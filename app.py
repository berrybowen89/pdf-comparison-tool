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
from typing import List, Dict
import fitz

variables = [
    {"var": "Project:", "var_name": "Project"},
    {"var": "Address:", "var_name": "Address"},
    {"var": "Date:", "var_name": "Date"},
    {"var": "Villa Model:", "var_name": "Villa Model"},
    {"var": "Factory Print Number:", "var_name": "Model Number"},
    {"var": "Unit Dimensions:", "var_name": "Construction Type"},
    {"var": "Number of Modules:", "var_name": "Number of Modules"},
    {"var": "Roof Pitch", "var_name": "Roof Pitch"},
    {"var": "Roof Shingles:", "var_name": "Roof Shingles"},
    {"var": "Interior Ceiling", "var_name": "Interior Ceiling"},
    {"var": "Clerestory Windows", "var_name": "Clerestory Windows"},
    {"var": 'Eaves', "var_name": "Eaves Attach"},
    {"var": '16" Front and Rear Overhang', "var_name": "Front and Rear Overhang"},
    {"var": "Fire Sprinklers", "var_name": "Fire Sprinklers"},
    {"var": "Electrical Panel", "var_name": "Electrical Panel"},
    {"var": "Covered Porch", "var_name": "Covered Porch"},
    {"var": "Mirrored Floorplan (side to side)", "var_name": "Mirrored Floorplan"},
    {"var": "Flipped Floorplan (end to end)", "var_name": "Flipped Floorplan"},
    {"var": "Alternate Kitchen Layout", "var_name": "Alternate Kitchen Layout"},
    {"var": "Larger Windows", "var_name": "Larger Windows"},
    {"var": "Sliding Glass Door(s)", "var_name": "Sliding Glass Door(s)"},
    {"var": "Skylight(s)", "var_name": "Skylight(s)"},
    {"var": "Den in place of bedroom", "var_name": "Den in place of bedroom"},
    {"var": "Alternate Laundry Room (1200A)", "var_name": "Alternate Laundry Room"},
    {"var": "Front Exterior Door Type", "var_name": "Front Exterior Door Type"},
    {"var": "Rear Exterior Door Type", "var_name": "Rear Exterior Door Type"},
    {"var": "Ex. Body Paint", "var_name": "Exterior Body Paint"},
    {"var": "Ext. Fascia & Trim", "var_name": "Exterior Fascia & Trim"},
    {"var": "Lap Siding (fiber cement)", "var_name": "Lap Siding"},
    {"var": "Stucco Option", "var_name": "Stucco Option"},
    {"var": "Kitchen/Bath Flooring Type", "var_name": "Kitchen/Bath Flooring Type"},
    {"var": "Kitchen/Bath Flooring Color", "var_name": "Kitchen/Bath Flooring Color"},
    {"var": "Living Room Flooring Type", "var_name": "Living Room Flooring Type"},
    {"var": "Living Room Flooring Color", "var_name": "Living Room Flooring Color"},
    {"var": "Bedroom Flooring Type", "var_name": "Bedroom Flooring Type"},
    {"var": "Bedroom Flooring Color", "var_name": "Bedroom Flooring Color"},
    {"var": "Shaker Cabinet Doors (Upper)", "var_name": "Upper Cabinet Doors"},
    {"var": "Shaker Cabinet Doors (Lower)", "var_name": "Lower Cabinet Doors"},
    {"var": "Kitchen Sink", "var_name": "OP001618"},
    {"var": "Countertop Material", "var_name": "Countertop Material"},
    {"var": "Optional Island", "var_name": "Optional Island"},
    {"var": "Cabinet Hardware Type", "var_name": "Cabinet Hardware Type"},
    {"var": "Cabinet Hardware Finish", "var_name": "Cabinet Hardware Finish"},
    {"var": "Interior Door Hardware", "var_name": "Interior Door Hardware"},
    {"var": "Additional Recessed Lights", "var_name": "Additional Recessed Lights"},
    {"var": "Wire for A/C and Condenser Upgrade", "var_name": "A/C and Condenser Wiring"},
    {"var": "Washer Dryer Upgrade", "var_name": "Washer Dryer Upgrade"},
    {"var": "Thermostat", "var_name": "Thermostat"},
    {"var": "Appliances", "var_name": "Appliances"},
    {"var": "Optional Bathroom Window", "var_name": "Optional Bathroom Window"},
    {"var": "Primary Shower Type", "var_name": "Primary Shower Type"},
    {"var": "Secondary Shower Type", "var_name": "Secondary Shower Type"}
]

