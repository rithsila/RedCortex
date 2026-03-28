#!/usr/bin/env python3
"""
RedCortex - Modern Streamlit Web UI
Professional RAG interface with dark/light themes, chat interface, and rich analytics
"""
import os
import sys
import time
import json

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from rag_pipeline import (
    hybrid_search,
    format_context,
    query_llm,
    get_cached_response,
    get_cache_key,
    MODEL_DEFAULT,
    query_logger
)

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="RedCortex | RHEL Knowledge Base",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/redcortex/help',
        'Report a bug': 'https://github.com/redcortex/issues',
        'About': 'RedCortex v2.2 - AI-Powered RHEL Knowledge Base'
    }
)

# =============================================================================
# THEME & CUSTOM CSS
# =============================================================================
def get_custom_css():
    """Generate custom CSS based on theme"""
    is_dark = st.session_state.get('theme', 'dark') == 'dark'
    
    # Color palettes
    if is_dark:
        colors = {
            'bg_primary': '#0d1117',
            'bg_secondary': '#161b22',
            'bg_tertiary': '#21262d',
            'text_primary': '#e6edf3',
            'text_secondary': '#8b949e',
            'accent': '#58a6ff',
            'accent_hover': '#79c0ff',
            'success': '#3fb950',
            'warning': '#d29922',
            'error': '#f85149',
            'border': '#30363d',
            'card_shadow': '0 8px 24px rgba(0,0,0,0.4)',
            'gradient_start': '#161b22',
            'gradient_end': '#0d1117',
        }
    else:
        colors = {
            'bg_primary': '#ffffff',
            'bg_secondary': '#f6f8fa',
            'bg_tertiary': '#eaeef2',
            'text_primary': '#1f2328',
            'text_secondary': '#656d76',
            'accent': '#0969da',
            'accent_hover': '#0550ae',
            'success': '#1a7f37',
            'warning': '#9a6700',
            'error': '#cf222e',
            'border': '#d0d7de',
            'card_shadow': '0 8px 24px rgba(140,149,159,0.2)',
            'gradient_start': '#f6f8fa',
            'gradient_end': '#ffffff',
        }
    
    return f"""
    <style>
    /* Global styles */
    .stApp {{
        background: linear-gradient(180deg, {colors['gradient_start']} 0%, {colors['gradient_end']} 100%);
    }}
    
    /* Header styling */
    .main-header {{
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, {colors['accent']} 0%, #a371f7 50%, #f778ba 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }}
    
    .sub-header {{
        font-size: 1.1rem;
        color: {colors['text_secondary']};
        font-weight: 400;
        margin-bottom: 2rem;
    }}
    
    /* Chat message bubbles */
    .chat-message {{
        padding: 1.25rem;
        border-radius: 1rem;
        margin: 0.75rem 0;
        animation: fadeIn 0.3s ease-out;
        box-shadow: {colors['card_shadow']};
    }}
    
    .chat-user {{
        background: linear-gradient(135deg, {colors['accent']}20 0%, {colors['accent']}10 100%);
        border-left: 4px solid {colors['accent']};
        margin-left: 2rem;
    }}
    
    .chat-assistant {{
        background: {colors['bg_secondary']};
        border: 1px solid {colors['border']};
        margin-right: 2rem;
    }}
    
    .chat-icon {{
        font-size: 1.5rem;
        margin-right: 0.75rem;
    }}
    
    /* Source cards */
    .source-card {{
        background: {colors['bg_secondary']};
        border: 1px solid {colors['border']};
        border-radius: 0.75rem;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.2s ease;
        cursor: pointer;
    }}
    
    .source-card:hover {{
        border-color: {colors['accent']};
        transform: translateY(-2px);
        box-shadow: {colors['card_shadow']};
    }}
    
    .source-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }}
    
    .source-badge {{
        background: {colors['accent']}20;
        color: {colors['accent']};
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }}
    
    .source-score {{
        color: {colors['text_secondary']};
        font-size: 0.875rem;
    }}
    
    .source-content {{
        color: {colors['text_secondary']};
        font-size: 0.9rem;
        line-height: 1.5;
    }}
    
    /* Metrics styling */
    .metric-container {{
        background: {colors['bg_secondary']};
        border-radius: 0.75rem;
        padding: 1rem;
        text-align: center;
        border: 1px solid {colors['border']};
    }}
    
    .metric-value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {colors['text_primary']};
    }}
    
    .metric-label {{
        font-size: 0.8rem;
        color: {colors['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    /* Status indicators */
    .status-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 0.5rem;
    }}
    
    .status-online {{ background: {colors['success']}; box-shadow: 0 0 8px {colors['success']}; }}
    .status-warning {{ background: {colors['warning']}; box-shadow: 0 0 8px {colors['warning']}; }}
    .status-offline {{ background: {colors['error']}; box-shadow: 0 0 8px {colors['error']}; }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: {colors['bg_secondary']};
        border-right: 1px solid {colors['border']};
    }}
    
    [data-testid="stSidebar"] .stButton>button {{
        width: 100%;
        border-radius: 0.5rem;
        transition: all 0.2s ease;
    }}
    
    /* Input styling */
    .stTextInput > div > div > input {{
        border-radius: 0.75rem;
        border: 1px solid {colors['border']};
        padding: 0.875rem 1rem;
        font-size: 1rem;
        background: {colors['bg_primary']};
        color: {colors['text_primary']};
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: {colors['accent']};
        box-shadow: 0 0 0 3px {colors['accent']}20;
    }}
    
    /* Button styling */
    .stButton > button {{
        border-radius: 0.75rem;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s ease;
    }}
    
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {colors['accent']} 0%, #8250df 100%);
        border: none;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px {colors['accent']}40;
    }}
    
    /* Expander styling */
    .streamlit-expanderHeader {{
        background: {colors['bg_tertiary']};
        border-radius: 0.5rem;
        padding: 0.75rem 1rem;
    }}
    
    /* Animations */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}
    
    @keyframes shimmer {{
        0% {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}
    
    .typing-indicator {{
        display: flex;
        gap: 0.25rem;
        padding: 1rem;
    }}
    
    .typing-dot {{
        width: 8px;
        height: 8px;
        background: {colors['accent']};
        border-radius: 50%;
        animation: pulse 1.4s ease-in-out infinite;
    }}
    
    .typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
    .typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
    
    /* Quick action chips */
    .quick-chip {{
        display: inline-block;
        background: {colors['bg_tertiary']};
        border: 1px solid {colors['border']};
        border-radius: 1rem;
        padding: 0.5rem 1rem;
        margin: 0.25rem;
        font-size: 0.875rem;
        color: {colors['text_secondary']};
        cursor: pointer;
        transition: all 0.2s ease;
    }}
    
    .quick-chip:hover {{
        background: {colors['accent']}20;
        border-color: {colors['accent']};
        color: {colors['accent']};
    }}
    
    /* Answer styling */
    .answer-content {{
        font-size: 1rem;
        line-height: 1.7;
        color: {colors['text_primary']};
    }}
    
    .answer-content code {{
        background: {colors['bg_tertiary']};
        padding: 0.2rem 0.4rem;
        border-radius: 0.25rem;
        font-family: 'SF Mono', Monaco, monospace;
        font-size: 0.9em;
    }}
    
    .answer-content pre {{
        background: {colors['bg_tertiary']};
        padding: 1rem;
        border-radius: 0.5rem;
        overflow-x: auto;
    }}
    
    /* Footer */
    .footer {{
        text-align: center;
        padding: 2rem;
        color: {colors['text_secondary']};
        font-size: 0.875rem;
        border-top: 1px solid {colors['border']};
        margin-top: 2rem;
    }}
    
    /* Hide default streamlit elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .stDeployButton {{display:none;}}
    </style>
    """

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'chat_history': [],
        'total_queries': 0,
        'cache_hits': 0,
        'theme': 'dark',
        'show_welcome': True,
        'last_query': None,
        'search_method': 'Hybrid (BM25 + Vector)',
        'top_k': 5,
        'is_processing': False,
        'system_status': None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# =============================================================================
