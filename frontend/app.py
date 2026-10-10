import streamlit as st
import requests
import json
import time

API_URL = "http://localhost:8001"

st.set_page_config(
    page_title="Multi-Agent Stock Research",
    page_icon="📊",
    layout="wide",
)

# --- Sidebar ---
st.sidebar.title("⚙️ Settings")
ticker = st.sidebar.selectbox(
    "Ticker",
    ["AAPL", "MSFT", "GOOGL", "AMZN", "MCD", "NVDA", "TSLA", "JPM", "KO", "XOM"],
    index=4,  # MCD default
)
experience = st.sidebar.selectbox("Experience Level", ["beginner", "intermediate", "advanced"], index=1)
risk = st.sidebar.selectbox("Risk Tolerance", ["low", "medium", "high"], index=1)
budget = st.sidebar.selectbox("Budget", ["small", "medium", "large"], index=1)

# Beginner mode toggle
beginner_mode = st.sidebar.toggle("🎓 Beginner Mode", value=(experience == "beginner"))
if beginner_mode:
    experience = "beginner"

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Quick Actions")
if st.sidebar.button("View Dossier"):
    try:
        resp = requests.get(f"{API_URL}/dossier/{ticker}", timeout=10)
        if resp.ok:
            st.sidebar.json(resp.json()["dossier"])
        else:
            st.sidebar.error(f"Failed: {resp.text}")
    except Exception as e:
        st.sidebar.error(f"API Error: {e}")

# Health check
try:
    health = requests.get(f"{API_URL}/health", timeout=3).json()
    pg_status = "🟢" if health.get("postgres") else "🔴"
    rd_status = "🟢" if health.get("redis") else "🔴"
    st.sidebar.markdown(f"**Status**: {pg_status} Postgres {rd_status} Redis")
except:
    st.sidebar.markdown("**Status**: 🔴 API Offline")

# --- Main ---
st.title("🤖 Multi-Agent Stock Research")
st.markdown("*AI-powered Bull/Bear debate system with compliance verification*")

# Demo scenarios
st.markdown("### 💡 Try these queries:")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Should I buy MCD?"):
        st.session_state["demo_query"] = "Should I buy McDonald's stock?"
        st.session_state["demo_ticker"] = "MCD"
with col2:
    if st.button("NVDA risk analysis"):
        st.session_state["demo_query"] = "What are the main risks of investing in NVIDIA right now?"
        st.session_state["demo_ticker"] = "NVDA"
with col3:
    if st.button("AAPL vs MSFT"):
        st.session_state["demo_query"] = "Compare Apple and Microsoft as investments"
        st.session_state["demo_ticker"] = "AAPL"

# Chat input
default_query = st.session_state.get("demo_query", "")
query = st.text_input("Ask a question about any stock:", value=default_query, key="chat_input")

