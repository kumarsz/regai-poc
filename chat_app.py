import streamlit as st
import boto3
import json

# ── Config ──────────────────────────────────────────────
KB_ID = "HQNBPCYYAJ"        # paste from Bedrock console once KB is ready
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
REGION = "us-east-1"

# ── AWS clients ──────────────────────────────────────────
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=REGION)

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title="RegAI Assistant",
    page_icon="🏛",
    layout="wide"
)

st.title("🏛 RegAI — Regulatory Circular Assistant")
st.caption("Powered by AWS Bedrock Knowledge Base · POC 1 & 2")

# ── Session state for chat history ───────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Display chat history ──────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "citations" in msg:
            with st.expander("📎 Source citations"):
                for i, citation in enumerate(msg["citations"]):
                    st.markdown(f"**Source {i+1}:** {citation}")

# ── Query function ────────────────────────────────────────
def query_kb(question):
    response = bedrock_agent.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KB_ID,
                "modelArn": f"arn:aws:bedrock:{REGION}::foundation-model/{MODEL_ID}",
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5
                    }
                }
            }
        }
    )

    answer = response["output"]["text"]

    # Extract citations
    citations = []
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            source = ref.get("location", {}).get("s3Location", {}).get("uri", "")
            excerpt = ref.get("content", {}).get("text", "")[:200]
            if source:
                filename = source.split("/")[-1]
                citations.append(f"`{filename}` — ...{excerpt}...")

    return answer, citations

# ── Chat input ────────────────────────────────────────────
sample_questions = [
    "What are the key requirements in the MAS circular?",
    "What does Basel III say about capital requirements?",
    "What is the compliance deadline mentioned?",
    "Summarise the main obligations for financial institutions.",
]

st.sidebar.header("💡 Sample Reg Ops questions")
for q in sample_questions:
    if st.sidebar.button(q, use_container_width=True):
        st.session_state.pending_question = q

if st.sidebar.button("🗑 Clear chat", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

# ── Handle input ──────────────────────────────────────────
question = st.chat_input("Ask a question about the regulatory circulars...")

if not question and "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

if question:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Query KB and show response
    with st.chat_message("assistant"):
        with st.spinner("Searching circulars..."):
            try:
                answer, citations = query_kb(question)
                st.markdown(answer)
                if citations:
                    with st.expander("📎 Source citations"):
                        for i, citation in enumerate(citations):
                            st.markdown(f"**Source {i+1}:** {citation}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "citations": citations
                })
            except Exception as e:
                error_msg = f"Error querying knowledge base: {str(e)}"
                st.error(error_msg)