# SYSTEM STATUS
# =============================================================================
def check_system_status():
    """Check system component status"""
    status = {
        'database': {'status': 'unknown', 'message': 'Checking...'},
        'qdrant': {'status': 'unknown', 'message': 'Checking...'},
        'ollama': {'status': 'unknown', 'message': 'Checking...'},
    }
    
    # Check database
    try:
        import sqlite3
        conn = sqlite3.connect("data/library.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE is_hot=1")
        chunk_count = cursor.fetchone()[0]
        conn.close()
        status['database'] = {
            'status': 'online',
            'message': f'{book_count} books, {chunk_count} chunks'
        }
    except Exception as e:
        status['database'] = {'status': 'offline', 'message': str(e)}
    
    # Check Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        collections = client.get_collections()
        status['qdrant'] = {
            'status': 'online',
            'message': f'{len(collections.collections)} collections'
        }
    except Exception as e:
        status['qdrant'] = {'status': 'offline', 'message': str(e)}
    
    # Check Ollama
    try:
        import httpx
        response = httpx.get(
            f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/tags",
            timeout=5.0
        )
        if response.status_code == 200:
            models = response.json().get('models', [])
            status['ollama'] = {
                'status': 'online',
                'message': f'{len(models)} models'
            }
        else:
            status['ollama'] = {'status': 'warning', 'message': f'HTTP {response.status_code}'}
    except Exception as e:
        status['ollama'] = {'status': 'offline', 'message': str(e)}
    
    return status

