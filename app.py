import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io
import pandas as pd
from difflib import SequenceMatcher
import pdfplumber
import re
import time
from typing import List, Dict
import fitz  # PyMuPDF

# Streamlit page config
st.set_page_config(page_title="Sales Quote Comparison", page_icon="💼", layout="wide")
st.title("Sales Quote Line Item Comparison")
st.markdown("Using Claude 3 Opus for Enhanced Analysis")

# Secure API key handling
try:
    if 'anthropic_client' not in st.session_state:
        anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.session_state.anthropic_client = Anthropic(api_key=anthropic_api_key)
except Exception as e:
    st.error("Please configure your API key in Streamlit secrets")
    st.stop()

# Initialize session state
if 'quote1' not in st.session_state:
    st.session_state.quote1 = None
if 'quote2' not in st.session_state:
    st.session_state.quote2 = None
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = None

def enhanced_pdf_extraction(file) -> Dict[str, any]:
    """Improved PDF text extraction combining multiple methods."""
    text_pdfplumber = extract_pdf_text_pdfplumber(file)
    text_pymupdf = extract_pdf_text_pymupdf(file)
    
    combined_text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            for word in words:
                combined_text.append({
                    'text': word['text'],
                    'x0': word['x0'],
                    'y0': word['y0'],
                    'line_number': int(word['y0'] / 10)
                })
    
    lines = {}
    for word in combined_text:
        line_num = word['line_number']
        if line_num not in lines:
            lines[line_num] = []
        lines[line_num].append(word['text'])
    
    formatted_text = '\n'.join([' '.join(line) for line in lines.values()])
    
    return {
        'text': formatted_text,
        'pdfplumber_text': text_pdfplumber,
        'pymupdf_text': text_pymupdf,
        'word_positions': combined_text
    }

def extract_pdf_text_pdfplumber(file) -> str:
    """Extract text from PDF using pdfplumber with enhanced formatting."""
    try:
        with pdfplumber.open(file) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                tables = page.extract_tables()
                formatted_tables = []
                for table in tables:
                    formatted_table = '\n'.join(['\t'.join([str(cell) if cell else '' for cell in row]) for row in table])
                    formatted_tables.append(formatted_table)
                
                page_text = text + '\n' + '\n'.join(formatted_tables)
                pages_text.append(page_text)
            
            return '\n\n'.join(pages_text)
    except Exception as e:
        st.error(f"Error in pdfplumber extraction: {str(e)}")
        return ""

def extract_pdf_text_pymupdf(file) -> str:
    """Extract text from PDF using PyMuPDF for better formatting."""
    try:
        file_bytes = file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        pages_text = []
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            page_text = []
            
            for block in blocks:
                if block["type"] == 0:
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        page_text.append(line_text)
                elif block["type"] == 1:
                    page_text.append("[Image]")
            
            pages_text.append("\n".join(page_text))
        
        doc.close()
        return "\n\n".join(pages_text)
    except Exception as e:
        st.error(f"Error in PyMuPDF extraction: {str(e)}")
        return ""

def chunk_document(text: str, max_tokens: int = 3000) -> List[str]:
    """Split document into chunks for API processing."""
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in text.split('\n'):
        line_tokens = len(line.split()) + len([c for c in line if c in '.,;:!?'])
        
        if current_length + line_tokens > max_tokens:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_length = line_tokens
        else:
            current_chunk.append(line)
            current_length += line_tokens
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def process_with_claude(client, content: str, retries: int = 3):
    """Process content with Claude API with retry logic."""
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": content
                }]
            )
            return response
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(2 ** attempt)
            
    return None

def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,;:$%()-]', '', text)
    text = text.replace('\r', '\n')
    text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
    return text

