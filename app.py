import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO
import re

# [Previous data processing functions remain the same]

# Streamlit App
st.set_page_config(
    page_title="PDF Specification Extraction",
    page_icon="📑",
    layout="wide"
)

# Add custom styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .css-1v0mbdj {
        width: 100%;
    }
    .stDataFrame td {
        text-align: left !important;
        padding: 8px !important;
    }
    .stDataFrame th {
        text-align: left !important;
        padding: 8px !important;
        background-color: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.title("📑 Factory Specification PDF Analyzer")
st.markdown("""
    This tool extracts and analyzes factory specifications from PDF documents.
    Upload your factory specification PDF to get started.
""")

# File Upload Section
uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])

if uploaded_file is not None:
    # Process Button
    if st.button("Process PDF", type="primary"):
        with st.spinner("Processing PDF..."):
            try:
                # Read PDF
                pdf_reader = PdfReader(uploaded_file)
                text = ''
                for page in pdf_reader.pages:
                    text += page.extract_text() + '\n'
                
                # Extract data
                data = extract_structured_data(text)
                results_df = pd.DataFrame(data)
                
                # Format data
                formatted_df = format_dataframe(results_df)
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["📋 Data View", "🔍 Filtered View", "📊 Summary"])
                
                with tab1:
                    st.subheader("Extracted Specifications")
                    display_results(formatted_df)
                    
                    # Download buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        # Excel download
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            formatted_df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 Download Excel",
                            data=buffer.getvalue(),
                            file_name="specifications.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    with col2:
                        # CSV download
                        csv = formatted_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name="specifications.csv",
                            mime="text/csv"
                        )
                
                with tab2:
                    st.subheader("Filter Specifications")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_sections = st.multiselect(
                            "Filter by Section",
                            options=sorted(formatted_df['Section'].unique())
                        )
                    
                    with col2:
                        selected_features = st.multiselect(
                            "Filter by Feature",
                            options=sorted(formatted_df['Feature'].unique())
                        )
                    
                    # Apply filters
                    filtered_df = formatted_df.copy()
                    if selected_sections:
                        filtered_df = filtered_df[filtered_df['Section'].isin(selected_sections)]
                    if selected_features:
                        filtered_df = filtered_df[filtered_df['Feature'].isin(selected_features)]
                    
                    if selected_sections or selected_features:
                        st.dataframe(
                            filtered_df,
                            use_container_width=True,
                            hide_index=True
                        )
                
                with tab3:
                    st.subheader("Data Summary")
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Items", len(formatted_df))
                    with col2:
                        st.metric("Sections", len(formatted_df['Section'].unique()))
                    with col3:
                        st.metric("Features", len(formatted_df['Feature'].unique()))
                    
                    # Section breakdown
                    st.subheader("Items by Section")
                    section_counts = formatted_df['Section'].value_counts()
                    st.bar_chart(section_counts)
                    
                    # Feature breakdown
                    st.subheader("Items by Feature")
                    feature_counts = formatted_df['Feature'].value_counts().head(10)
                    st.bar_chart(feature_counts)
                
            except Exception as e:
                st.error(f"An error occurred while processing the PDF: {str(e)}")
else:
    st.info("👆 Please upload a factory specification PDF to begin analysis")

# Footer
st.markdown("---")
st.markdown("Tool version 1.0.0 | Made with Streamlit")