def render_status_indicator(status):
    """Render status dot with appropriate color"""
    if status == 'online':
        return '<span class="status-dot status-online"></span>'
    elif status == 'warning':
        return '<span class="status-dot status-warning"></span>'
    else:
        return '<span class="status-dot status-offline"></span>'

# =============================================================================
# SIDEBAR COMPONENTS
# =============================================================================
def render_sidebar():
    """Render the sidebar with settings and analytics"""
    with st.sidebar:
        # Logo/Brand
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h2 style="margin: 0; font-size: 1.5rem;">🧠 RedCortex</h2>
            <p style="color: #8b949e; font-size: 0.875rem; margin: 0;">v2.2</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Theme toggle
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🌙 Dark" if st.session_state.theme == 'light' else "☀️ Light", 
                        use_container_width=True):
                st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
                st.rerun()
        
        st.markdown("---")
        
        # Settings
        st.header("⚙️ Search Settings")
        
        # Search method
        search_method = st.radio(
            "Search Method",
            ["Hybrid (BM25 + Vector)", "Vector Only", "BM25 Only"],
            index=0 if st.session_state.search_method == "Hybrid (BM25 + Vector)" else 
                  (1 if st.session_state.search_method == "Vector Only" else 2),
            help="Hybrid combines keyword (BM25) and semantic (Vector) search for best results"
        )
        st.session_state.search_method = search_method
        enable_hybrid = search_method == "Hybrid (BM25 + Vector)"
        enable_vector = search_method in ["Hybrid (BM25 + Vector)", "Vector Only"]
        enable_bm25 = search_method in ["Hybrid (BM25 + Vector)", "BM25 Only"]
        
        # Number of results
        top_k = st.slider(
            "Results to retrieve",
            min_value=3,
            max_value=10,
            value=st.session_state.top_k,
            help="Number of document chunks to retrieve for context"
        )
        st.session_state.top_k = top_k
        
        # Model info
        st.markdown("---")
        st.header("🤖 Model")
        st.info(f"**{MODEL_DEFAULT}**\n\nOptimized for technical RHEL queries")
        
        # System Status
        st.markdown("---")
        st.header("🔌 System Status")
        
        status = check_system_status()
        for component, info in status.items():
            icon = "🟢" if info['status'] == 'online' else ("🟡" if info['status'] == 'warning' else "🔴")
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; 
                        padding: 0.5rem; background: {'#21262d' if st.session_state.theme == 'dark' else '#f6f8fa'}; 
                        border-radius: 0.5rem; margin: 0.25rem 0;">
                <span>{icon} <strong>{component.title()}</strong></span>
                <span style="font-size: 0.75rem; color: #8b949e;">{info['message']}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick stats
        st.markdown("---")
        st.header("📊 Session Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Queries", st.session_state.total_queries)
        with col2:
            cache_rate = (st.session_state.cache_hits / max(st.session_state.total_queries, 1)) * 100
            st.metric("Cache %", f"{cache_rate:.1f}%")
        
        # Recent queries
        if st.session_state.chat_history:
            st.markdown("---")
            st.header("💬 Recent")
            
            for i, item in enumerate(reversed(st.session_state.chat_history[-5:])):
                with st.expander(f"{item['question'][:40]}...", expanded=False):
                    st.caption(f"**Method:** {item.get('method', 'hybrid')}")
                    time_val = item.get('time', 'N/A')
                    time_str = f"{time_val:.2f}s" if isinstance(time_val, (int, float)) else str(time_val)
                    st.caption(f"**Time:** {time_str}")
                    if st.button(f"🔄 Rerun", key=f"rerun_{i}"):
                        st.session_state.last_query = item['question']
                        st.rerun()

