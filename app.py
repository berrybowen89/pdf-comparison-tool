import streamlit as st
from anthropic import Anthropic
from rapidfuzz import fuzz
import pypdf
import docx
import io
import pandas as pd
import pdfplumber
import re
import time
import tempfile
import subprocess
from typing import List, Dict
import fitz

# Original variables and matching tables
variables = [
    {"var": "Project:", "var_name": "Project"},
    {"var": "Address:", "var_name": "Address"},
    {"var": "Date:", "var_name": "Date"},
    # ... (include all your variables)
]

matching_table = [
    {'villa_var': 'Factory Print Number:', 'factory_code': 'Model No.:'},
    {'villa_var': 'Villa Model:', 'factory_code': 'Construction Type'},
    # ... (include all your matching table entries)
]

# Streamlit page config
st.set_page_config(page_title="Sales Quote Comparison", page_icon="💼", layout="wide")
st.title("Sales Quote Line Item Comparison")
st.markdown("Using Claude 3 Opus for Enhanced Analysis")

# Initialize Anthropic client
try:
    if 'anthropic_client' not in st.session_state:
        anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.session_state.anthropic_client = Anthropic(api_key=anthropic_api_key)
except Exception as e:
    st.error("Please configure your API key in Streamlit secrets")
    st.stop()

# Initialize session state
if 'quote1' not in st.session_state: st.session_state.quote1 = None
if 'quote2' not in st.session_state: st.session_state.quote2 = None
if 'comparison_results' not in st.session_state: st.session_state.comparison_results = None

def extract_text_from_oxps(file):
    """Extract text from OXPS file by converting to PDF first."""
    try:
        with io.BytesIO(file.read()) as oxps_buffer:
            with tempfile.NamedTemporaryFile(suffix='.oxps') as temp_oxps:
                temp_oxps.write(oxps_buffer.getvalue())
                temp_oxps.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_pdf:
                    subprocess.run(['oxps2pdf', temp_oxps.name, temp_pdf.name], check=True)
                    
                    with open(temp_pdf.name, 'rb') as pdf_file:
                        return extract_pdf_text_pdfplumber(io.BytesIO(pdf_file.read()))
    except Exception as e:
        st.error(f"Error converting OXPS file: {str(e)}")
        return ""

def normalize_value(value):
    if value is None: return ""
    return "".join(e for e in str(value).strip().lower() if e.isalnum() or e.isspace())

def fuzzy_match(val1, val2, threshold=50):
    if not val1 or not val2: return False
    return fuzz.ratio(val1, val2) >= threshold

def robust_match(villa_value, factory_value):
    if any(x is None for x in [villa_value, factory_value]): return False
    
    if "roof pitch" in str(factory_value).lower():
        factory_value = str(factory_value).replace("ROOF PITCH","")
    if "roof pitch" in str(villa_value).lower():
        villa_value = str(villa_value).replace("ROOF PITCH","")

    norm_villa = normalize_value(villa_value)
    norm_factory = normalize_value(factory_value)

    return (norm_villa == norm_factory or
            norm_villa in norm_factory or
            norm_factory in norm_villa or
            fuzzy_match(norm_villa, norm_factory))

def extract_pdf_text_pdfplumber(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        st.error(f"Error in PDF extraction: {str(e)}")
        return ""

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,;:$%()-]', '', text)
    text = text.replace('\r', '\n')
    text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
    return text

def extract_tables_from_text(text: str) -> List[List[str]]:
    tables = []
    current_table = []
    
    lines = text.split('\n')
    for line in lines:
        if '\t' in line or '  ' in line:
            cells = re.split(r'\t|  +', line.strip())
            current_table.append(cells)
        elif current_table:
            if len(current_table) > 1:
                tables.append(current_table)
            current_table = []
    
    if current_table and len(current_table) > 1:
        tables.append(current_table)
    
    return tables

def read_file(file) -> Dict[str, str]:
    """Enhanced file reading with OXPS support."""
    try:
        if file.type == "application/pdf":
            text = extract_pdf_text_pdfplumber(file)
            return {
                'text': clean_text(text),
                'tables': extract_tables_from_text(text),
                'raw_text': text
            }
        elif file.type == "application/oxps":
            text = extract_text_from_oxps(file)
            return {
                'text': clean_text(text),
                'tables': extract_tables_from_text(text),
                'raw_text': text
            }
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(file)
            text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
            tables = [[cell.text for cell in row.cells] for table in doc.tables for row in table.rows]
            return {
                'text': clean_text(text),
                'tables': tables,
                'raw_text': text
            }
        else:
            text = file.getvalue().decode('utf-8')
            return {
                'text': clean_text(text),
                'tables': extract_tables_from_text(text),
                'raw_text': text
            }
    except Exception as e:
        st.error(f"Error reading file {file.name}: {str(e)}")
        return {'text': '', 'tables': [], 'raw_text': ''}

def extract_variables_from_villa_text(text, variables):
    extracted = {}
    for variable in variables:
        var, var_name = variable['var'], variable['var_name']
        start = text.find(var) + len(var)
        if start > len(var):
            end = text.find("\n", start)
            extracted[var_name] = text[start:end].strip()
    return extracted

