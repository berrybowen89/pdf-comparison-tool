import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io

# Streamlit page config
st.set_page_config(page_title="Sales Quote Comparison", page_icon="💼", layout="wide")

# Initialize Streamlit page
st.title("Sales Quote Comparison Tool")
st.markdown("Upload two sales quotes to get a detailed line-by-line comparison")

# Secure API key handling
try:
    if 'anthropic_client' not in st.session_state:
        anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.session_state.anthropic_client = Anthropic(api_key=anthropic_api_key)
except Exception as e:
    st.error("Please configure your API key in Streamlit secrets")
    st.stop()

# Initialize session state for documents
if 'quote1' not in st.session_state:
    st.session_state.quote1 = None
if 'quote2' not in st.session_state:
    st.session_state.quote2 = None

def read_pdf(file):
    pdf_reader = pypdf.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def read_docx(file):
    doc = docx.Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def read_txt(file):
    return file.getvalue().decode('utf-8')

def read_file(file):
    if file.type == "application/pdf":
        return read_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return read_docx(file)
    else:  # txt files
        return read_txt(file)

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

# Comparison Options
st.subheader("Comparison Options")
comparison_type = st.selectbox(
    "What type of comparison would you like?",
    options=[
        "Full line-by-line comparison",
        "Compare prices only",
        "Compare specifications only",
        "Compare terms and conditions",
        "Highlight key differences",
        "Summarize advantages of each quote"
    ]
)

specific_focus = st.multiselect(
    "Any specific aspects to focus on?",
    options=[
        "Pricing structure",
        "Delivery terms",
        "Warranty details",
        "Payment terms",
        "Technical specifications",
        "Service level agreements"
    ]
)

# Compare button
if st.button("Compare Quotes") and st.session_state.quote1 and st.session_state.quote2:
    st.write("### Comparison Results")
    
    with st.spinner("Analyzing quotes..."):
        try:
            # Prepare the prompt based on comparison type and specific focus
            prompt = f"""
            I have two sales quotes to compare. Please provide a detailed {comparison_type}.
            
            Focus specifically on these aspects: {', '.join(specific_focus) if specific_focus else 'all aspects'}
            
            Quote 1 ({st.session_state.quote1['name']}):
            {st.session_state.quote1['content']}
            
            Quote 2 ({st.session_state.quote2['name']}):
            {st.session_state.quote2['content']}
            
            Please provide:
            1. A line-by-line comparison of key elements
            2. Price comparison and analysis
            3. Notable differences in terms and conditions
            4. Advantages and disadvantages of each quote
            5. Recommendations based on the comparison
            
            Format the response in a clear, structured way with appropriate headers and bullet points.
            """
            
            response = st.session_state.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Display results in tabs
            tab1, tab2, tab3 = st.tabs(["Detailed Comparison", "Summary", "Raw Text"])
            
            with tab1:
                st.markdown(response.content[0].text)
            
            with tab2:
                st.markdown("""
                ### Quick Summary
                """)
                
                # Create a second prompt for a brief summary
                summary_prompt = f"""
                Based on the comparison above, provide a very brief executive summary (3-4 bullet points)
                of the key differences between these quotes and a clear recommendation.
                Focus on price, value, and key differentiators.
                """
                
                summary_response = st.session_state.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": response.content[0].text},
                        {"role": "user", "content": summary_prompt}
                    ]
                )
                
                st.markdown(summary_response.content[0].text)
            
            with tab3:
                col1, col2 = st.columns(2)
                with col1:
                    st.text_area("Quote 1 Raw Text", st.session_state.quote1['content'], height=300)
                with col2:
                    st.text_area("Quote 2 Raw Text", st.session_state.quote2['content'], height=300)
            
        except Exception as e:
            st.error(f"Error processing comparison: {str(e)}")

# Clear button
if st.button("Clear All"):
    st.session_state.quote1 = None
    st.session_state.quote2 = None
    st.rerun()

# Add a footer with usage information
st.markdown("---")
st.markdown("""
    **Usage Notes:**
    - Upload two sales quotes in PDF, DOCX, or TXT format
    - Select the type of comparison you need
    - Choose specific aspects to focus on
    - Get a detailed comparison with recommendations
    - Using Claude 3.5 Sonnet for optimal analysis
""")
