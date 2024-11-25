import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io

# Streamlit page config
st.set_page_config(page_title="Claude Document Processor", page_icon="📄")

# Initialize Streamlit page
st.title("Claude Document Processor")

# Secure API key handling
try:
    if 'anthropic_client' not in st.session_state:
        anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.session_state.anthropic_client = Anthropic(api_key=anthropic_api_key)
except Exception as e:
    st.error("Please configure your API key in Streamlit secrets")
    st.stop()

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

# File uploader
uploaded_file = st.file_uploader("Upload a document (PDF, DOCX, or TXT)", type=['pdf', 'docx', 'txt'])

if uploaded_file:
    # Extract text based on file type
    try:
        if uploaded_file.type == "application/pdf":
            text = read_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = read_docx(uploaded_file)
        else:  # txt files
            text = read_txt(uploaded_file)
        
        st.success("Document uploaded successfully!")
        
        # User question about the document
        user_question = st.text_input(
            "What would you like to know about this document?",
            placeholder="e.g., 'Summarize this document' or 'What are the main points?'"
        )
        
        if user_question:
            with st.spinner("Processing..."):
                try:
                    # Create message with document content and question
                    response = st.session_state.anthropic_client.messages.create(
                        model="claude-3-opus-20240229",
                        max_tokens=1000,
                        messages=[
                            {
                                "role": "user",
                                "content": f"Here's a document to analyze:\n\n{text}\n\nQuestion: {user_question}"
                            }
                        ]
                    )
                    
                    # Display response
                    st.write("### Claude's Response:")
                    st.write(response.content[0].text)
                    
                except Exception as e:
                    st.error(f"Error processing request: {str(e)}")
    
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")

# Add requirements to requirements.txt:
# streamlit
# anthropic
# pypdf
# python-docx