def extract_variables_from_factory_text(text):
    extracted = {}
    lines = text.splitlines()
    
    for i, line in enumerate(lines):
        parts = line.split(maxsplit=4)
        
        if "OP001542 Model No.:" in line:
            extracted["Model No.:"] = parts[3].strip()
        elif len(parts) >= 2 and parts[0].startswith("OP"):
            extracted[parts[0]] = " ".join(parts[1:]).strip()
        elif len(parts) >= 3 and parts[1].startswith("OP"):
            extracted[parts[1]] = " ".join(parts[2:]).strip()
        elif ":" in line:
            key, value = map(str.strip, line.split(":", 1))
            extracted[key] = value
            
        special_codes = ["OP000110", "OP000446", "OP000112", "OP001619"]
        for code in special_codes:
            if code in line and extracted.get(code) is None:
                target_idx = i + (15 if code != "OP000446" else 14)
                if target_idx < len(lines):
                    extracted[code] = lines[target_idx].strip()
    
    return extracted

def process_comparison_result(quote1_data, quote2_data):
    results = []
    
    # Standard field comparison
    for var in variables:
        var_name = var['var_name']
        if var_name in quote1_data and var_name in quote2_data:
            value1, value2 = quote1_data[var_name], quote2_data[var_name]
            is_match = robust_match(value1, value2)
            results.append({
                "Line Item": var_name,
                "Quote 1 Description": value1,
                "Quote 2 Description": value2,
                "Match Status": "✓" if is_match else "❌"
            })
    
    # Factory code matching
    for match in matching_table:
        villa_var, factory_code = match['villa_var'], match['factory_code']
        var_name = next((v['var_name'] for v in variables if v['var'] == villa_var), villa_var)
        
        quote1_value = quote1_data.get(var_name, "Not Found")
        quote2_value = quote2_data.get(factory_code, "Not Found")
        
        if quote1_value != "Not Found" or quote2_value != "Not Found":
            if not any(r["Line Item"] == var_name for r in results):
                results.append({
                    "Line Item": var_name,
                    "Quote 1 Description": quote1_value,
                    "Quote 2 Description": quote2_value,
                    "Match Status": "✓" if robust_match(quote1_value, quote2_value) else "❌"
                })
    
    return results

# File upload UI
col1, col2 = st.columns(2)

with col1:
    st.subheader("Quote 1")
    quote1_file = st.file_uploader(
        "Upload first quote",
        type=['pdf', 'docx', 'txt', 'oxps'],
        key="quote1_uploader"
    )
    if quote1_file:
        extracted_data = read_file(quote1_file)
        st.session_state.quote1 = {
            'name': quote1_file.name,
            'content': extracted_data['text'],
            'raw_content': extracted_data['raw_text']
        }
        st.success(f"Quote 1 uploaded: {quote1_file.name}")
        
        preview_tab1, preview_tab2 = st.tabs(["Processed Text", "Raw Text"])
        with preview_tab1:
            st.text(extracted_data['text'][:1000] + "...")
        with preview_tab2:
            st.text(extracted_data['raw_text'][:1000] + "...")

with col2:
    st.subheader("Quote 2")
    quote2_file = st.file_uploader(
        "Upload second quote",
        type=['pdf', 'docx', 'txt', 'oxps'],
        key="quote2_uploader"
    )
    if quote2_file:
        extracted_data = read_file(quote2_file)
        st.session_state.quote2 = {
            'name': quote2_file.name,
            'content': extracted_data['text'],
            'raw_content': extracted_data['raw_text']
        }
        st.success(f"Quote 2 uploaded: {quote2_file.name}")
        
        preview_tab1, preview_tab2 = st.tabs(["Processed Text", "Raw Text"])
        with preview_tab1:
            st.text(extracted_data['text'][:1000] + "...")
        with preview_tab2:
            st.text(extracted_data['raw_text'][:1000] + "...")

# Compare button
if st.button("Compare Quotes") and st.session_state.quote1 and st.session_state.quote2:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Processing documents...")
        progress_bar.progress(25)
        
        quote1_data = extract_variables_from_villa_text(st.session_state.quote1['content'], variables)
        quote2_data = extract_variables_from_factory_text(st.session_state.quote2['content'])
        
        status_text.text("Comparing documents...")
        progress_bar.progress(50)
        
        results = process_comparison_result(quote1_data, quote2_data)
        
        status_text.text("Generating report...")
        progress_bar.progress(75)
        
        total_items = len(results)
        exact_matches = sum(1 for r in results if r["Match Status"] == "✓")
        
        st.markdown("### Comparison Results")
        st.dataframe(pd.DataFrame(results))
        
        st.markdown(f"""
        **Summary:**
        - Total Items: {total_items}
        - Exact Matches: {exact_matches}
        - Match Rate: {(exact_matches/total_items*100):.1f}%
        """)
        
        df = pd.DataFrame(results)
        csv = df.to_csv(index=False)
        st.download_button(
            "Download Results",
            csv,
            "comparison_results.csv",
            "text/csv",
            key='download-csv'
        )
        
        progress_bar.progress(100)
        status_text.text("Analysis complete! ✅")
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Error in comparison: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
    **Legend:**
    - ✓ : Exact match
    - ❌ : No match
""")

# Clear button
if st.button("Clear and Start Over"):
    st.session_state.quote1 = None
    st.session_state.quote2 = None
    st.rerun()
