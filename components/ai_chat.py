"""
AI Botanical Assistant Component
"""
import streamlit as st
import time

def render(db):
    st.title("🤖 GrowLeafy AI Assistant")
    st.caption("Ask questions about plant care, pest identification, or fertilizer application.")
    st.markdown("---")
    
    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I am your GrowLeafy botanical assistant. How can I help you with your nursery today?"}
        ]

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("E.g., How do I treat powdery mildew on roses?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # --- API INTEGRATION POINT ---
            # Replace the code below with your actual LLM API call (OpenAI, Gemini, etc.)
            # e.g., response = openai.ChatCompletion.create(...)
            
            with st.spinner("Thinking..."):
                time.sleep(1.5) # Simulating network delay
                
                # Fallback/Dummy logic for demonstration
                lowercase_prompt = prompt.lower()
                if "mildew" in lowercase_prompt or "fungus" in lowercase_prompt:
                    full_response = "For powdery mildew or fungal issues, I recommend checking your **Pesticide Database** for products containing Neem Oil or Sulfur. Ensure the plant has good air circulation and water at the base to keep leaves dry."
                elif "fertilizer" in lowercase_prompt or "grow" in lowercase_prompt:
                    full_response = "During the active growing season, a balanced NPK fertilizer (like 10-10-10) is usually best. You can search your **Fertilizer Database** for these ratios."
                else:
                    full_response = "That's a great question about nursery management. (Connect your LLM API here to generate real answers based on your database!)"
            
            # Stream the response for a "typing" effect
            simulated_stream = ""
            for chunk in full_response.split():
                simulated_stream += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(simulated_stream + "▌")
            
            message_placeholder.markdown(full_response)
            
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
    # Clear chat button
    if len(st.session_state.messages) > 1:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Chat history cleared. How else can I help you?"}
            ]
            st.rerun()