# =============================================================================
# MAIN UI COMPONENTS
# =============================================================================
def render_header():
    """Render the main header"""
    st.markdown('<p class="main-header">🧠 RedCortex</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">AI-Powered Red Hat Enterprise Linux Knowledge Base</p>',
        unsafe_allow_html=True
    )

def render_quick_actions():
    """Render quick action suggestion chips"""
    quick_queries = [
        "How to configure firewalld?",
        "Create a new user account",
        "Manage systemd services",
        "Configure SELinux policies",
        "Set up SSH key authentication",
        "Manage LVM volumes",
        "Configure NetworkManager",
        "Troubleshoot boot issues",
    ]
    
    st.markdown("<p style='color: #8b949e; margin-bottom: 0.5rem;'>💡 Quick suggestions:</p>", 
                unsafe_allow_html=True)
    
    cols = st.columns(4)
    for i, query in enumerate(quick_queries[:4]):
        with cols[i]:
            if st.button(query, key=f"quick_{i}", use_container_width=True):
                st.session_state.last_query = query
                st.rerun()

def render_welcome():
    """Render welcome message when no queries yet"""
    if not st.session_state.chat_history and st.session_state.show_welcome:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem; opacity: 0.8;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">👋</div>
            <h3 style="margin-bottom: 1rem;">Welcome to RedCortex</h3>
            <p style="color: #8b949e; max-width: 500px; margin: 0 auto;">
                Your intelligent assistant for Red Hat Enterprise Linux documentation.
                Ask about system administration, security, networking, and more.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        render_quick_actions()

