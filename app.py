import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io
import pandas as pd
from difflib import SequenceMatcher
import pdfplumber  # Added for better PDF extraction
import re
from typing import List, Dict
import fitz  # PyMuPDF for even better PDF handling

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
    """Extract text from PDF using PyMuPDF for better formatting and table recognition."""
    try:
        # Convert StreamitUploadedFile to bytes for PyMuPDF
        file_bytes = file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        pages_text = []
        for page in doc:
            # Get the text blocks with their coordinates and formatting
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
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep important punctuation
    text = re.sub(r'[^\w\s.,;:$%()-]', '', text)
    # Normalize line endings
    text = text.replace('\r', '\n')
    # Remove empty lines
    text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
    return text

def extract_tables_from_text(text: str) -> List[List[str]]:
    """Attempt to identify and extract tabular data from text."""
    tables = []
    current_table = []
    
    lines = text.split('\n')
    for line in lines:
        # Heuristic: lines with multiple tabs or consistent separators might be table rows
        if '\t' in line or '  ' in line:
            cells = re.split(r'\t|  +', line.strip())
            current_table.append(cells)
        elif current_table:
            if len(current_table) > 1:  # Only keep tables with multiple rows
                tables.append(current_table)
            current_table = []
    
    if current_table and len(current_table) > 1:
        tables.append(current_table)
    
    return tables

def read_file(file) -> Dict[str, str]:
    """Enhanced file reading with better PDF handling and text preprocessing."""
    try:
        if file.type == "application/pdf":
            # Try multiple PDF extraction methods
            text_pdfplumber = extract_pdf_text_pdfplumber(file)
            text_pymupdf = extract_pdf_text_pymupdf(file)
            
            # Combine results, preferring the one with more content
            text = text_pdfplumber if len(text_pdfplumber) > len(text_pymupdf) else text_pymupdf
            
            # Extract and format tables
            tables = extract_tables_from_text(text)
            formatted_tables = ['\n'.join(['\t'.join(row) for row in table]) for table in tables]
            
            # Combine regular text and formatted tables
            final_text = text + '\n\n' + '\n\n'.join(formatted_tables)
            
            # Clean and normalize the text
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

# Update requirements.txt:
# streamlit
# anthropic
# pypdf
# python-docx
# pdfplumber
# PyMuPDF

# [Previous code remains the same until the file upload section]

# Modified file upload handling
with col1:
    st.subheader("Quote 1")
    quote1_file = st.file_uploader(
        "Upload first quote",
        type=['pdf', 'docx', 'txt'],
        key="quote1_uploader"
    )
    if quo
