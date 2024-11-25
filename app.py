import streamlit as st
from anthropic import Anthropic
import pypdf
import docx
import io

# Streamlit page config
st.set_page_config(page_title="Claude Multi-Document Processor", page_icon="📚", layout="wide")

# Initialize Streamlit page
st.title("Claude Multi-Document Processor")

# Secure API key handling
try:
    if 'anthropic_client' not in st.session_state:
        anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.session_state.anthropic_client = Anthropic(api_key=anthropic_api_key)
except Exception as e:
    st.error("Please configure your API key in Streamlit secrets")
    st.stop()

# Initialize session state for documents
if 'documents' not in st.session_state:
    st.session_state.documents = {}

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

# File uploader for multiple files
uploaded_files = st.file_uploader(
    "Upload documents (PDF, DOCX, or TXT)", 
    type=['pdf', 'docx', 'txt'],
    accept_multiple_files=True
)

# Process uploaded files
for uploaded_file in uploaded_files:
    if uploaded_file.name not in st.session_state.documents:
        try:
            if uploaded_file.type == "application/pdf":
                text = read_pdf(uploaded_file)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = read_docx(uploaded_file)
            else:  # txt files
                text = read_txt(uploaded_file)
            
            st.session_state.documents[uploaded_file.name] = text
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {str(e)}")

# Display uploaded documents
if st.session_state.documents:
    st.success(f"Successfully uploaded {len(st.session_state.documents)} documents")
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Uploaded Documents:")
        for doc_name in st.session_state.documents.keys():
            st.write(f"📄 {doc_name}")
    
        # Option to clear all documents
        if st.button("Clear All Documents"):
            st.session_state.documents = {}
            st.rerun()
    
    with col2:
        # Document selection for preview
        selected_doc = st.selectbox(
            "Select a document to preview:",
            options=list(st.session_state.documents.keys())
        )
        if selected_doc:
            with st.expander("Document Preview"):
                st.text(st.session_state.documents[selected_doc][:1000] + "...")

    # User question about the documents
    st.write("### Ask Questions About Your Documents")
    user_question = st.text_input(
        "What would you like to know about these documents?",
        placeholder="e.g., 'Compare these documents' or 'What are the main points from all documents?'"
    )
    
    if user_question:
        with st.spinner("Processing with Claude 3.5 Sonnet..."):
            try:
                # Prepare document content
                all_docs_content = "\n\n---DOCUMENT SEPARATOR---\n\n".join(
                    f"Document: {name}\nContent:\n{content}" 
                    for name, content in st.session_state.documents.items()
                )
                
                # Create message with all documents and question
                response = st.session_state.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",  # Using Claude 3.5 Sonnet
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"I have multiple documents to analyze. Here they are:\n\n"
                                f"{all_docs_content}\n\n"
                                f"Question: {user_question}"
                            )
                        }
                    ]
                )
                
                # Display response in a nice format
                st.write("### Claude's Response:")
                st.markdown(response.content[0].text)
                
            except Exception as e:
                st.error(f"Error processing request: {str(e)}")

else:
    st.info("Please upload some documents to begin.")

# Add a footer with usage information
st.markdown("---")
st.markdown("""
    **Usage Notes:**
    - You can upload multiple documents of different types (PDF, DOCX, TXT)
    - Each document is processed independently
    - Questions can be asked about individual documents or relationships between documents
    - Using Claude 3.5 Sonnet for optimal performance and cost-effectiveness
""")
