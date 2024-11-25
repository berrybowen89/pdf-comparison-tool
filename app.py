import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO
import re

def extract_text_from_pdf(pdf_file):
    """Improved PDF text extraction"""
    pdf_reader = PdfReader(pdf_file)
    full_text = []
    
    for page in pdf_reader.pages:
        text = page.extract_text()
        
        # Split into lines and process each line
        lines = text.split('\n')
        for line in lines:
            # Clean the line
            line = line.strip()
            
            # Skip truly empty lines and page numbers only
            if not line or (line.isdigit() and len(line) < 3):
                continue
            
            # Keep lines with option codes
            if 'OP' in line:
                full_text.append(line)
                continue
                
            # Keep lines with specific keywords
            if any(keyword in line.upper() for keyword in [
                'MODEL', 'TYPE', 'SIZE', 'CONSTRUCTION', 'ROOF', 'FEATURE',
                'OPTION', 'DESCRIPTION', 'QUANTITY', 'CABINET', 'WINDOW',
                'DOOR', 'FLOOR', 'PAINT', 'TRIM', 'BATHROOM', 'KITCHEN',
                'ELECTRICAL', 'PLUMBING', 'APPLIANCE'
            ]):
                full_text.append(line)
                continue
                
            # Keep lines with measurements
            if re.search(r'\d+["\']|\d+x\d+|\d+\s*(?:feet|ft|inch|in)', line, re.IGNORECASE):
                full_text.append(line)
                continue
                
            # Keep lines with key-value pairs
            if ':' in line:
                full_text.append(line)
                continue
                
            # Keep lines with standard measurements
            if re.search(r'\d+\'.*\d+\"|\d+\s*(?:SF|LF|EA)|\$\s*\d+', line):
                full_text.append(line)
                continue
                
            # Keep lines with color specifications
            if any(color in line.lower() for color in ['white', 'black', 'brown', 'grey', 'gray', 'beige', 'nickel', 'steel']):
                full_text.append(line)
                continue
                
            # Keep lines with pricing information
            if re.search(r'\$|\bEA\b|\bSTANDARD\b|\bUPGRADE\b', line):
                full_text.append(line)
                continue
                
            # Keep lines with specification details
            if len(line.split()) >= 3:  # Line has substantial content
                full_text.append(line)

    # Remove duplicate lines while preserving order
    seen = set()
    unique_text = []
    for line in full_text:
        if line not in seen:
            seen.add(line)
            unique_text.append(line)
    
    return '\n'.join(unique_text)

def normalize_text(text):
    """Enhanced text normalization"""
    if text is None:
        return ""
    # Remove special characters but keep spaces and numbers
    text = re.sub(r'[^\w\s\d]', ' ', text.lower())
    # Replace multiple spaces with single space
    text = ' '.join(text.split())
    return text

def enhanced_fuzzy_match(text1, text2, threshold=75):
    """Enhanced fuzzy matching"""
    if not text1 or not text2:
        return False
    
    # Normalize texts
    norm_text1 = normalize_text(str(text1))
    norm_text2 = normalize_text(str(text2))
    
    # Handle option codes specially
    if 'op' in norm_text1.lower() and 'op' in norm_text2.lower():
        op_score = fuzz.partial_ratio(norm_text1, norm_text2)
        if op_score >= 90:  # Higher threshold for option codes
            return True
    
    # Calculate different fuzzy ratios
    ratio = fuzz.ratio(norm_text1, norm_text2)
    partial_ratio = fuzz.partial_ratio(norm_text1, norm_text2)
    token_sort_ratio = fuzz.token_sort_ratio(norm_text1, norm_text2)
    token_set_ratio = fuzz.token_set_ratio(norm_text1, norm_text2)
    
    # Weighted average of different metrics
    weighted_score = (
        ratio * 0.25 + 
        partial_ratio * 0.35 + 
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
    processed_factory_lines = set()
    
    # Process Villa PDF lines
    for villa_line in villa_lines:
        villa_line = villa_line.strip()
        if not villa_line:
            continue
            
        if ':' in villa_line:
            option, value = villa_line.split(':', 1)
        else:
            option = "Specification"
            value = villa_line
            
        option = option.strip()
        value = value.strip()
        
        if not value:
            continue
        
        # Find best match in factory text
        best_match = None
        best_score = 0
        best_line = None
        
        for factory_line in factory_lines:
            factory_line = factory_line.strip()
            if not factory_line or factory_line in processed_factory_lines:
                continue
            
            # Special handling for option codes
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
        
        if best_match and best_score > 45:  # Minimum threshold for considering a match
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
                
                # Debug view
                with st.expander("Show Extracted Text (Debug)"):
                    st.subheader("Villa PDF Text")
                    st.text(villa_text)
                    st.subheader("Factory PDF Text")
                    st.text(factory_text)
                    
                    # Show line counts
                    st.subheader("Line Counts")
                    st.text(f"Villa PDF: {len(villa_text.split('\n'))} lines")
                    st.text(f"Factory PDF: {len(factory_text.split('\n'))} lines")
                
                # Compare PDFs
                results = compare_pdfs(villa_text, factory_text)
                
                # Display results
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                # Add summary statistics
                st.subheader("Comparison Summary")
                total_comparisons = len(results)
                matches = sum(1 for r in results if r['Match'] == "✔️")
                st.write(f"Total Comparisons: {total_comparisons}")
                st.write(f"Matches Found: {matches}")
                st.write(f"Match Rate: {(matches/total_comparisons*100):.1f}%")
                
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
                st.error("Full error details:", exc_info=True)
else:
    st.info("Please upload both PDF files to start comparison")

# Add footer with version info
st.markdown("---")
st.markdown("v1.2 - Enhanced PDF Specification Comparison Tool")
