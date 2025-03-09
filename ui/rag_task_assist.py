# ui/rag_task_assistant.py
import streamlit as st
from ui.rag_utils import reset_question_input

def task_assistant(chain):
    """
    Task Assistant UI - Displays the chat interface and handles user interactions.

    Args:
        chain (ConversationalRetrievalChain): The RAG conversational retrieval chain.
    """
    # Task Assistant Section (Now at Bottom)
    st.header("Task Assistant")
    st.write("Ask me anything about your tasks!")

    # Display chat history
    chat_container = st.container(height=300, border=True)
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(
                    f'<div style="text-align: right;"><b>You:</b> {message["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**Assistant:** {message['content']}")

    # Chat input with dynamic key to force reset
    user_input = st.text_input(
        "Your question:",
        placeholder="e.g., What tasks are related to Project A?",
        key=f"question_input_{st.session_state.question_key}"
    )

    if st.button("Send", key="send_button"):
        if user_input:
            if chain is None:
                st.error("System not initialized. Please provide your API key.")
            else:
                # Add user message to chat history
                st.session_state.chat_history.append({"role": "user", "content": user_input})

                # Get response from the chain
                with st.spinner("Thinking..."):
                    try:
                        response = chain.invoke({"question": user_input})
                        answer = response["answer"]

                        # Add assistant response to chat history
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})

                        # Reset the question input field
                        reset_question_input()

                        # Rerun to update the UI
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")

    # Example questions in a collapsible section
    with st.expander("Example questions you can ask", expanded=False):
        st.markdown("""
        - What tasks are related to Project A?
        - What should I work on next?
        - Do I have any reading tasks?
        - What are my highest priority tasks?
        - Show me all tasks related to development
        - What personal development tasks do I have?
        """)

