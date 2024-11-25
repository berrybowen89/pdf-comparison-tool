import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO
import re

def extract_structured_data(text):
    """Extract data specifically from Feature, Option, Variant, Description, Quantity, Price columns"""
    lines = text.split('\n')
    structured_data = []
    current_section = None
    
    for line in lines:
        # Skip empty lines and page headers
        if not line.strip() or "Champion is a registered trademark" in line:
            continue
            
        # Check if line contains option code
        option_match = re.search(r'(OP\d{6})', line)
        
        # Try to extract structured data from line
        if "Feature" in line and "Option" in line:
            continue  # Skip header row
            
        # Handle section headers
        if line.strip().endswith('...') or line.strip() in [
            'Construction', 'Exterior', 'Windows', 'Electrical', 'Cabinets', 
            'Kitchen', 'Appliances', 'Interior', 'Plumbing/Heating'
        ]:
            current_section = line.strip().replace('...', '').strip()
            continue
            
        # Extract data from regular content lines
        parts = re.split(r'\s{2,}', line.strip())
        
        if len(parts) >= 2:  # Must have at least feature and option
            feature = parts[0].strip()
            
            # Skip if feature is just a number or page indicator
            if feature.isdigit() or "Page" in feature:
                continue
                
            data = {
                'Section': current_section,
                'Feature': feature,
                'Option': '',
                'Variant': '',
                'Description': '',
                'Quantity': '',
                'Price': ''
            }
            
            # Extract option code if present
            if option_match:
                data['Option'] = option_match.group(1)
                line = line.replace(option_match.group(1), '')
            
            # Try to extract variant, description, quantity and price
            remaining_parts = line.split()
            
            # Look for quantity patterns (e.g., "1 EA", "1LF", "143 LF")
            quantity_match = re.search(r'(\d+\s*(?:EA|LF|SF))', line)
            if quantity_match:
                data['Quantity'] = quantity_match.group(1)
            
            # Look for price patterns (Standard, or dollar amounts)
            price_match = re.search(r'(Standard|\d+\.\d{2})', line)
            if price_match:
                data['Price'] = price_match.group(1)
            
            # Extract variant if present (usually between option and description)
            variant_candidates = [p for p in remaining_parts if p in ['Nickel', 'White', 'Brown', 'Matte']]
            if variant_candidates:
                data['Variant'] = variant_candidates[0]
            
            # Everything else goes into description
            description_parts = []
            for part in remaining_parts:
                if part not in [data['Option'], data['Variant'], data['Quantity'], data['Price']]:
                    description_parts.append(part)
            
            data['Description'] = ' '.join(description_parts).strip()
            
            if data['Feature'] and (data['Option'] or data['Description']):
                structured_data.append(data)
    
    return structured_data

def compare_pdfs(villa_text, factory_text):
    """Compare PDF contents with focus on specified columns"""
    factory_data = extract_structured_data(factory_text)
    
    # Convert to DataFrame for easier handling
    df = pd.DataFrame(factory_data)
    
    # Clean up the data
    df = df.replace('', None)
    df = df.dropna(how='all', subset=['Option', 'Description'])
    
    return df

# Streamlit UI
st.set_page_config(page_title="PDF Specification Comparison", layout="wide")

st.title("PDF Specification Comparison Tool")

# File uploaders
villa_file = st.file_uploader("Upload Villa PDF", type=['pdf'])
factory_file = st.file_uploader("Upload Factory PDF", type=['pdf'])

if villa_file and factory_file:
    if st.button("Extract Specifications", type="primary"):
        try:
            # Extract text from PDFs
            factory_text = PdfReader(factory_file).pages
            factory_text = '\n'.join([page.extract_text() for page in factory_text])
            
            # Process and display results
            results_df = compare_pdfs(None, factory_text)  # Currently only processing factory PDF
            
            # Display results with better formatting
            st.dataframe(
                results_df,
                column_config={
                    "Section": st.column_config.TextColumn("Section", width=100),
                    "Feature": st.column_config.TextColumn("Feature", width=150),
                    "Option": st.column_config.TextColumn("Option", width=100),
                    "Variant": st.column_config.TextColumn("Variant", width=100),
                    "Description": st.column_config.TextColumn("Description", width=300),
                    "Quantity": st.column_config.TextColumn("Quantity", width=80),
                    "Price": st.column_config.TextColumn("Price", width=100),
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Add download button
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                results_df.to_excel(writer, index=False)
            
            st.download_button(
                label="Download as Excel",
                data=output.getvalue(),
                file_name="factory_specifications.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Display some statistics
            st.subheader("Summary")
            st.write(f"Total Items: {len(results_df)}")
            st.write(f"Sections Found: {len(results_df['Section'].unique())}")
            st.write(f"Options with Pricing: {len(results_df[results_df['Price'].notna()])}")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Full error details:", exc_info=True)

else:
    st.info("Please upload the PDF files to begin extraction")

# Add footer
st.markdown("---")
st.markdown("v2.0 - Specification Extraction Tool")
