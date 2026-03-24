#!/usr/bin/env python3
"""
Streamlit Web UI for RedCortex
Provides an interactive interface for querying the knowledge base
"""
import os
import sys
import time

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from rag_pipeline import (
    hybrid_search,
    format_context,
    query_llm,
    get_cached_response,
    get_cache_key,
    MODEL_DEFAULT
)

# Page configuration
st.set_page_config(
    page_title="RedCortex - RHEL Knowledge Base",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
    }
    .source-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .answer-box {
        background-color: #e8f4f8;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "total_queries" not in st.session_state:
        st.session_state.total_queries = 0
    if "cache_hits" not in st.session_state:
        st.session_state.cache_hits = 0


def display_chat_history():
    """Display previous Q&A pairs"""
    if st.session_state.chat_history:
        st.sidebar.markdown("---")
        st.sidebar.subheader("💬 Recent Queries")
        for i, item in enumerate(reversed(st.session_state.chat_history[-5:])):
            with st.sidebar.expander(f"Q: {item['question'][:50]}..."):
                st.write(f"**Answer:** {item['answer'][:200]}...")
                st.write(f"*Method: {item['method']}*")


def main():
    init_session_state()
    
    # Header
    st.markdown('<p class="main-header">📚 RedCortex</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Red Hat Enterprise Linux Knowledge Base</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Search method
        search_method = st.radio(
            "Search Method",
            ["Hybrid (BM25 + Vector)", "Vector Only"],
            index=0
        )
        enable_hybrid = search_method == "Hybrid (BM25 + Vector)"
        
        # Number of results
        top_k = st.slider("Number of sources", min_value=3, max_value=10, value=5)
        
        # Model info
        st.markdown("---")
        st.header("🤖 Model")
        st.info(f"**Current:** {MODEL_DEFAULT}")
        
        # Stats
        st.markdown("---")
        st.header("📊 Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Queries", st.session_state.total_queries)
        with col2:
            cache_rate = (st.session_state.cache_hits / max(st.session_state.total_queries, 1)) * 100
            st.metric("Cache Hit %", f"{cache_rate:.1f}%")
        
        display_chat_history()
    
    # Main content
    st.markdown("---")
    
    # Query input
    query = st.text_input(
        "Ask a question about Red Hat Enterprise Linux:",
        placeholder="e.g., How do I configure firewalld rich rules?",
        key="query_input"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    with col2:
        if st.button("🔄 Clear History", use_container_width=False):
            st.session_state.chat_history = []
            st.rerun()
    
    if search_button and query:
        # Check cache
        cache_key = get_cache_key(query, MODEL_DEFAULT, top_k)
        cached = get_cached_response(cache_key)
        
        if cached:
            st.session_state.cache_hits += 1
            is_cached = True
        else:
            is_cached = False
        
        st.session_state.total_queries += 1
        
        # Progress
        with st.spinner("Searching knowledge base..." if not is_cached else "Retrieving from cache..."):
            start_time = time.time()
            
            try:
                # Search
                results, method = hybrid_search(query, top_k=top_k, enable_hybrid=enable_hybrid)
                search_time = time.time() - start_time
                
                if not results:
                    st.error("❌ No relevant documents found in the knowledge base.")
                    return
                
                # Get context and generate answer
                context, sources = format_context(results)
                
                if not is_cached:
                    answer, cost_info, used_model = query_llm(query, context, MODEL_DEFAULT)
                else:
                    answer = cached["answer"]
                    cost_info = cached["cost_info"] + " (cached)"
                    used_model = cached["model"]
                
                total_time = time.time() - start_time
                
                # Store in history
                st.session_state.chat_history.append({
                    "question": query,
                    "answer": answer,
                    "method": method,
                    "sources": sources
                })
                
                # Display results
                st.markdown("---")
                
                # Metrics row
                metric_cols = st.columns(4)
                with metric_cols[0]:
                    st.markdown(f'<div class="metric-card"><strong>⏱️ Time</strong><br>{total_time:.2f}s</div>', 
                              unsafe_allow_html=True)
                with metric_cols[1]:
                    st.markdown(f'<div class="metric-card"><strong>📄 Sources</strong><br>{len(results)}</div>', 
                              unsafe_allow_html=True)
                with metric_cols[2]:
                    st.markdown(f'<div class="metric-card"><strong>🔍 Method</strong><br>{method}</div>', 
                              unsafe_allow_html=True)
                with metric_cols[3]:
                    cache_status = "✅ Hit" if is_cached else "❌ Miss"
                    st.markdown(f'<div class="metric-card"><strong>💾 Cache</strong><br>{cache_status}</div>', 
                              unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Two columns for answer and sources
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("💡 Answer")
                    st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.caption(f"Model: {used_model} | {cost_info}")
                
                with col2:
                    st.subheader("📚 Sources")
                    for i, src in enumerate(sources, 1):
                        with st.expander(f"Source {i}"):
                            st.caption(src)
                    
                    # Source summary
                    st.markdown("---")
                    st.caption(f"**Search Details:**")
                    st.caption(f"- Vector search: {sum(1 for r in results if r.source in ['vector', 'hybrid'])} results")
                    st.caption(f"- Pages covered: {min(r.page_start for r in results)}-{max(r.page_end for r in results)}")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Tip: Make sure the database is initialized and documents are indexed.")
    
    # Footer
    st.markdown("---")
    st.caption("RedCortex - Enhanced RAG Pipeline with Semantic Chunking, Hybrid Search, and Cross-Encoder Reranking")


if __name__ == "__main__":
    main()
