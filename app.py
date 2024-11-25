import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io
import pandas as pd
from difflib import SequenceMatcher
import pdfplumber
import re
from typing import List, Dict
import fitz  # PyMuPDF
import json

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

# ... (file extraction and processing functions remain the same)

def compare_quotes(quote1_data, quote2_data):
    comparison_prompt = f"""
    Thoroughly compare the attached sales quotes, analyzing both text and tables. Generate a structured JSON response with these sections:

    1. Summary: Key insights and differences between the quotes
    2. LineItemComparison: Markdown table comparing each line item 
       Columns: 
       - LineItem: Description of item
       - Quote1Value: Value from Quote 1 (numeric where applicable)  
       - Quote2Value: Value from Quote 2 (numeric where applicable)
       - MatchStatus: Exact match (✓), Partial match (~), Only in Quote 1 ([1]), Only in Quote 2 ([2])
       - Difference: Difference between Quote1Value and Quote2Value (blank if n/a)
    3. TableComparison: Insights from comparing any tables
    4. UniqueItems: List items unique to each quote
    5. Statistics:
       - TotalItems: Total line items compared
       - ExactMatches: Number of exact matches  
       - PartialMatches: Number of partial or fuzzy matches
       - ItemsOnlyQuote1: Number of items only in Quote 1
       - ItemsOnlyQuote2: Number of items only in Quote 2

    Quote 1: {quote1_data}
    Quote 2: {quote2_data}
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
        comparison_json = json.loads(comparison_result)
        
        # Stage 3: Processing Results
        status_text.text("Stage 3/4: Processing results...")  
        progress_bar.progress(75)
        
        # Stage 4: Displaying Results
        status_text.text("Stage 4/4: Generating comparison...")
        progress_bar.progress(90)
        
        # Display results
        st.markdown("### Comparison Summary") 
        st.markdown(comparison_json['Summary'])
        
        st.markdown("### Line Item Comparison")
        st.markdown(comparison_json['LineItemComparison'])  
        
        if comparison_json['TableComparison']:
            st.markdown("### Table Comparison")
            st.markdown(comparison_json['TableComparison'])
        
        st.markdown("### Unique Items")
        st.markdown(comparison_json['UniqueItems'])
        
        st.markdown("### Comparison Statistics")  
        st.json(comparison_json['Statistics'])
        
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
    - ✓ : Exact match
    - ~ : Partial match  
    - [1] : Only in Quote 1
    - [2] : Only in Quote 2
""")

# Add a clear button at the bottom
if st.button("Clear and Start Over"):
    st.session_state.quote1 = None
    st.session_state.quote2 = None  
    st.rerun()
