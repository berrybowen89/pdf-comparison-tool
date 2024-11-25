import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO
import re

def extract_text_from_pdf(pdf_file):
    """Enhanced text extraction from PDF"""
    pdf_reader = PdfReader(pdf_file)
    full_text = []
    
    for page in pdf_reader.pages:
        text = page.extract_text()
        
        # Split text into lines and process each line
        lines = text.split('\n')
        for line in lines:
            # Clean up the line
            line = line.strip()
            
            # Skip empty lines and page numbers
            if not line or line.isdigit():
                continue
                
            # Extract Feature/Option patterns
            if "OP" in line:
                # Handle option codes with descriptions
                parts = re.split(r'(OP\d{6})', line)
                if len(parts) > 1:
                    for i in range(1, len(parts), 2):
                        option_code = parts[i]
                        description = parts[i+1].strip() if i+1 < len(parts) else ""
                        if description:
                            full_text.append(f"{option_code} {description}")
            
            # Extract key-value pairs
            elif ':' in line:
                full_text.append(line)
            
            # Extract table-like content
            elif any(keyword in line.upper() for keyword in ['FEATURE', 'OPTION', 'DESCRIPTION', 'QUANTITY']):
                full_text.append(line)
            
            # Extract important specifications
            elif any(keyword in line.upper() for keyword in ['MODEL', 'TYPE', 'SIZE', 'CONSTRUCTION', 'ROOF']):
                full_text.append(line)

    return '\n'.join(full_text)

def normalize_text(text):
    """Enhanced text normalization"""
    if text is None:
        return ""
    # Remove special characters but keep spaces and numbers
    text = re.sub(r'[^\w\s\d]', ' ', text.lower())
    # Normalize whitespace
    text = ' '.join(text.split())
    return text

def enhanced_fuzzy_match(text1, text2, threshold=75):
    """Enhanced fuzzy matching with better handling of specifications"""
    if not text1 or not text2:
        return False
    
    # Normalize texts
    norm_text1 = normalize_text(str(text1))
    norm_text2 = normalize_text(str(text2))
    
    # Calculate different fuzzy ratios
    ratio = fuzz.ratio(norm_text1, norm_text2)
    partial_ratio = fuzz.partial_ratio(norm_text1, norm_text2)
    token_sort_ratio = fuzz.token_sort_ratio(norm_text1, norm_text2)
    token_set_ratio = fuzz.token_set_ratio(norm_text1, norm_text2)
    
    # Weighted average of different metrics
    weighted_score = (
        ratio * 0.3 + 
        partial_ratio * 0.3 + 
        token_sort_ratio * 0.2 +
        token_set_ratio * 0.2
    )
    
    return weighted_score >= threshold

def compare_pdfs(villa_text, factory_text):
    """Enhanced PDF comparison"""
    # Split texts into lines
    villa_lines = villa_text.split('\n')
    factory_lines = factory_text.split('\n')
    
    comparison_results = []
    processed_factory_lines = set()  # Track processed factory lines
    
    # Process Villa PDF lines
    for villa_line in villa_lines:
        if ':' in villa_line:
            option, value = villa_line.split(':', 1)
            option = option.strip()
            value = value.strip()
            
            if not value:  # Skip empty values
                continue
            
            # Find best match in factory text
            best_match = None
            best_score = 0
            best_line = None
            
            for factory_line in factory_lines:
                if factory_line in processed_factory_lines:
                    continue
                    
                if len(factory_line.split()) >= 2:  # Ensure line has content
                    # Try to match option codes if present
                    if "OP" in factory_line and "OP" in value:
                        op_score = fuzz.partial_ratio(value, factory_line)
                        if op_score > best_score:
                            best_score = op_score
                            best_match = factory_line
                            best_line = factory_line
                    else:
                        # Regular content matching
                        score = fuzz.token_set_ratio(value, factory_line)
                        if score > best_score:
                            best_score = score
                            best_match = factory_line
                            best_line = factory_line
            
            if best_match:
                processed_factory_lines.add(best_line)
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
                
                # Display extracted text for debugging
                with st.expander("Show Extracted Text (Debug)"):
                    st.subheader("Villa PDF Text")
                    st.text(villa_text)
                    st.subheader("Factory PDF Text")
                    st.text(factory_text)
                
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
st.markdown("v1.1 - Enhanced PDF Specification Comparison Tool")