def render_chat_message(role, content, metadata=None):
    """Render a chat message bubble"""
    is_user = role == "user"
    icon = "👤" if is_user else "🧠"
    css_class = "chat-user" if is_user else "chat-assistant"
    
    st.markdown(f"""
    <div class="chat-message {css_class}">
        <div style="display: flex; align-items: flex-start;">
            <span class="chat-icon">{icon}</span>
            <div style="flex: 1;">
                <strong>{'You' if is_user else 'RedCortex'}</strong>
                <div class="answer-content">{content}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if metadata and not is_user:
        cols = st.columns(4)
        metrics = [
            ("⏱️ Time", f"{metadata.get('time', 0):.2f}s"),
            ("📄 Sources", metadata.get('sources', 0)),
            ("🔍 Method", metadata.get('method', 'hybrid')),
            ("💾 Cache", "Hit" if metadata.get('cached') else "Miss"),
        ]
        for col, (label, value) in zip(cols, metrics):
            with col:
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

def render_source_cards(sources):
    """Render source document cards"""
    st.subheader("📚 Sources")
    
    for i, src in enumerate(sources, 1):
        score_pct = int(src.get('score', 0) * 100)
        score_color = "#3fb950" if score_pct > 80 else ("#d29922" if score_pct > 50 else "#f85149")
        
        st.markdown(f"""
        <div class="source-card">
            <div class="source-header">
                <span class="source-badge">{src.get('source_type', 'unknown')}</span>
                <span class="source-score" style="color: {score_color};">Score: {score_pct}%</span>
            </div>
            <div class="source-content">
                <strong>Pages {src.get('page_start', '?')}-{src.get('page_end', '?')}</strong><br>
                {src.get('content', 'No preview available')[:150]}...
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_typing_indicator():
    """Render typing animation"""
    st.markdown("""
    <div class="chat-message chat-assistant">
        <div style="display: flex; align-items: center;">
            <span class="chat-icon">🧠</span>
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# QUERY PROCESSING
# =============================================================================
def process_query(query: str, enable_hybrid: bool, top_k: int):
    """Process a query and return results"""
    start_time = time.time()
    
    # Check cache
    cache_key = get_cache_key(query, MODEL_DEFAULT, top_k)
    cached = get_cached_response(cache_key)
    
    if cached:
        st.session_state.cache_hits += 1
        return {
            'answer': cached["answer"],
            'sources': [],
            'metadata': {
                'time': time.time() - start_time,
                'sources': 0,
                'method': 'cache',
                'cached': True,
                'cost': 0
            }
        }
    
    # Search
    search_start = time.time()
    results, method = hybrid_search(query, top_k=top_k, enable_hybrid=enable_hybrid)
    
    if not results:
        return {'error': 'No relevant documents found in the knowledge base.'}
    
    # Get answer from LLM
    context, source_texts = format_context(results)
    answer, cost_info, used_model = query_llm(query, context, MODEL_DEFAULT, method, len(results))
    
    total_time = time.time() - start_time
    
    # Format sources
    sources = [
        {
            'chunk_id': r.chunk_id,
            'page_start': r.page_start,
            'page_end': r.page_end,
            'score': r.score,
            'source_type': r.source,
            'content': r.content[:200] + "..."
        }
        for r in results
    ]
    
    return {
        'answer': answer,
        'sources': sources,
        'metadata': {
            'time': total_time,
            'sources': len(results),
            'method': method,
            'cached': False,
            'cost': cost_info,
            'model': used_model
        }
    }

# =============================================================================
# MAIN APPLICATION
# =============================================================================
def main():
    """Main application entry point"""
    init_session_state()
    
    # Apply custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # Render sidebar
    render_sidebar()
    
    # Render header
    render_header()
    
    # Render welcome or chat history
    if not st.session_state.chat_history:
        render_welcome()
    else:
        # Show chat history
        for item in st.session_state.chat_history:
            render_chat_message("user", item['question'])
            render_chat_message("assistant", item['answer'], item.get('metadata'))
            if item.get('sources'):
                with st.expander(f"📚 View {len(item['sources'])} Sources", expanded=False):
                    render_source_cards(item['sources'])
    
    # Query input area
    st.markdown("---")
    
    # Use last_query if set (from quick actions or rerun)
    default_value = st.session_state.get('last_query', '')
    
    col1, col2 = st.columns([6, 1])
    with col1:
        query = st.text_input(
            "Ask about RHEL:",
            value=default_value,
            placeholder="e.g., How do I configure firewalld rich rules?",
            key="query_input",
            label_visibility="collapsed"
        )
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Clear last_query after using it
    if st.session_state.get('last_query'):
        st.session_state.last_query = None
    
    # Process query
    if search_button and query:
        st.session_state.is_processing = True
        st.session_state.total_queries += 1
        
        # Show user message immediately
        render_chat_message("user", query)
        
        # Show typing indicator
        render_typing_indicator()
        
        # Determine search settings
        enable_hybrid = st.session_state.search_method == "Hybrid (BM25 + Vector)"
        
        with st.spinner(""):
            result = process_query(query, enable_hybrid, st.session_state.top_k)
        
        if 'error' in result:
            st.error(f"❌ {result['error']}")
            st.info("💡 Tip: Make sure the database is initialized and documents are indexed.")
        else:
            # Store in history
            st.session_state.chat_history.append({
                'question': query,
                'answer': result['answer'],
                'sources': result['sources'],
                'metadata': result['metadata']
            })
            
            # Rerun to show updated chat
            st.rerun()
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>🧠 RedCortex v2.2 | Built with Streamlit • Qdrant • Ollama • OpenRouter</p>
        <p style="font-size: 0.75rem; opacity: 0.7;">
            Hybrid Search • Cross-Encoder Reranking • Query Caching • Semantic Chunking
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
