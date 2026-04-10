import streamlit as st
from snowflake.snowpark.context import get_active_session
import _snowflake
import pandas as pd
import plotly.express as px
import json

session = get_active_session()

DATABASE = "HACKATHON_DB"
SCHEMA = "CORTEX_BI"
STAGE = "SEMANTIC_MODELS"
FILE = "semantic_model.yaml"
SEMANTIC_MODEL_FILE = f"@{DATABASE}.{SCHEMA}.{STAGE}/{FILE}"

st.set_page_config(page_title="SD Cortex BI Chat", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f0f4ff; }
    </style>
""", unsafe_allow_html=True)
st.title("Conversational BI with Cortex Analyst")
st.caption("Built by Sonali Dash | Ask business questions in plain English")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "query_log" not in st.session_state:
    st.session_state.query_log = []

def send_message(prompt):
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
        "semantic_model_file": SEMANTIC_MODEL_FILE,
    }
    resp = _snowflake.send_snow_api_request(
        "POST",
        f"/api/v2/cortex/analyst/message",
        {},
        {},
        request_body,
        {},
        30000,
    )
    if resp["status"] < 400:
        return json.loads(resp["content"])
    else:
        raise Exception(f"API error {resp['status']}: {resp['content']}")

def generate_summary(question, result_df):
    if result_df is None or result_df.empty:
        return "No data available to summarize."
    sample = result_df.head(8).to_string(index=False)
    prompt = f"Based on this question and data, give a 3-sentence executive summary.\nQuestion: {question}\nData:\n{sample}"
    try:
        resp = session.sql(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${prompt}$$) AS S").collect()
        return resp[0]["S"]
    except Exception as e:
        return f"Summary unavailable: {str(e)}"

def process_response(response):
    message = response.get("message", {})
    content = message.get("content", [])
    sql_text = None
    text_response = None
    suggestions = []
    for item in content:
        if item.get("type") == "sql":
            sql_text = item.get("statement", "")
        elif item.get("type") == "text":
            text_response = item.get("text", "")
        elif item.get("type") == "suggestions":
            suggestions = item.get("suggestions", [])
    return sql_text, text_response, suggestions

suggested_questions = [
    "What are the top economic indicators by latest value?",
    "Show GDP trend over the last 10 years",
    "What is the latest CPI reading?",
    "Compare employment hires across industries",
    "Which BLS report has the most data points?",
    "Show monthly unemployment trends for 2023",
    "What industries have the highest job openings?",
    "Average value by frequency for economic indicators",
]

with st.sidebar:
    st.subheader("Suggested questions")
    for q in suggested_questions:
        if st.button(q, key=q, use_container_width=True):
            st.session_state.selected_question = q
    st.divider()
    st.subheader("Query log")
    if st.session_state.query_log:
        log_df = pd.DataFrame(st.session_state.query_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True)
    else:
        st.info("No queries yet")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sql"):
            with st.expander("View generated SQL"):
                st.code(msg["sql"], language="sql")

question = st.chat_input("Ask a business question about financial and economic data...")

if hasattr(st.session_state, "selected_question"):
    question = st.session_state.selected_question
    del st.session_state.selected_question

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your question..."):
            try:
                response = send_message(question)
                sql_text, text_response, suggestions = process_response(response)

                if sql_text:
                    with st.expander("View generated SQL", expanded=False):
                        st.code(sql_text, language="sql")

                    try:
                        result_df = session.sql(sql_text).to_pandas()
                        if not result_df.empty:
                            st.dataframe(result_df.head(50), use_container_width=True, hide_index=True)

                            numeric_cols = result_df.select_dtypes(include=["number"]).columns.tolist()
                            non_numeric = [c for c in result_df.columns if c not in numeric_cols]

                            if numeric_cols and non_numeric:
                                date_cols = [c for c in result_df.columns if "date" in c.lower()]
                                if date_cols:
                                    fig = px.line(result_df, x=date_cols[0], y=numeric_cols[0], title=f"{numeric_cols[0]} over time")
                                    st.plotly_chart(fig, use_container_width=True)
                                elif result_df[non_numeric[0]].nunique() <= 30:
                                    fig = px.bar(result_df.head(20), x=non_numeric[0], y=numeric_cols[0], title=f"{numeric_cols[0]} by {non_numeric[0]}", color=numeric_cols[0], color_continuous_scale="Blues")
                                    st.plotly_chart(fig, use_container_width=True)

                            summary = generate_summary(question, result_df)
                            st.info(summary)

                            log_entry = {"question": question, "sql_ok": "Yes", "rows": len(result_df)}
                        else:
                            st.warning("Query returned no results.")
                            log_entry = {"question": question, "sql_ok": "Yes", "rows": 0}
                    except Exception as e:
                        st.error(f"SQL execution error: {str(e)}")
                        log_entry = {"question": question, "sql_ok": "Error", "rows": str(e)[:50]}

                    st.session_state.messages.append({"role": "assistant", "content": text_response or "Results above", "sql": sql_text})

                elif text_response:
                    st.write(text_response)
                    st.session_state.messages.append({"role": "assistant", "content": text_response})
                    log_entry = {"question": question, "sql_ok": "N/A", "rows": "text only"}

                elif suggestions:
                    st.write("Your question was ambiguous. Did you mean:")
                    for s in suggestions:
                        st.write(f"- {s}")
                    st.session_state.messages.append({"role": "assistant", "content": "Suggestions: " + ", ".join(suggestions)})
                    log_entry = {"question": question, "sql_ok": "Ambiguous", "rows": "suggestions"}

                else:
                    st.json(response)
                    st.session_state.messages.append({"role": "assistant", "content": "Unparseable response"})
                    log_entry = {"question": question, "sql_ok": "No", "rows": "parse error"}

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
                log_entry = {"question": question, "sql_ok": "Error", "rows": str(e)[:50]}

            st.session_state.query_log.append(log_entry)

st.divider()
st.markdown("**Platform:** Cortex Analyst + Cortex COMPLETE + Streamlit in Snowflake | Semantic Model: semantic_model.yaml")