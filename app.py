import streamlit as st
from anthropic import Anthropic

# Initialize Streamlit page
st.title("Claude 3 Chat Interface")

# Initialize Anthropic client (we'll handle the API key more securely)
if 'anthropic_client' not in st.session_state:
    api_key = st.text_input("Enter your Anthropic API key:", type="password")
    if api_key:
        st.session_state.anthropic_client = Anthropic(api_key=api_key)

# Create a message input
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Get user input
if prompt := st.chat_input("What would you like to ask Claude?"):
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get Claude's response
    if 'anthropic_client' in st.session_state:
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
