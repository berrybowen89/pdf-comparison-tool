import streamlit as st
from anthropic import Anthropic

# Streamlit page config
st.set_page_config(page_title="Claude Chat", page_icon="🤖")

# Initialize Streamlit page
st.title("Claude 3 Chat Interface")

# Secure API key handling
try:
    if 'anthropic_client' not in st.session_state:
        anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        st.session_state.anthropic_client = Anthropic(api_key=anthropic_api_key)
except Exception as e:
    st.error("Please configure your API key in Streamlit secrets")
    st.stop()

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to ask Claude?"):
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        # Get Claude's response
        with st.chat_message("assistant"):
            with st.spinner("Claude is thinking..."):
                response = st.session_state.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=1000,
                    messages=st.session_state.messages
                )
                st.write(response.content[0].text)
                
                # Add assistant response to history
                st.session_state.messages.append(
                    {"role": "assistant", "content": response.content[0].text}
                )
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Add a clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()
