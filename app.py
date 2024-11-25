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
        
        # Check for section headers
        if any(section in line for section in [
            'Construction', 'Exterior', 'Windows', 'Electrical', 'Cabinets', 
            'Kitchen', 'Appliances', 'Interior', 'Plumbing/Heating', 'Primary Bath',
            'Hall Bath', 'Utility Room', 'Floor Covering'
        ]):
            current_section = line.strip()
            continue
            
        # Skip header rows and footers
        if "Feature" in line and "Option" in line:
            continue
        if "Buyer:" in line or "Date:" in line or "Seller:" in line:
            continue
        if "Page" in line or line.strip().isdigit():
            continue
            
        # Split line by multiple spaces while preserving single spaces within phrases
        parts = [p.strip() for p in re.split(r'\s{2,}', line.strip()) if p.strip()]
        
        if parts:  # Only process non-empty lines
            data = {
                'Section': current_section or 'Miscellaneous',
                'Feature': parts[0] if parts else '',
                'Option': '',
                'Variant': '',
                'Description': '',
                'Quantity': '',
                'Price': ''
            }
            
            # Extract option code
            if option_match:
                data['Option'] = option_match.group(1)
                
            # Look for quantity patterns
            qty_match = re.search(r'(\d+\s*(?:EA|LF|SF))', line)
            if qty_match:
                data['Quantity'] = qty_match.group(1)
                
            # Look for price patterns
            price_match = re.search(r'(Standard|\d+\.\d{2})', line)
            if price_match:
                data['Price'] = price_match.group(1)
                
            # Look for variants
            variants = ['Nickel', 'White', 'Brown', 'Matte', 'Expresso', 
                       'Toasted Almond', 'Linen Ruffle', 'Dual Black', 'Flint Rock']
            for variant in variants:
                if variant in line:
                    data['Variant'] = variant
                    break
                    
            # Extract description
            desc_parts = []
            for part in parts[1:]:  # Skip feature name
                if part != data['Option'] and part != data['Variant'] and part != data['Quantity'] and part != data['Price']:
                    desc_parts.append(part)
            data['Description'] = ' '.join(desc_parts).strip()
            
            # Only add if we have meaningful data
            if data['Feature'] and (data['Option'] or data['Description']):
                structured_data.append(data)
    
    return structured_data

def compare_pdfs(factory_text):
    """Process factory PDF contents"""
    factory_data = extract_structured_data(factory_text)
    
    # Convert to DataFrame
    df = pd.DataFrame(factory_data)
    
    # Clean up the data
    df = df.fillna('')  # Replace NaN with empty string
    
    return df

# Streamlit UI
st.set_page_config(page_title="PDF Specification Extraction", layout="wide")

st.title("PDF Specification Extraction Tool")

# File uploader
factory_file = st.file_uploader("Upload Factory PDF", type=['pdf'])

if factory_file:
    if st.button("Extract Specifications", type="primary"):
        try:
            # Extract text from PDF
            factory_text = ''
            pdf_reader = PdfReader(factory_file)
            for page in pdf_reader.pages:
                factory_text += page.extract_text() + '\n'
            
            # Process and display results
            results_df = compare_pdfs(factory_text)
            
            # Display results with formatting
            st.dataframe(
                results_df,
                column_config={
                    "Section": st.column_config.TextColumn("Section", width=120),
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
            
            # Display statistics
            st.subheader("Summary")
            st.write(f"Total Items: {len(results_df)}")
            st.write(f"Sections Found: {len(results_df['Section'].unique())}")
            st.write(f"Options with Pricing: {len(results_df[results_df['Price'] != ''])}")
            
            # Display sections found
            st.subheader("Sections Found")
            st.write(", ".join(sorted(results_df['Section'].unique())))
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Error details:", exc_info=True)

else:
    st.info("Please upload the factory PDF file to begin extraction")

# Add footer
st.markdown("---")
st.markdown("v2.1 - Specification Extraction Tool")
