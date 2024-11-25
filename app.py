import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io
import pandas as pd
from difflib import SequenceMatcher

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

def read_file(file):
    try:
        if file.type == "application/pdf":
            pdf_reader = pypdf.PdfReader(file)
            return "\n".join(page.extract_text() for page in pdf_reader.pages)
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(file)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        else:  # txt files
            return file.getvalue().decode('utf-8')
    except Exception as e:
        st.error(f"Error reading file {file.name}: {str(e)}")
        return ""

# Create two columns for file uploads
col1, col2 = st.columns(2)

with col1:
    st.subheader("Quote 1")
    quote1_file = st.file_uploader(
        "Upload first quote",
        type=['pdf', 'docx', 'txt'],
        key="quote1_uploader"
    )
    if quote1_file:
        st.session_state.quote1 = {
            'name': quote1_file.name,
            'content': read_file(quote1_file)
        }
        st.success(f"Quote 1 uploaded: {quote1_file.name}")
        with st.expander("Preview Quote 1"):
            st.text(st.session_state.quote1['content'][:1000] + "...")

with col2:
    st.subheader("Quote 2")
    quote2_file = st.file_uploader(
        "Upload second quote",
        type=['pdf', 'docx', 'txt'],
        key="quote2_uploader"
    )
    if quote2_file:
        st.session_state.quote2 = {
            'name': quote2_file.name,
            'content': read_file(quote2_file)
        }
        st.success(f"Quote 2 uploaded: {quote2_file.name}")
        with st.expander("Preview Quote 2"):
            st.text(st.session_state.quote2['content'][:1000] + "...")

# Compare button
if st.button("Compare Quotes") and st.session_state.quote1 and st.session_state.quote2:
    with st.spinner("Performing detailed analysis with Claude 3 Opus..."):
        try:
            # First pass: Extract structured data
            extraction_prompt = f"""
            Analyze these two sales quotes and provide a detailed line-by-line comparison.
            Extract the following information in a structured JSON format:

            1. Line items with their details:
               - Item description
               - Price in both quotes
               - Quantity in both quotes
               - Specifications in both quotes
               - Whether it appears in both quotes
               - Whether pricing matches
               - Whether specifications match
               - Percentage price difference (if applicable)

            2. Also identify:
               - Terms and conditions differences
               - Delivery terms
               - Warranty information
               - Payment terms
               - Any special offers or discounts

            Quote 1 ({st.session_state.quote1['name']}):
            {st.session_state.quote1['content']}

            Quote 2 ({st.session_state.quote2['name']}):
            {st.session_state.quote2['content']}

            Format the response as structured data that can be directly converted to a table.
            Include ALL items from both quotes, using "Not Present" for missing items.
            """
            
            # Use Claude 3 Opus for the initial analysis
            initial_response = st.session_state.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": extraction_prompt
                }]
            )
            
            # Create tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs([
                "Comparison Table", 
                "Detailed Analysis", 
                "Terms & Conditions", 
                "Executive Summary"
            ])
            
            with tab1:
                st.markdown("### Line Item Comparison")
                
                # Apply custom styling for the table
                st.markdown("""
                <style>
                .match { color: green; font-weight: bold; }
                .mismatch { color: red; font-weight: bold; }
                .highlight { background-color: #f0f2f6; }
                </style>
                """, unsafe_allow_html=True)
                
                # Ask Claude to format the comparison specifically for visualization
                viz_prompt = """
                Based on the analysis above, create a comparison table with the following columns:
                1. Item Description
                2. Quote 1 Price
                3. Quote 2 Price
                4. Price Difference %
                5. Match Status (✓ or ✗)
                6. Notes
                
                Format this as a markdown table.
                """
                
                viz_response = st.session_state.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4096,
                    messages=[
                        {"role": "assistant", "content": initial_response.content[0].text},
                        {"role": "user", "content": viz_prompt}
                    ]
                )
                
                # Display the formatted table
                st.markdown(viz_response.content[0].text)
                
                # Add a download button for the comparison
                st.download_button(
                    "Download Comparison as CSV",
                    viz_response.content[0].text,
                    "quote_comparison.csv",
                    "text/csv"
                )
            
            with tab2:
                st.markdown("### Detailed Analysis")
                
                analysis_prompt = """
                Based on the comparison above, provide a detailed analysis including:
                1. Major price differences and their impact
                2. Specification variations and their significance
                3. Value analysis comparing both quotes
                4. Potential negotiation points
                5. Technical advantages/disadvantages
                """
                
                analysis_response = st.session_state.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4096,
                    messages=[
                        {"role": "assistant", "content": initial_response.content[0].text},
                        {"role": "user", "content": analysis_prompt}
                    ]
                )
                
                st.markdown(analysis_response.content[0].text)
            
            with tab3:
                st.markdown("### Terms & Conditions Comparison")
                
                terms_prompt = """
                Compare the terms and conditions of both quotes, including:
                1. Payment terms
                2. Delivery conditions
                3. Warranty terms
                4. Support/maintenance terms
                5. Legal requirements and compliance
                Present this in a clear, structured format.
                """
                
                terms_response = st.session_state.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4096,
                    messages=[
                        {"role": "assistant", "content": initial_response.content[0].text},
                        {"role": "user", "content": terms_prompt}
                    ]
                )
                
                st.markdown(terms_response.content[0].text)
            
            with tab4:
                st.markdown("### Executive Summary")
                
                summary_prompt = """
                Provide a concise executive summary of the comparison, including:
                1. Total cost comparison
                2. Key differentiators
                3. Best value analysis
                4. Recommended choice with justification
                Limit this to key points that would be relevant for decision makers.
                """
                
                summary_response = st.session_state.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4096,
                    messages=[
                        {"role": "assistant", "content": initial_response.content[0].text},
                        {"role": "user", "content": summary_prompt}
                    ]
                )
                
                st.markdown(summary_response.content[0].text)
                
                # Add key metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Price Difference", "Calculated from comparison")
                with col2:
                    st.metric("Number of Matching Items", "From analysis")
                with col3:
                    st.metric("Value Score", "Based on analysis")

        except Exception as e:
            st.error(f"Error in comparison: {str(e)}")

# Clear button
if st.button("Clear All"):
    st.session_state.quote1 = None
    st.session_state.quote2 = None
    st.session_state.comparison_results = None
    st.rerun()

# Footer with legend and information
st.markdown("---")
st.markdown("""
    **Legend:**
    - ✓ : Exact match between quotes
    - ✗ : Difference found
    - Percentages show price differences (Quote 2 vs Quote 1)
    
    **Note:** Analysis performed using Claude 3 Opus for maximum accuracy
""")
