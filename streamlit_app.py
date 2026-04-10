import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import plotly.express as px

session = get_active_session()

st.set_page_config(page_title="SD Churn Explainer", layout="wide")
st.markdown("""
    <style>
    .stApp {
        background-color: #f0fff0;
    }
    </style>
""", unsafe_allow_html=True)
st.title("Snowflake Customer Churn Predictor")
st.caption("Built by Sonali Dash | Snowflake ML + SHAP Explainability")

predictions = session.table("PREDICTIONS_BATCH").to_pandas()
shap_importance = session.table("SHAP_FEATURE_IMPORTANCE").to_pandas()
shap_values = session.table("SHAP_VALUES").to_pandas()
metrics = session.table("MODEL_METRICS").to_pandas()

col1, col2, col3, col4 = st.columns(4)
churn_rate = predictions["PREDICTED_CHURN"].mean()
col1.metric("Churn Rate", f"{churn_rate:.1%}")
col2.metric("High-Risk Customers", int(predictions["PREDICTED_CHURN"].sum()))
col3.metric("AUC Score", f"{metrics['AUC'].values[0]:.4f}")
col4.metric("F1 Score", f"{metrics['F1_SCORE'].values[0]:.4f}")

st.divider()

tab1, tab2, tab3 = st.tabs(["Segment Breakdown", "SHAP Explainability", "Per-Customer Lookup"])

with tab1:
    st.subheader("Churn Rate by Department")
    dept_churn = predictions.groupby("DEPARTMENT").agg(
        TOTAL=("PREDICTED_CHURN", "count"),
        CHURNERS=("PREDICTED_CHURN", "sum"),
        CHURN_RATE=("PREDICTED_CHURN", "mean")
    ).reset_index().sort_values("CHURN_RATE", ascending=False)

    fig1 = px.bar(
        dept_churn,
        x="DEPARTMENT",
        y="CHURN_RATE",
        color="CHURN_RATE",
        color_continuous_scale="Reds",
        text=dept_churn["CHURN_RATE"].apply(lambda x: f"{x:.1%}"),
        title="Churn Rate by Department"
    )
    fig1.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig1, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("HR Risk Label vs Predicted Churn")
        risk_churn = predictions.groupby("ATTRITION_RISK_LABEL")["PREDICTED_CHURN"].mean().reset_index()
        fig_risk = px.bar(
            risk_churn,
            x="ATTRITION_RISK_LABEL",
            y="PREDICTED_CHURN",
            color="ATTRITION_RISK_LABEL",
            title="Predicted Churn by HR Risk Label"
        )
        st.plotly_chart(fig_risk, use_container_width=True)

    with col_b:
        st.subheader("Churn Distribution")
        fig_dist = px.histogram(
            predictions,
            x="PREDICTED_CHURN",
            nbins=2,
            title="Predicted Churn Distribution",
            labels={"PREDICTED_CHURN": "Predicted Label"}
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    st.subheader("Top Risky Customers")
    risky = predictions[predictions["PREDICTED_CHURN"] == 1].sort_values("EMPLOYEE_ID")
    st.dataframe(
        risky[["EMPLOYEE_ID", "DEPARTMENT", "ATTRITION_RISK_LABEL", "PREDICTED_CHURN"]].rename(
            columns={"EMPLOYEE_ID": "Customer ID", "DEPARTMENT": "Department", "ATTRITION_RISK_LABEL": "HR Risk", "PREDICTED_CHURN": "Churn Predicted"}
        ),
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.subheader("Top Churn Drivers (Global SHAP Importance)")
    shap_sorted = shap_importance.sort_values("MEAN_ABS_SHAP", ascending=True)
    fig2 = px.bar(
        shap_sorted,
        x="MEAN_ABS_SHAP",
        y="FEATURE_NAME",
        orientation="h",
        title="Feature Importance (Mean |SHAP|)",
        color="MEAN_ABS_SHAP",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 5 Churn Drivers")
    for idx, row in shap_importance.head(5).iterrows():
        st.write(f"**{row['FEATURE_NAME']}**: Mean |SHAP| = {row['MEAN_ABS_SHAP']:.4f}")

    st.subheader("Model Performance Summary")
    met_col1, met_col2, met_col3, met_col4 = st.columns(4)
    met_col1.metric("AUC", f"{metrics['AUC'].values[0]:.4f}")
    met_col2.metric("Precision", f"{metrics['PRECISION_SCORE'].values[0]:.4f}")
    met_col3.metric("Recall", f"{metrics['RECALL'].values[0]:.4f}")
    met_col4.metric("F1 Score", f"{metrics['F1_SCORE'].values[0]:.4f}")

with tab3:
    st.subheader("Individual Customer Explainability")
    emp_list = predictions["EMPLOYEE_ID"].sort_values().tolist()
    selected_emp = st.selectbox("Select Customer", emp_list)

    emp_pred = predictions[predictions["EMPLOYEE_ID"] == selected_emp].iloc[0]
    emp_shap = shap_values[shap_values["EMPLOYEE_ID"] == selected_emp]

    col_x, col_y, col_z = st.columns(3)
    col_x.metric("Predicted Churn", "Yes" if emp_pred["PREDICTED_CHURN"] == 1 else "No")
    col_y.metric("Department", emp_pred["DEPARTMENT"])
    col_z.metric("HR Risk Label", emp_pred["ATTRITION_RISK_LABEL"])

    if not emp_shap.empty:
        feature_cols = [c for c in emp_shap.columns if c not in ["EMPLOYEE_ID", "BASE_VALUE", "MODEL_VERSION"]]
        emp_shap_vals = emp_shap[feature_cols].iloc[0]
        emp_shap_df = pd.DataFrame({
            "Feature": emp_shap_vals.index,
            "SHAP Value": emp_shap_vals.values
        }).sort_values("SHAP Value", key=abs, ascending=True)

        fig3 = px.bar(
            emp_shap_df,
            x="SHAP Value",
            y="Feature",
            orientation="h",
            color="SHAP Value",
            color_continuous_scale="RdBu_r",
            title=f"SHAP Breakdown for {selected_emp}"
        )
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Top Positive and Negative Contributors")
        top_pos = emp_shap_df[emp_shap_df["SHAP Value"] > 0].tail(3)
        top_neg = emp_shap_df[emp_shap_df["SHAP Value"] < 0].head(3)
        cp, cn = st.columns(2)
        with cp:
            st.write("**Pushing toward churn:**")
            for _, r in top_pos.iterrows():
                st.write(f"- {r['Feature']}: +{r['SHAP Value']:.4f}")
        with cn:
            st.write("**Pushing away from churn:**")
            for _, r in top_neg.iterrows():
                st.write(f"- {r['Feature']}: {r['SHAP Value']:.4f}")
    else:
        st.info("No SHAP values available for this customer (not in test set)")

st.divider()
st.markdown("**Pipeline:** Snowpark Feature Engineering > Feature Store > GradientBoosting Classifier > Model Registry > SHAP Explainability > Streamlit Dashboard")
st.markdown("**Snowflake Objects:** HACKATHON_DB.ML_CHURN | Feature Store: SD_EMPLOYEE_ENTITY, SD_CHURN_FEATURE_VIEW_V1 | Model Registry: SD_CHURN_CLASSIFIER_V3")