def extract_tables_from_text(text: str) -> List[List[str]]:
    """Attempt to identify and extract tabular data from text."""
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
    """Enhanced file reading with better PDF handling."""
    try:
        if file.type == "application/pdf":
            extracted_data = enhanced_pdf_extraction(file)
            return {
                'text': extracted_data['text'],
                'tables': extract_tables_from_text(extracted_data['text']),
                'raw_text': extracted_data['pdfplumber_text']
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

# Create two columns for file uploads
col1, col2 = st.columns(2)

# File upload handling
with col1:
    st.subheader("Quote 1")
    quote1_file = st.file_uploader(
        "Upload first quote",
        type=['pdf', 'docx', 'txt'],
        key="quote1_uploader"
    )
    if quote1_file:
        extracted_data = read_file(quote1_file)
        st.session_state.quote1 = {
            'name': quote1_file.name,
            'content': extracted_data['text'],
            'tables': extracted_data['tables'],
            'raw_content': extracted_data['raw_text']
        }
        st.success(f"Quote 1 uploaded: {quote1_file.name}")
        
        preview_tab1, preview_tab2 = st.tabs(["Processed Text", "Raw Text"])
        with preview_tab1:
            st.text(extracted_data['text'][:1000] + "...")
        with preview_tab2:
            st.text(extracted_data['raw_text'][:1000] + "...")
            
        if extracted_data['tables']:
            with st.expander("View Detected Tables"):
                for i, table in enumerate(extracted_data['tables']):
                    st.markdown(f"**Table {i+1}**")
                    st.dataframe(pd.DataFrame(table))

with col2:
    st.subheader("Quote 2")
    quote2_file = st.file_uploader(
        "Upload second quote",
        type=['pdf', 'docx', 'txt'],
        key="quote2_uploader"
    )
    if quote2_file:
        extracted_data = read_file(quote2_file)
        st.session_state.quote2 = {
            'name': quote2_file.name,
            'content': extracted_data['text'],
            'tables': extracted_data['tables'],
            'raw_content': extracted_data['raw_text']
        }
        st.success(f"Quote 2 uploaded: {quote2_file.name}")
        
        preview_tab1, preview_tab2 = st.tabs(["Processed Text", "Raw Text"])
        with preview_tab1:
            st.text(extracted_data['text'][:1000] + "...")
        with preview_tab2:
            st.text(extracted_data['raw_text'][:1000] + "...")
            
        if extracted_data['tables']:
            with st.expander("View Detected Tables"):
                for i, table in enumerate(extracted_data['tables']):
                    st.markdown(f"**Table {i+1}**")
                    st.dataframe(pd.DataFrame(table))

# Compare button
if st.button("Compare Quotes") and st.session_state.quote1 and st.session_state.quote2:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Stage 1/4: Processing documents...")
        progress_bar.progress(25)
        
        quote1_chunks = chunk_document(st.session_state.quote1['content'])
        quote2_chunks = chunk_document(st.session_state.quote2['content'])
        
        status_text.text("Stage 2/4: Analyzing with Claude...")
        progress_bar.progress(50)
        
        results = []
        for q1_chunk, q2_chunk in zip(quote1_chunks, quote2_chunks):
            chunk_prompt = f"""
            Compare these quote sections and create a clear markdown table showing ONLY:
            | Line Item | Quote 1 Description | Quote 2 Description | Match Status |

            Quote 1: {q1_chunk}
            Quote 2: {q2_chunk}

            Use these match indicators:
            ✓ = Exact match
            ~ = Partial match
            [1] = Only in Quote 1
            [2] = Only in Quote 2
            """
            
            chunk_result = process_with_claude(st.session_state.anthropic_client, chunk_prompt)
            results.append(chunk_result.content[0].text)
        
        status_text.text("Stage 3/4: Processing results...")
        progress_bar.progress(75)
        
        combined_results = '\n'.join(results)
        
        status_text.text("Stage 4/4: Generating comparison table...")
        progress_bar.progress(90)
        
        st.markdown("### Line Item Comparison")
        st.markdown(combined_results)
        
        st.download_button(
            "Download Comparison",
            combined_results,
            "comparison.csv",
            "text/csv"
        )
        
        progress_bar.progress(100)
        status_text.text("Analysis complete! ✅")
        
        st.markdown(f"*Analysis completed at {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Error in comparison: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
    **Legend:**
    - ✓ : Exact match
    - ~ : Partial match
    - [1] : Only in Quote 1
    - [2] : Only in Quote 2
""")

# Clear button
if st.button("Clear and Start Over"):
    st.session_state.quote1 = None
    st.session_state.quote2 = None
    st.rerun()