if st.button("🔍 Analyze", type="primary") and query:
    with st.spinner("🤖 Agents debating... (Bull 🐂 vs Bear 🐻)"):
        start = time.time()
        try:
            selected_ticker = st.session_state.get("demo_ticker", ticker)
            resp = requests.post(
                f"{API_URL}/chat",
                json={
                    "query": query,
                    "ticker": selected_ticker,
                    "experience": experience,
                    "risk_tolerance": risk,
                    "budget": budget,
                },
                timeout=60,
            )
            elapsed = time.time() - start
            
            if resp.ok:
                data = resp.json()
                
                st.success(f"✅ Analysis complete in {elapsed:.1f}s ({data.get('latency_ms', 0):.0f}ms backend)")
                
                # --- Main Response ---
                st.markdown("## 📋 Analysis")
                st.markdown(data.get("formatted_response", "No response"))
                
                # --- Tabs for detailed view ---
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "🐂 Bull Case", "🐻 Bear Case", "⚖️ Judge Verdict", 
                    "👨‍🔬 Experts", "😈 Devil's Advocate"
                ])
                
                with tab1:
                    bull = data.get("bull_case", {})
                    if bull:
                        if "thesis" in bull:
                            st.markdown(f"### Thesis")
                            st.markdown(bull["thesis"])
                        if "key_points" in bull:
                            st.markdown("### Key Points")
                            for point in bull["key_points"]:
                                st.markdown(f"- {point}")
                        if "upside_target" in bull and bull["upside_target"]:
                            st.metric("Upside Target", f"${bull['upside_target']}")
                        if "confidence" in bull:
                            conf = min(max(bull["confidence"], 0.0), 1.0)
                            st.progress(conf, text=f"Confidence: {bull['confidence']:.0%}")
                    else:
                        st.info("Bull case not available")
                
                with tab2:
                    bear = data.get("bear_case", {})
                    if bear:
                        if "thesis" in bear:
                            st.markdown(f"### Thesis")
                            st.markdown(bear["thesis"])
                        if "key_points" in bear:
                            st.markdown("### Key Points")
                            for point in bear["key_points"]:
                                st.markdown(f"- {point}")
                        if "downside_target" in bear and bear["downside_target"]:
                            st.metric("Downside Target", f"${bear['downside_target']}")
                        if "confidence" in bear:
                            conf = min(max(bear["confidence"], 0.0), 1.0)
                            st.progress(conf, text=f"Confidence: {bear['confidence']:.0%}")
                    else:
                        st.info("Bear case not available")
                
                with tab3:
                    judge = data.get("judge_verdict", {})
                    if judge:
                        verdict = judge.get("verdict", "N/A")
                        color = {"bullish": "green", "bearish": "red", "neutral": "orange"}.get(verdict, "gray")
                        st.markdown(f"### Verdict: :{color}[{verdict.upper()}]")
                        if "conviction" in judge:
                            conv = min(max(judge["conviction"], 0.0), 1.0)
                            st.progress(conv, text=f"Conviction: {judge['conviction']:.0%}")
                        if "rationale" in judge:
                            st.markdown(f"**Rationale:** {judge['rationale']}")
                        if "scenarios" in judge:
                            st.markdown("### Scenarios")
                            for sc in judge["scenarios"]:
                                st.markdown(f"- **{sc.get('name', 'N/A')}** ({sc.get('probability', 0):.0%}): {sc.get('description', '')}")
                    else:
                        st.info("Judge verdict not available")
                
                with tab4:
                    experts = data.get("experts", {})
                    if experts:
                        for name, output in experts.items():
                            if output:
                                with st.expander(f"📊 {name.capitalize()}"):
                                    if isinstance(output, str):
                                        try:
                                            st.json(json.loads(output))
                                        except Exception:
                                            st.write(output)
                                    else:
                                        st.json(output)
                    else:
                        st.info("Expert analysis not available")
                
                with tab5:
                    devil = data.get("devils_advocate", {})
                    if devil:
                        sound = devil.get("verdict_sound", None)
                        if sound is not None:
                            st.markdown(f"### Verdict Sound: {'✅ Yes' if sound else '❌ No'}")
                        if "weaknesses" in devil:
                            st.markdown("### Weaknesses Found")
                            for w in devil["weaknesses"]:
                                st.markdown(f"- {w}")
                        if "alternative_interpretation" in devil:
                            st.markdown(f"**Alternative:** {devil['alternative_interpretation']}")
                    else:
                        st.info("Devil's advocate not available")
                
                # Errors
                if data.get("errors"):
                    st.warning(f"⚠️ Some errors occurred: {data['errors']}")
                    
            else:
                st.error(f"API Error: {resp.status_code} - {resp.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API. Make sure FastAPI is running on port 8000.")
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. The analysis may take up to 30 seconds.")
        except Exception as e:
            st.error(f"Error: {e}")

    # Clear demo state
    if "demo_query" in st.session_state:
        del st.session_state["demo_query"]
    if "demo_ticker" in st.session_state:
        del st.session_state["demo_ticker"]

# --- Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "Multi-Agent Stock Research Demo | Bull/Bear/Judge Architecture | "
    "Powered by Llama 3 via Groq"
    "</div>",
    unsafe_allow_html=True,
)
