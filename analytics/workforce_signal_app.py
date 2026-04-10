import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import plotly.express as px

session = get_active_session()

st.set_page_config(page_title="The Invisible Workforce Signal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #fff8f0; }
    </style>
""", unsafe_allow_html=True)
st.title("The Invisible Workforce Signal")
st.caption("Built by Sonali Dash | Who on my team is at risk of leaving, and why?")

df = session.sql("""
    SELECT *,
        -- Promotion Urgency Index (innovation: ratio, not just raw months)
        ROUND(MONTHS_SINCE_PROMOTION / GREATEST(TENURE_YEARS, 0.5), 2) AS PROMOTION_URGENCY,
        -- Team Size Risk Multiplier (innovation: large teams = less attention)
        CASE WHEN TEAM_SIZE >= 15 THEN 1.2 WHEN TEAM_SIZE >= 10 THEN 1.1 ELSE 1.0 END AS TEAM_MULTIPLIER,
        -- Base risk components
        (CASE WHEN TENURE_YEARS < 2 THEN 30 WHEN TENURE_YEARS < 5 THEN 15 ELSE 5 END) AS TENURE_RISK,
        (CASE WHEN PERFORMANCE_RATING <= 2 THEN 35 WHEN PERFORMANCE_RATING = 3 THEN 15 ELSE 5 END) AS PERF_RISK,
        (CASE WHEN MONTHS_SINCE_PROMOTION > 36 THEN 35 WHEN MONTHS_SINCE_PROMOTION > 18 THEN 20 ELSE 5 END) AS PROMO_RISK,
        -- Final risk score with team multiplier
        ROUND(
            ((CASE WHEN TENURE_YEARS < 2 THEN 30 WHEN TENURE_YEARS < 5 THEN 15 ELSE 5 END) +
             (CASE WHEN PERFORMANCE_RATING <= 2 THEN 35 WHEN PERFORMANCE_RATING = 3 THEN 15 ELSE 5 END) +
             (CASE WHEN MONTHS_SINCE_PROMOTION > 36 THEN 35 WHEN MONTHS_SINCE_PROMOTION > 18 THEN 20 ELSE 5 END))
            * (CASE WHEN TEAM_SIZE >= 15 THEN 1.2 WHEN TEAM_SIZE >= 10 THEN 1.1 ELSE 1.0 END)
        , 1) AS RISK_SCORE,
        -- Risk tier
        CASE
            WHEN ROUND(
                ((CASE WHEN TENURE_YEARS < 2 THEN 30 WHEN TENURE_YEARS < 5 THEN 15 ELSE 5 END) +
                 (CASE WHEN PERFORMANCE_RATING <= 2 THEN 35 WHEN PERFORMANCE_RATING = 3 THEN 15 ELSE 5 END) +
                 (CASE WHEN MONTHS_SINCE_PROMOTION > 36 THEN 35 WHEN MONTHS_SINCE_PROMOTION > 18 THEN 20 ELSE 5 END))
                * (CASE WHEN TEAM_SIZE >= 15 THEN 1.2 WHEN TEAM_SIZE >= 10 THEN 1.1 ELSE 1.0 END)
            , 1) >= 70 THEN 'High'
            WHEN ROUND(
                ((CASE WHEN TENURE_YEARS < 2 THEN 30 WHEN TENURE_YEARS < 5 THEN 15 ELSE 5 END) +
                 (CASE WHEN PERFORMANCE_RATING <= 2 THEN 35 WHEN PERFORMANCE_RATING = 3 THEN 15 ELSE 5 END) +
                 (CASE WHEN MONTHS_SINCE_PROMOTION > 36 THEN 35 WHEN MONTHS_SINCE_PROMOTION > 18 THEN 20 ELSE 5 END))
                * (CASE WHEN TEAM_SIZE >= 15 THEN 1.2 WHEN TEAM_SIZE >= 10 THEN 1.1 ELSE 1.0 END)
            , 1) >= 40 THEN 'Medium'
            ELSE 'Low'
        END AS RISK_TIER,
        -- Flight risk pattern (innovation: combo detection)
        CASE
            WHEN PERFORMANCE_RATING <= 2 AND TENURE_YEARS >= 5 THEN 'Quiet Quitting'
            WHEN PERFORMANCE_RATING >= 4 AND MONTHS_SINCE_PROMOTION > 24 THEN 'Poach Risk'
            WHEN TENURE_YEARS < 1.5 AND TEAM_SIZE >= 12 THEN 'Lost in Crowd'
            WHEN MONTHS_SINCE_PROMOTION > 30 AND PERFORMANCE_RATING = 3 THEN 'Stagnating'
            ELSE 'Normal'
        END AS FLIGHT_PATTERN
    FROM HACKATHON_DB.ANALYTICS.HR_ATTRITION
""").to_pandas()

# KPI tiles
col1, col2, col3, col4, col5 = st.columns(5)
total = len(df)
high = len(df[df["RISK_TIER"] == "High"])
medium = len(df[df["RISK_TIER"] == "Medium"])
low = len(df[df["RISK_TIER"] == "Low"])
patterns = len(df[df["FLIGHT_PATTERN"] != "Normal"])
col1.metric("Total Employees", total)
col2.metric("High Risk", high, delta=f"{high/total:.0%}", delta_color="inverse")
col3.metric("Medium Risk", medium)
col4.metric("Low Risk", low)
col5.metric("Flight Patterns Detected", patterns)

st.divider()

# Department filter
departments = ["All"] + sorted(df["DEPARTMENT"].unique().tolist())
selected_dept = st.selectbox("Filter by Department", departments)

if selected_dept != "All":
    filtered = df[df["DEPARTMENT"] == selected_dept]
else:
    filtered = df

# Charts row
left, mid, right = st.columns([1, 1, 1])

color_map = {"High": "#e74c3c", "Medium": "#f39c12", "Low": "#2ecc71"}

with left:
    st.subheader("Risk Distribution")
    tier_counts = filtered["RISK_TIER"].value_counts().reset_index()
    tier_counts.columns = ["Risk Tier", "Count"]
    fig1 = px.bar(tier_counts, x="Risk Tier", y="Count", color="Risk Tier",
                  color_discrete_map=color_map, title=f"Risk Tiers — {selected_dept}")
    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with mid:
    st.subheader("Risk by Department")
    dept_risk = df.groupby(["DEPARTMENT", "RISK_TIER"]).size().reset_index(name="Count")
    fig2 = px.bar(dept_risk, x="DEPARTMENT", y="Count", color="RISK_TIER",
                  color_discrete_map=color_map, title="Department Breakdown", barmode="stack")
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

with right:
    st.subheader("Flight Risk Patterns")
    pattern_counts = filtered[filtered["FLIGHT_PATTERN"] != "Normal"]["FLIGHT_PATTERN"].value_counts().reset_index()
    pattern_counts.columns = ["Pattern", "Count"]
    pattern_colors = {"Quiet Quitting": "#9b59b6", "Poach Risk": "#e74c3c", "Lost in Crowd": "#3498db", "Stagnating": "#f39c12"}
    if not pattern_counts.empty:
        fig3 = px.bar(pattern_counts, x="Pattern", y="Count", color="Pattern",
                      color_discrete_map=pattern_colors, title="Detected Patterns")
        fig3.update_layout(showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No flight patterns in this department")

st.divider()

# Manager Hotspot (innovation)
st.subheader("Manager Hotspot — Who Needs HR Support?")
mgr = filtered.groupby("MANAGER_ID").agg(
    TEAM_COUNT=("EMPLOYEE_ID", "count"),
    AVG_RISK=("RISK_SCORE", "mean"),
    HIGH_RISK_COUNT=("RISK_TIER", lambda x: (x == "High").sum()),
    DEPT=("DEPARTMENT", "first")
).reset_index().sort_values("AVG_RISK", ascending=False)
mgr.columns = ["Manager ID", "Team Count", "Avg Risk Score", "High Risk Employees", "Department"]
st.dataframe(mgr.head(10), use_container_width=True, hide_index=True)

st.divider()

# Top 5 highest risk employees (bonus)
st.subheader("Top 5 Highest-Risk Employees")
top5 = filtered.nlargest(5, "RISK_SCORE")[["EMPLOYEE_ID", "EMPLOYEE_NAME", "DEPARTMENT", "TENURE_YEARS",
    "PERFORMANCE_RATING", "MONTHS_SINCE_PROMOTION", "RISK_SCORE", "RISK_TIER", "FLIGHT_PATTERN"]]
st.dataframe(top5, use_container_width=True, hide_index=True)

# Retention action for selected employee (innovation)
st.subheader("Retention Action Plan")
emp_list = filtered.sort_values("RISK_SCORE", ascending=False)["EMPLOYEE_ID"].tolist()
selected_emp = st.selectbox("Select employee for action plan", emp_list)

if selected_emp:
    emp = filtered[filtered["EMPLOYEE_ID"] == selected_emp].iloc[0]
    ecol1, ecol2, ecol3 = st.columns(3)
    ecol1.metric("Risk Score", emp["RISK_SCORE"])
    ecol2.metric("Risk Tier", emp["RISK_TIER"])
    ecol3.metric("Flight Pattern", emp["FLIGHT_PATTERN"])

    if st.button("Generate Check-in Plan", type="primary"):
        with st.spinner("Generating personalized retention plan..."):
            prompt = f"""You are an HR advisor. Generate a brief 15-minute check-in agenda for a manager meeting with an employee who may be at risk of leaving.

Employee: {emp['EMPLOYEE_NAME']}
Department: {emp['DEPARTMENT']}
Tenure: {emp['TENURE_YEARS']} years
Performance Rating: {emp['PERFORMANCE_RATING']}/5
Months Since Promotion: {emp['MONTHS_SINCE_PROMOTION']}
Risk Score: {emp['RISK_SCORE']}/100
Flight Pattern: {emp['FLIGHT_PATTERN']}

Provide:
1. A warm opening question
2. Two probing questions specific to their risk factors
3. One actionable next step the manager can commit to
Keep it concise and empathetic."""

            try:
                resp = session.sql(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${prompt}$$) AS PLAN").collect()
                st.success("Check-in agenda generated:")
                st.markdown(resp[0]["PLAN"])
            except Exception as e:
                st.error(f"Could not generate plan: {str(e)}")

st.divider()

# Full filterable table
st.subheader("All Employees")
risk_filter = st.multiselect("Filter by Risk Tier", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
table_data = filtered[filtered["RISK_TIER"].isin(risk_filter)].sort_values("RISK_SCORE", ascending=False)
st.dataframe(
    table_data[["EMPLOYEE_ID", "EMPLOYEE_NAME", "DEPARTMENT", "MANAGER_ID", "TENURE_YEARS",
                "PERFORMANCE_RATING", "MONTHS_SINCE_PROMOTION", "TEAM_SIZE", "PROMOTION_URGENCY",
                "RISK_SCORE", "RISK_TIER", "FLIGHT_PATTERN"]],
    use_container_width=True, hide_index=True
)

# Scoring logic
with st.expander("How is the Risk Score calculated?"):
    st.markdown("""
**Risk Score (0-100+)** is calculated from three factors with a team size multiplier:

**Tenure Risk** (max 30): < 2 years = 30, 2-5 years = 15, 5+ years = 5

**Performance Risk** (max 35): Rating 1-2 = 35, Rating 3 = 15, Rating 4-5 = 5

**Promotion Risk** (max 35): > 36 months = 35, 18-36 months = 20, < 18 months = 5

**Team Size Multiplier** (innovation): 15+ employees = 1.2x, 10-14 = 1.1x, <10 = 1.0x

**Flight Risk Patterns** (innovation — combo detection):
- *Quiet Quitting*: Low performance + long tenure (checked out but staying)
- *Poach Risk*: High performance + no promotion (competitor will grab them)
- *Lost in Crowd*: New hire + large team (not getting attention)
- *Stagnating*: Average performance + long promotion wait (giving up)

**Promotion Urgency Index**: months_since_promotion / tenure_years (higher = more urgent)

**Manager Hotspot**: Avg risk score per manager — flags which managers need HR support first
    """)

st.markdown("**Platform:** Snowflake SQL + Cortex COMPLETE + Streamlit in Snowflake | Data: hr_attrition.csv")