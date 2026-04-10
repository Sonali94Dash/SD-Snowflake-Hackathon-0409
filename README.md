# SD-Snowflake-Hackathon-0409

## Customer Churn Classification with SHAP Explainability
**Built by Sonali Dash** | CSEGSA Hackathon 2026

---

### Problem Statement
Predict customer churn using behavioral and HR signals, explain predictions with SHAP values, and surface results through an interactive Streamlit dashboard — all within Snowflake.

### Key Results
| Metric | Score |
|--------|-------|
| AUC | 0.9354 |
| Precision | 0.9574 |
| Recall | 0.8824 |
| F1 Score | 0.9184 |

---

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SNOWFLAKE PLATFORM                          │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │ 5 CSV    │───>│ Snowpark     │───>│ Feature Store          │  │
│  │ Sources  │    │ Feature Eng. │    │ SD_CHURN_FEATURE_VIEW  │  │
│  └──────────┘    └──────────────┘    └───────────┬───────────┘  │
│                                                  │              │
│  ┌──────────────────────────────────────────────┐│              │
│  │ GradientBoosting Classifier (18 features)    ││              │
│  │ snowflake.ml.modeling.ensemble               │◄              │
│  └──────────────────┬───────────────────────────┘              │
│                     │                                           │
│  ┌──────────────────▼───────────────────────────┐              │
│  │ Model Registry: SD_CHURN_CLASSIFIER V3       │              │
│  └──────────────────┬───────────────────────────┘              │
│                     │                                           │
│  ┌──────────────────▼──────┐  ┌─────────────────────────────┐  │
│  │ SHAP Explainability     │  │ Streamlit Dashboard          │  │
│  │ TreeExplainer           │  │ SD_EmployeeChurn_Dashboard   │  │
│  │ Global + Per-Customer   │  │ Segments + SHAP + Lookup     │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Data Sources (5 tables)

| File | Rows | Description |
|------|------|-------------|
| `hr_attrition.csv` | 1,000 | Employee HR attributes + attrition risk label |
| `tool_adoption.csv` | 11,971 | Daily platform usage logs (sessions, actions) |
| `prompt_quality.csv` | 11,820 | AI/LLM usage quality metrics |
| `access_logs.csv` | 1,538 | Data table access audit trail |
| `contract_metadata.csv` | 500 | Vendor contract risk metadata |

### Churn Proxy Definition
Binary label combining HR risk assessment + behavioral inactivity signals:
- `churn = 1` if HR attrition_risk_label = 'High'
- `churn = 1` if engagement_score < 2.5 AND last tool activity > 60 days ago
- `churn = 1` if avg_sessions < 2 AND HR label = 'Medium'
- `churn = 0` otherwise

Result: 238 churners (23.8%) / 762 non-churners (76.2%)

### Engineered Features (18 total)

**From HR:** tenure_years, performance_rating, salary_band_num, months_since_promotion, engagement_score, team_size

**From Behavioral Data:** avg_sessions, avg_actions, total_tool_days, avg_queries, avg_prompts, avg_quality

**From Contracts (dept-level):** dept_contract_count, dept_avg_contract_value, dept_high_risk_contracts, dept_avg_liability

**Derived:** promotion_stagnation (months_since_promotion / tenure), engagement_per_team (engagement_score / team_size)

### Top 5 Churn Drivers (SHAP)
1. **ENGAGEMENT_SCORE** — Mean |SHAP| = 2.9963 (dominant driver)
2. **PERFORMANCE_RATING** — Mean |SHAP| = 0.9296
3. **TEAM_SIZE** — Mean |SHAP| = 0.8591
4. **MONTHS_SINCE_PROMOTION** — Mean |SHAP| = 0.8495
5. **ENGAGEMENT_PER_TEAM** — Mean |SHAP| = 0.7710

---

### Snowflake Objects Created

| Object Type | Name |
|-------------|------|
| Database/Schema | `HACKATHON_DB.ML_CHURN` |
| Raw Tables | `RAW_HR_ATTRITION`, `RAW_ACCESS_LOGS`, `RAW_TOOL_ADOPTION`, `RAW_PROMPT_QUALITY`, `RAW_CONTRACT_METADATA` |
| Labeled Table | `LABELED_CHURN` |
| Feature Table | `FEATURES_TRAINING` |
| Predictions | `PREDICTIONS_BATCH` |
| SHAP Tables | `SHAP_FEATURE_IMPORTANCE`, `SHAP_VALUES` |
| Metrics | `MODEL_METRICS` |
| Feature Store Entity | `SD_EMPLOYEE_ENTITY` |
| Feature Store View | `SD_CHURN_FEATURE_VIEW V1` |
| Model Registry | `SD_CHURN_CLASSIFIER V3` |
| Streamlit App | `SD_EmployeeChurn_Dashboard` |
| Stage | `CHURN_STAGE` |

---

### Setup Instructions

#### Prerequisites
- Snowflake trial account (Standard or Enterprise edition)
- ACCOUNTADMIN role access

#### Step 1: Create workspace
```sql
CREATE DATABASE IF NOT EXISTS HACKATHON_DB;
CREATE SCHEMA IF NOT EXISTS HACKATHON_DB.ML_CHURN;
USE SCHEMA HACKATHON_DB.ML_CHURN;
```

#### Step 2: Upload data
1. Create internal stage: `CREATE OR REPLACE STAGE churn_stage;`
2. Upload all 5 CSV files to the stage via Snowsight UI
3. Run COPY INTO commands (see notebook Cell 2)

#### Step 3: Run the notebook
1. Open `SD_Churn_Pipeline.ipynb` in Snowflake Notebooks
2. Run all cells sequentially (top to bottom)
3. Notebook creates all tables, trains model, generates SHAP values

#### Step 4: Deploy Streamlit app
1. Create new Streamlit App in Snowsight → `SD_EmployeeChurn_Dashboard`
2. Set database: `HACKATHON_DB`, schema: `ML_CHURN`, warehouse: `COMPUTE_WH`
3. Add `plotly` package in Packages dropdown
4. Paste code from `streamlit_app.py`

---

### Repo Structure
```
├── README.md
├── SD_Churn_Pipeline.ipynb    # End-to-end Snowflake notebook
├── streamlit_app.py           # Streamlit dashboard code
├── data/
│   ├── hr_attrition.csv
│   ├── tool_adoption.csv
│   ├── prompt_quality.csv
│   ├── access_logs.csv
│   └── contract_metadata.csv
```

### Snowflake Platform Features Used
- **Snowpark Python** — Feature engineering, data joins, transformations
- **Feature Store** — Versioned feature views with entity registration
- **ML Modeling API** — `snowflake.ml.modeling.ensemble.GradientBoostingClassifier`
- **Model Registry** — Versioned model logging and governance
- **SHAP (TreeExplainer)** — Global and per-customer explainability
- **Streamlit in Snowflake** — Interactive dashboard with 3 panels https://app.snowflake.com/streamlit/us-east-1/mfc26167/#/apps/6oha2hfb24uhlaaykt5i

### Security & Governance
- All data stays within Snowflake — no external data movement
- Model versioned in registry (reproducibility)
- Feature definitions governed via Feature Store
- SHAP explanations attached to every prediction (auditability)
