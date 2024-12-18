import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io
import pandas as pd
from difflib import SequenceMatcher
import pdfplumber
import re
import json
from typing import List, Dict
import fitz  # PyMuPDF

# Streamlit page config
st.set_page_config(page_title="Sales Quote Comparison", page_icon="💼", layout="wide")

# Initialize Streamlit page
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

def extract_pdf_text_pdfplumber(file) -> str:
    """Extract text from PDF using pdfplumber with enhanced formatting."""
    try:
        with pdfplumber.open(file) as pdf:
            pages_text = []
            for page in pdf.pages:
                # Extract text with better handling of tables and layouts
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                # Extract tables and format them properly
                tables = page.extract_tables()
                formatted_tables = []
                for table in tables:
                    formatted_table = '\n'.join(['\t'.join([str(cell) if cell else '' for cell in row]) for row in table])
                    formatted_tables.append(formatted_table)
                
                # Combine regular text and tables
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
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        page_text.append(line_text)
                elif block["type"] == 1:  # Image block
                    page_text.append("[Image]")
            
            pages_text.append("\n".join(page_text))
        
        doc.close()
        return "\n\n".join(pages_text)
    except Exception as e:
        st.error(f"Error in PyMuPDF extraction: {str(e)}")
        return ""

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
    """Enhanced file reading with better PDF handling and text preprocessing."""
    try:
        if file.type == "application/pdf":
            text_pdfplumber = extract_pdf_text_pdfplumber(file)
            text_pymupdf = extract_pdf_text_pymupdf(file)
            
            text = text_pdfplumber if len(text_pdfplumber) > len(text_pymupdf) else text_pymupdf
            tables = extract_tables_from_text(text)
            formatted_tables = ['\n'.join(['\t'.join(row) for row in table]) for table in tables]
            final_text = text + '\n\n' + '\n\n'.join(formatted_tables)
            final_text = clean_text(final_text)
            
            return {
                'text': final_text,
                'tables': tables,
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
        else:  # txt files
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

# Modified file upload handling
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
        
        # Show preview with tabs for different views
        preview_tab1, preview_tab2 = st.tabs(["Processed Text", "Raw Text"])
        with preview_tab1:
            st.text(extracted_data['text'][:1000] + "...")
        with preview_tab2:
            st.text(extracted_data['raw_text'][:1000] + "...")
            
        # Show detected tables
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
        
        # Show preview with tabs for different views
        preview_tab1, preview_tab2 = st.tabs(["Processed Text", "Raw Text"])
        with preview_tab1:
            st.text(extracted_data['text'][:1000] + "...")
        with preview_tab2:
            st.text(extracted_data['raw_text'][:1000] + "...")
            
        # Show detected tables
        if extracted_data['tables']:
            with st.expander("View Detected Tables"):
                for i, table in enumerate(extracted_data['tables']):
                    st.markdown(f"**Table {i+1}**")
                    st.dataframe(pd.DataFrame(table))

def compare_quotes(quote1_data, quote2_data):
    comparison_prompt = f"""
    Please thoroughly compare the two sales quotes provided below. Analyze both the text and any tables. 
    Respond with a JSON object containing these keys:

    summary: Key insights and differences between the quotes, in a short paragraph 
    lineItems: An array of objects, one per line item, each with:
        - description: Description of the line item
        - quote1Value: Value from Quote 1 (numeric if possible, else string)
        - quote2Value: Value from Quote 2 (numeric if possible, else string)
        - match: Exact, Partial, OnlyQuote1, or OnlyQuote2
        - difference: Numeric difference if values are numeric, else null
    tables: Array of insights/differences found in comparing any tables, or [] if no tables
    onlyQuote1: Array of line item descriptions only in Quote 1, or [] 
    onlyQuote2: Array of line item descriptions only in Quote 2, or []
    stats: Object with:
        - totalItems: Total number of line items compared
        - exactMatches: Number of exact matches
        - partialMatches: Number of partial matches
        - itemsOnlyQuote1: Number of items only in Quote 1
        - itemsOnlyQuote2: Number of items only in Quote 2
        - totalDifference: Total numeric difference across all line items

    Quote 1: 
    {quote1_data}

    Quote 2:
    {quote2_data}
    """
    
    response = st.session_state.anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": comparison_prompt
        }]
    )
    
    return response.content[0].text

# Compare button
if st.button("Compare Quotes") and st.session_state.quote1 and st.session_state.quote2:
    # Create a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Stage 1: Document Processing
        status_text.text("Stage 1/4: Processing documents...")
        progress_bar.progress(25)
        
        # Stage 2: Sending to Claude
        status_text.text("Stage 2/4: Analyzing with Claude...")
        progress_bar.progress(50)
        
        comparison_result = compare_quotes(st.session_state.quote1['content'], st.session_state.quote2['content'])
        # Print out the raw comparison result for debugging
        st.write("Raw Comparison Result:")
        st.write(comparison_result)

        comparison_json = json.loads(comparison_result)
        
        # Stage 3: Processing Results
        status_text.text("Stage 3/4: Processing results...")
        progress_bar.progress(75)
        
        # Stage 4: Displaying Results
        status_text.text("Stage 4/4: Generating comparison...")
        progress_bar.progress(90)
        
        # Display results
        st.markdown("### Comparison Summary")
        st.markdown(comparison_json['summary'])
        
        st.markdown("### Line Item Comparison")
        line_item_table = pd.DataFrame(comparison_json['lineItems'])
        st.table(line_item_table)
        
        if comparison_json['tables']:
            st.markdown("### Table Comparison")
            st.json(comparison_json['tables'])
        
        st.markdown("### Only in Quote 1")
        st.json(comparison_json['onlyQuote1'])

        st.markdown("### Only in Quote 2")  
        st.json(comparison_json['onlyQuote2'])
        
        st.markdown("### Comparison Statistics")
        st.json(comparison_json['stats'])
        
        # Add download button
        st.download_button(
            "Download Comparison",
            comparison_result,
            "comparison.json",
            "application/json"
        )
        
        # Complete the progress bar
        progress_bar.progress(100)
        status_text.text("Analysis complete! ✅")
        
        # Add timestamp
        st.markdown(f"*Analysis completed at {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Error in comparison: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
    **Legend:**
    - Exact: Line items are an exact match 
    - Partial: Line items are a partial match
    - OnlyQuote1: Line item is only in Quote 1
    - OnlyQuote2: Line item is only in Quote 2
""")

# Add a clear button at the bottom
if st.button("Clear and Start Over"):
    st.session_state.quote1 = None
    st.session_state.quote2 = None
    st.rerun()
