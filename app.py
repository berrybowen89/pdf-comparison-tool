import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def normalize_text(text):
    """Basic text normalization"""
    if text is None:
        return ""
    return " ".join(text.lower().split())

def enhanced_fuzzy_match(text1, text2, threshold=80):
    """Enhanced fuzzy matching with multiple metrics"""
    if not text1 or not text2:
        return False
    
    # Normalize texts
    norm_text1 = normalize_text(str(text1))
    norm_text2 = normalize_text(str(text2))
    
    # Calculate different fuzzy ratios
    ratio = fuzz.ratio(norm_text1, norm_text2)
    partial_ratio = fuzz.partial_ratio(norm_text1, norm_text2)
    token_sort_ratio = fuzz.token_sort_ratio(norm_text1, norm_text2)
    
    # Weighted average of different metrics
    weighted_score = (ratio * 0.4 + partial_ratio * 0.4 + token_sort_ratio * 0.2)
    
    return weighted_score >= threshold

def compare_pdfs(villa_text, factory_text):
    """Compare the contents of both PDFs"""
    # Split texts into lines
    villa_lines = villa_text.split('\n')
    factory_lines = factory_text.split('\n')
    
    comparison_results = []
    
    # Process Villa PDF lines
    for villa_line in villa_lines:
        if ':' in villa_line:
            option, value = villa_line.split(':', 1)
            option = option.strip()
            value = value.strip()
            
            # Find best match in factory text
            best_match = None
            best_score = 0
            
            for factory_line in factory_lines:
                if len(factory_line.split()) >= 2:  # Ensure line has content
                    score = fuzz.token_set_ratio(value, factory_line)
                    if score > best_score:
                        best_score = score
                        best_match = factory_line
            
            if best_match:
                is_match = enhanced_fuzzy_match(value, best_match)
                comparison_results.append({
                    "Villa Option": option,
                    "Villa Value": value,
                    "Factory Value": best_match,
                    "Match": "✔️" if is_match else "❌",
                    "Confidence": f"{best_score}%"
                })
    
    return comparison_results

# Streamlit UI
st.set_page_config(page_title="PDF Specification Comparison", layout="wide")

st.title("PDF Specification Comparison Tool")

st.markdown("""
### Instructions:
1. Upload your Villa PDF specification
2. Upload your Factory PDF specification
3. Click 'Compare PDFs' to see the results
4. Download the comparison results as Excel
""")

# File uploaders
col1, col2 = st.columns(2)
with col1:
    villa_file = st.file_uploader("Upload Villa PDF", type=['pdf'])
with col2:
    factory_file = st.file_uploader("Upload Factory PDF", type=['pdf'])

if villa_file and factory_file:
    if st.button("Compare PDFs", type="primary"):
        with st.spinner("Comparing PDFs..."):
            try:
                # Extract text from PDFs
                villa_text = extract_text_from_pdf(villa_file)
                factory_text = extract_text_from_pdf(factory_file)
                
                # Compare PDFs
                results = compare_pdfs(villa_text, factory_text)
                
                # Display results
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                # Create download button for Excel file
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button(
                    label="Download Results as Excel",
                    data=output.getvalue(),
                    file_name="comparison_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
else:
    st.info("Please upload both PDF files to start comparison")

# Add footer with version info
st.markdown("---")
st.markdown("v1.0 - PDF Specification Comparison Tool")
