import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO
import re

def extract_construction_section(line):
    """Special handling for Construction and Construction Type HUD sections"""
    data = {
        'Feature': '',
        'Option': '',
        'Variant': '',
        'Description': '',
        'Quantity': '',
        'Price': ''
    }
    
    # Look for option code
    option_match = re.search(r'(OP\d{6})', line)
    if option_match:
        data['Option'] = option_match.group(1)
        line = line.replace(option_match.group(1), '').strip()
    
    # Look for price at the end
    price_match = re.search(r'(\$?\d+\.\d{2}|Standard)$', line.strip())
    if price_match:
        data['Price'] = price_match.group(1)
        line = line[:line.rfind(price_match.group(1))].strip()
    
    # Split remaining text
    parts = [p.strip() for p in re.split(r'\s{2,}', line.strip()) if p.strip()]
    
    if parts:
        # First part is typically the feature
        data['Feature'] = parts[0]
        
        # Handle quantity if present (typically at the end before price)
        qty_match = re.search(r'(\d+\s*(?:EA|LF|SF))', line)
        if qty_match:
            data['Quantity'] = qty_match.group(1)
            parts = [p for p in parts if qty_match.group(1) not in p]
        
        # Everything else goes into description
        if len(parts) > 1:
            data['Description'] = ' '.join(parts[1:])
    
    return data

def extract_structured_data(text):
    """Extract data specifically from Feature, Option, Variant, Description, Quantity, Price columns"""
    lines = text.split('\n')
    structured_data = []
    current_section = None
    
    for line in lines:
        # Skip empty lines and page headers
        if not line.strip() or "Champion is a registered trademark" in line:
            continue
            
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
        
        # Special handling for Construction sections
        if current_section and ('Construction' in current_section or 'HUD' in current_section):
            data = extract_construction_section(line)
            data['Section'] = current_section
            if data['Feature']:  # Only add if we have a feature
                structured_data.append(data)
            continue
            
        # Regular processing for other sections
        # Look for option code first
        option_match = re.search(r'(OP\d{6})', line)
        option_code = option_match.group(1) if option_match else ''
        
        # Remove option code from line for further processing
        if option_code:
            line = line.replace(option_code, '')
        
        # Look for price at the end
        price_match = re.search(r'(\$?\d+\.\d{2}|Standard)$', line.strip())
        price = price_match.group(1) if price_match else ''
        if price:
            line = line[:line.rfind(price)].strip()
        
        # Look for quantity
        qty_pattern = r'(\d+\s*(?:EA|LF|SF))'
        qty_match = re.search(qty_pattern, line)
        quantity = qty_match.group(1) if qty_match else ''
        if quantity:
            line = line.replace(quantity, '')
        
        # Define known variants
        variants = ['Nickel', 'White', 'Brown', 'Matte', 'Expresso', 
                   'Toasted Almond', 'Linen Ruffle', 'Dual Black', 'Flint Rock']
        
        # Look for variant
        found_variant = ''
        for variant in variants:
            if variant in line:
                found_variant = variant
                line = line.replace(variant, '')
                break
        
        # Split remaining text into feature and description
        parts = [p.strip() for p in re.split(r'\s{2,}', line.strip()) if p.strip()]
        
        if parts:
            feature = parts[0]
            # Join remaining parts as description, excluding already extracted information
            description = ' '.join(parts[1:]).strip()
            
            data = {
                'Section': current_section or 'Miscellaneous',
                'Feature': feature,
                'Option': option_code,
                'Variant': found_variant,
                'Description': description,
                'Quantity': quantity,
                'Price': price
            }
            
            # Only add if we have meaningful data
            if data['Feature']:
                structured_data.append(data)
    
    return structured_data

def compare_pdfs(factory_text):
    """Process factory PDF contents"""
    factory_data = extract_structured_data(factory_text)
    
    # Convert to DataFrame
    df = pd.DataFrame(factory_data)
    
    # Clean up the data
    df = df.fillna('')  # Replace NaN with empty string
    
    # Clean up any extra whitespace in all columns
    for column in df.columns:
        df[column] = df[column].str.strip()
    
    return df

# Streamlit UI
st.set_page_config(page_title="PDF Specification Extraction", layout="wide")

st.title("PDF Specification Extraction Tool")

# File uploader
uploaded_file = st.file_uploader("Upload Factory PDF", type=['pdf'])

if uploaded_file is not None:
    if st.button("Process PDF", type="primary"):
        try:
            # Read PDF content
            pdf_reader = PdfReader(uploaded_file)
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            # Process the text content
            results_df = compare_pdfs(text_content)
            
            # Display the results in a table
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
                label="Download Excel File",
                data=output.getvalue(),
                file_name="extracted_specifications.xlsx",
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
            st.error(f"An error occurred while processing the PDF: {str(e)}")
else:
    st.info("Please upload a PDF file to begin")

# Add footer with version
st.markdown("---")
st.markdown("v2.2 - PDF Specification Extraction Tool")
