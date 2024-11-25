import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO
import re

def process_sub_descriptions(main_desc, sub_descs):
    """Combine main description with sub-descriptions in a clean format"""
    if not sub_descs:
        return main_desc
    
    # Clean up sub-descriptions and combine with main description
    clean_subs = [sub.strip().strip('-~*').strip() for sub in sub_descs]
    full_desc = [main_desc] + clean_subs if main_desc else clean_subs
    return ' | '.join(filter(None, full_desc))

def extract_structured_data(text):
    """Extract data with properly formatted descriptions"""
    lines = text.split('\n')
    structured_data = []
    current_section = None
    current_item = None
    sub_descriptions = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and headers/footers
        if (not line or 
            "Champion is a registered trademark" in line or
            "Buyer:" in line or 
            "Date:" in line or 
            "Page" in line):
            continue
            
        # Check for section headers
        if any(section in line for section in [
            'Construction', 'Exterior', 'Windows', 'Electrical', 'Cabinets', 
            'Kitchen', 'Appliances', 'Interior', 'Plumbing/Heating', 'Primary Bath',
            'Hall Bath', 'Utility Room', 'Floor Covering', 'Countertop'
        ]):
            # Save previous item if exists
            if current_item:
                current_item['Description'] = process_sub_descriptions(
                    current_item['Description'], sub_descriptions
                )
                structured_data.append(current_item)
                current_item = None
                sub_descriptions = []
            
            current_section = line.strip()
            continue
        
        # Check if line is a sub-description
        if line.strip().startswith(('-', '~', '**', '..')):
            if current_item:
                sub_descriptions.append(line)
            continue
        
        # Skip header rows
        if "Feature" in line and "Option" in line:
            continue
        
        # Try to extract main item data
        feature_match = re.match(r'^([A-Z][A-Z0-9/\s]+(?:\s*&\s*[A-Z]+)*)', line)
        option_match = re.search(r'(OP\d{6})', line)
        
        if feature_match:
            # Save previous item if exists
            if current_item:
                current_item['Description'] = process_sub_descriptions(
                    current_item['Description'], sub_descriptions
                )
                structured_data.append(current_item)
            
            # Reset for new item
            sub_descriptions = []
            feature = feature_match.group(1).strip()
            
            # Initialize new item
            current_item = {
                'Section': current_section or 'Miscellaneous',
                'Feature': feature,
                'Option': '',
                'Variant': '',
                'Description': '',
                'Quantity': '',
                'Price': ''
            }
            
            # Extract option code
            if option_match:
                current_item['Option'] = option_match.group(1)
                line = line.replace(current_item['Option'], '')
            
            # Extract quantity
            qty_match = re.search(r'(\d+\s*(?:EA|LF|SF|D\$))', line)
            if qty_match:
                current_item['Quantity'] = qty_match.group(1).strip()
                line = line.replace(qty_match.group(1), '')
            
            # Extract price
            price_match = re.search(r'(Standard|\d+\.\d{2}|-?\d+,\d+\.\d{2})', line)
            if price_match:
                current_item['Price'] = price_match.group(1).strip()
                line = line.replace(price_match.group(1), '')
            
            # Extract variant
            variants = ['Nickel', 'White', 'Brown', 'Matte', 'Expresso', 
                       'Toasted Almond', 'Linen Ruffle', 'Dual Black', 'Flint Rock',
                       'Chandler Oak']
            for variant in variants:
                if variant in line:
                    current_item['Variant'] = variant
                    line = line.replace(variant, '')
                    break
            
            # Clean up description
            description = ' '.join(line.split())
            description = re.sub(r'\s+', ' ', description).strip()
            description = re.sub(r'^[^a-zA-Z0-9]*|[^a-zA-Z0-9]*$', '', description)
            
            if description and not description.isspace():
                current_item['Description'] = description
    
    # Add last item if exists
    if current_item:
        current_item['Description'] = process_sub_descriptions(
            current_item['Description'], sub_descriptions
        )
        structured_data.append(current_item)
    
    return structured_data

def process_pdf(pdf_file):
    """Process uploaded PDF file"""
    try:
        # Extract text from PDF
        pdf_reader = PdfReader(pdf_file)
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text() + '\n'
        
        # Extract structured data
        data = extract_structured_data(text)
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

# Page configuration
st.set_page_config(
    page_title="PDF Specification Extraction",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .css-1v0mbdj {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# Main UI
st.title("📄 PDF Specification Extraction Tool")

st.markdown("""
Upload a factory specification PDF to extract and analyze its contents.
The tool will organize the data into a structured format with proper handling of specifications and sub-descriptions.
""")

# File uploader
uploaded_file = st.file_uploader("Upload Factory PDF", type=['pdf'])

if uploaded_file:
    # Add processing button
    if st.button("Extract Specifications", type="primary"):
        with st.spinner("Processing PDF..."):
            # Process the PDF
            results_df = process_pdf(uploaded_file)
            
            if results_df is not None:
                # Show success message
                st.success("PDF processed successfully!")
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["📊 Data View", "🔍 Filtered View", "📈 Summary"])
                
                with tab1:
                    st.subheader("Complete Dataset")
                    st.dataframe(
                        results_df,
                        column_config={
                            "Section": st.column_config.TextColumn("Section", width=120),
                            "Feature": st.column_config.TextColumn("Feature", width=150),
                            "Option": st.column_config.TextColumn("Option", width=100),
                            "Variant": st.column_config.TextColumn("Variant", width=100),
                            "Description": st.column_config.TextColumn("Description", width=400),
                            "Quantity": st.column_config.TextColumn("Quantity", width=80),
                            "Price": st.column_config.TextColumn("Price", width=100),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                
                with tab2:
                    st.subheader("Filter Data")
                    col1, col2 = st.columns(2)
                    with col1:
                        selected_section = st.multiselect(
                            "Filter by Section",
                            options=sorted(results_df['Section'].unique())
                        )
                    with col2:
                        selected_feature = st.multiselect(
                            "Filter by Feature",
                            options=sorted(results_df['Feature'].unique())
                        )
                    
                    # Apply filters
                    filtered_df = results_df.copy()
                    if selected_section:
                        filtered_df = filtered_df[filtered_df['Section'].isin(selected_section)]
                    if selected_feature:
                        filtered_df = filtered_df[filtered_df['Feature'].isin(selected_feature)]
                    
                    if selected_section or selected_feature:
                        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
                
                with tab3:
                    st.subheader("Data Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Items", len(results_df))
                    with col2:
                        st.metric("Unique Sections", len(results_df['Section'].unique()))
                    with col3:
                        st.metric("Unique Features", len(results_df['Feature'].unique()))
                    
                    # Section breakdown
                    st.subheader("Items per Section")
                    section_counts = results_df['Section'].value_counts()
                    st.bar_chart(section_counts)
                
                # Download options
                st.subheader("Download Data")
                col1, col2 = st.columns(2)
                with col1:
                    # Excel download
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        results_df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_buffer.getvalue(),
                        file_name="specifications.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # CSV download
                    csv_buffer = BytesIO()
                    results_df.to_csv(csv_buffer, index=False)
                    
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_buffer.getvalue(),
                        file_name="specifications.csv",
                        mime="text/csv"
                    )

else:
    st.info("👆 Please upload a PDF file to begin extraction")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit")