matching_table = [
    {'villa_var': 'Factory Print Number:', 'factory_code': 'Model No.:'},
    {'villa_var': 'Villa Model:', 'factory_code': 'Construction Type'},
    {'villa_var': 'Unit Dimensions:', 'factory_code': 'Model Size'},
    {'villa_var': 'Interior Ceiling', 'factory_code': 'OP000048'},
    {'villa_var': 'Roof Pitch', 'factory_code': 'OP000049'},
    {'villa_var': 'Roof Pitch', 'factory_code': 'OP001534'},
    {'villa_var': 'Skylight(s)', 'factory_code': 'OP000511'},
    {'villa_var': 'Skylight(s)', 'factory_code': 'OP000512'},
    {'villa_var': 'Clerestory Windows', 'factory_code': 'OP001603'},
    {'villa_var': '16" Front and Rear Overhang', 'factory_code': 'OP001516'},
    {'villa_var': 'Eaves', 'factory_code': 'OP001028'},
    {'villa_var': 'Ex. Body Paint', 'factory_code': 'OP001610'},
    {'villa_var': 'Ext. Fascia & Trim', 'factory_code': 'OP001609'},
    {'villa_var': 'Ext. Fascia & Trim', 'factory_code': 'OP001283'},
    {'villa_var': 'Roof Shingles', 'factory_code': 'OP000080'},
    {'villa_var': 'Optional Bathroom Window', 'factory_code': 'OP001057'},
    {'villa_var': 'Front Exterior Door Type', 'factory_code': 'OP000073'},
    {'villa_var': 'Rear Exterior Door Type', 'factory_code': 'OP001112'},
    {'villa_var': 'Electrical Panel', 'factory_code': 'OP001622'},
    {'villa_var': 'Thermostat', 'factory_code': 'OP001194'},
    {'villa_var': 'Shaker Cabinet Doors (Upper)', 'factory_code': 'OP001602'},
    {'villa_var': 'Shaker Cabinet Doors (Lower)', 'factory_code': 'OP001602'},
    {'villa_var': 'Kitchen/Bath Flooring Type', 'factory_code': 'OP001088'},
    {'villa_var': 'Kitchen/Bath Flooring Color', 'factory_code': 'OP001088'},
    {'villa_var': 'Living Room Flooring Type', 'factory_code': 'OP001088'},
    {'villa_var': 'Living Room Flooring Color', 'factory_code': 'OP001088'},
    {'villa_var': 'Bedroom Flooring Type', 'factory_code': 'OP001088'},
    {'villa_var': 'Bedroom Flooring Color', 'factory_code': 'OP001088'},
    {'villa_var': 'Primary Shower Type', 'factory_code': 'OP001002'},
    {'villa_var': 'Secondary Shower Type', 'factory_code': 'OP000110'}
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

def extract_variables_from_villa_text(text, variables):
    extracted = {}
    for variable in variables:
        var, var_name = variable['var'], variable['var_name']
        start = text.find(var) + len(var)
        if start > len(var):  # Only if var was found
            end = text.find("\n", start)
            extracted[var_name] = text[start:end].strip()
    return extracted

def extract_variables_from_factory_text(text):
    extracted = {}
    lines = text.splitlines()
    
    for i, line in enumerate(lines):
        parts = line.split(maxsplit=4)
        
        # Handle various text patterns
        if "OP001542 Model No.:" in line:
            extracted["Model No.:"] = parts[3].strip()
        elif len(parts) >= 2 and parts[0].startswith("OP"):
            extracted[parts[0]] = " ".join(parts[1:]).strip()
        elif len(parts) >= 3 and parts[1].startswith("OP"):
            extracted[parts[1]] = " ".join(parts[2:]).strip()
        elif ":" in line:
            key, value = map(str.strip, line.split(":", 1))
            extracted[key] = value
            
        # Handle special cases
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

def read_file(file):
    try:
        text = extract_pdf_text_pdfplumber(file)
        return {
            'text': text,
            'tables': [],  # Add table extraction if needed
            'raw_text': text
        }
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return {'text': '', 'tables': [], 'raw_text': ''}

# File upload UI
col1, col2 = st.columns(2)

with col1:
    st.subheader("Quote 1")
    quote1_file = st.file_uploader("Upload first quote", type=['pdf'], key="quote1_uploader")
    if quote1_file:
        extracted_data = read_file(quote1_file)
        st.session_state.quote1 = {
            'name': quote1_file.name,
            'content': extracted_data['text'],
            'raw_content': extracted_data['raw_text']
        }
        st.success(f"Quote 1 uploaded: {quote1_file.name}")

with col2:
    st.subheader("Quote 2")
    quote2_file = st.file_uploader("Upload second quote", type=['pdf'], key="quote2_uploader")
    if quote2_file:
        extracted_data = read_file(quote2_file)
        st.session_state.quote2 = {
            'name': quote2_file.name,
            'content': extracted_data['text'],
            'raw_content': extracted_data['raw_text']
        }
        st.success(f"Quote 2 uploaded: {quote2_file.name}")

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

if st.button("Clear and Start Over"):
    st.session_state.quote1 = None
    st.session_state.quote2 = None
    st.rerun()
