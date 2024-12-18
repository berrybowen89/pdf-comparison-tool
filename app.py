```python
import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import fitz
import io
import pandas as pd
from typing import List, Dict
from anthropic import Anthropic

# Streamlit page config
st.set_page_config(page_title="PDF Comparison Tool", page_icon="📊", layout="wide")

# Initialize Streamlit page
st.title("PDF Comparison Tool")
st.markdown("Using Claude AI for Enhanced Analysis")

# Secure API key handling
try:
    if 'anthropic_client' not in st.session_state:
        anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.session_state.anthropic_client = Anthropic(api_key=anthropic_api_key)
except Exception as e:
    st.error("Please configure your API key in Streamlit secrets")
    st.stop()

# Initialize session state
if 'villa_data' not in st.session_state:
    st.session_state.villa_data = None
if 'factory_data' not in st.session_state:
    st.session_state.factory_data = None
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = None

def extract_pdf_text(file) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        file_bytes = file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def extract_variables_from_villa_text(text):
    """Extract variables from Villa spec PDF."""
    # Placeholder for villa variable extraction logic
    # Modify according to your specific Villa PDF structure
    villa_data = {}
    return villa_data

def extract_variables_from_factory_text(text):
    """Extract variables from Factory spec PDF."""
    # Placeholder for factory variable extraction logic
    # Modify according to your specific Factory PDF structure
    factory_data = {}
    return factory_data

def compare_specs(villa_data, factory_data):
    """Compare Villa and Factory specs using Claude AI."""
    comparison_prompt = f"""
    Compare the Villa spec and Factory spec data provided below. Generate a structured response with these sections:

    1. Summary: Key insights and differences between the specs
    2. VariableComparison: Markdown table comparing each variable
       Columns:
       - Variable: Name of the variable
       - VillaValue: Value from Villa spec
       - FactoryValue: Value from Factory spec
       - MatchStatus: Exact match (✓), Partial match (~), Only in Villa spec ([V]), Only in Factory spec ([F])
    3. UniqueItems: List variables unique to each spec
    4. Statistics:
       - TotalVariables: Total variables compared
       - ExactMatches: Number of exact matches
       - PartialMatches: Number of partial or fuzzy matches
       - ItemsOnlyVilla: Number of variables only in Villa spec
       - ItemsOnlyFactory: Number of variables only in Factory spec

    Villa spec data: {villa_data}
    Factory spec data: {factory_data}
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

# File upload widgets
villa_file = st.file_uploader("Select Villa Spec PDF", type="pdf")
factory_file = st.file_uploader("Select Factory Spec PDF", type="pdf")

if villa_file and factory_file:
    # Extract text from PDFs
    villa_text = extract_pdf_text(villa_file)
    factory_text = extract_pdf_text(factory_file)

    # Extract variables from text
    villa_data = extract_variables_from_villa_text(villa_text)
    factory_data = extract_variables_from_factory_text(factory_text)

    # Store data in session state
    st.session_state.villa_data = villa_data
    st.session_state.factory_data = factory_data

    # Compare specs using Claude AI
    if st.button("Compare Specs"):
        comparison_result = compare_specs(villa_data, factory_data)
        st.session_state.comparison_results = comparison_result

        # Display comparison results
        st.markdown("### Comparison Summary")
        st.markdown(comparison_result)

        # Add download button
        st.download_button(
            "Download Comparison",
            comparison_result,
            "comparison.md",
            "text/markdown"
        )
else:
    st.warning("Please upload both Villa and Factory spec PDFs.")

# Display comparison results from session state
if st.session_state.comparison_results:
    st.markdown("### Comparison Results")
    st.markdown(st.session_state.comparison_results)
```
