# Conversational BI with Cortex Analyst
**AI Prompt 02 | Built by Sonali Dash | CSEGSA Hackathon 2026**

---

## Problem Statement
Build a natural language analytics interface using Cortex Analyst. Users ask business questions in plain English and receive SQL-backed charts, summaries, and insights — zero SQL required.

## Architecture
```
User Question (Plain English)
        |
        v
Streamlit Chat Interface
        |
        v
Cortex Analyst REST API  <-->  Semantic Model YAML (on Stage)
        |
        v
Generated SQL  -->  Snowflake Warehouse  -->  Results
        |                                       |
        v                                       v
SQL Transparency Panel              Plotly Charts (auto-detected)
                                            |
                                            v
                                Cortex COMPLETE (mistral-large2)
                                            |
                                            v
                                Executive Summary (3 sentences)
```

## Data Sources
| Table | Records | Description |
|-------|---------|-------------|
| FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES | 164K+ variables | GDP, CPI, SOFR, federal funds rate, treasury yields, housing, retail sales |
| FINANCIAL_ECONOMIC_INDICATORS_ATTRIBUTES | 164K+ variables | Metadata: report source, measure, industry, frequency |
| BUREAU_OF_LABOR_STATISTICS_EMPLOYMENT_TIMESERIES | 22M+ records | JOLTS hires, quits, job openings, separations (1939-present) |
| BUREAU_OF_LABOR_STATISTICS_EMPLOYMENT_ATTRIBUTES | Metadata | BLS report type, measure, industry, establishment size |

Source: Snowflake Marketplace — "Snowflake Data: Finance & Economics" (free)

## Semantic Model
- 4 tables with dimensions, time_dimensions, and measures
- 2 relationships (timeseries → attributes via VARIABLE key)
- Rich synonyms (GDP, CPI, SOFR, JOLTS, etc.)
- 10 verified queries as few-shot examples
- Iteratively refined based on NL query testing

## NL Query Log (15+ tested)
| # | Question | SQL OK | Chart | Notes |
|---|----------|--------|-------|-------|
| 1 | Show me the latest 10 economic indicators | Yes | Yes | Top values by date |
| 2 | What is the GDP trend over the last 5 years? | Yes | Yes | Line chart |
| 3 | Show CPI data | Yes | Yes | Time series |
| 4 | What is the federal funds rate? | Yes | Yes | Rate over time |
| 5 | Show JOLTS hires data by industry | Yes | Yes | Bar chart by industry |
| 6 | Show job openings trend | Yes | Yes | Line chart |
| 7 | Which industries have the highest quit rates? | Yes | Yes | Ranked bar |
| 8 | How many indicators does each source publish? | Yes | Yes | By agency |
| 9 | Which BLS reports have the most data? | Yes | Yes | Report ranking |
| 10 | Show treasury yield data | Yes | Yes | Time series |
| 11 | What was the SOFR rate last month? | Yes | Yes | Recent data |
| 12 | Compare hires vs quits for manufacturing | Yes | Yes | Comparison |
| 13 | How is the economy doing? | Ambiguous | No | Too vague - needs specific indicator |
| 14 | Show monthly employment data for 2024 | Yes | Yes | Filtered by year |
| 15 | What are the top 5 industries by job openings? | Yes | Yes | Ranked |
| 16 | Interest rates | Ambiguous | No | Multiple types - needs clarification |
| 17 | What is the housing starts trend? | Yes | Yes | Time series |
| 18 | Show money supply data for the US | No results | No | Variable exists but filter too narrow. Fix: add M1/M2 synonyms |
| 19 | Which indicators are published quarterly? | Yes | Yes | Frequency filter |
| 20 | Compare separations vs hires in 2024 | Yes | Yes | Side by side |

## Snowflake Objects
| Object | Name |
|--------|------|
| Schema | HACKATHON_DB.CORTEX_BI |
| Stage | SEMANTIC_MODELS |
| Semantic Model | semantic_model.yaml |
| Streamlit App | SD_Cortex_Analyst |

## Snowflake Platform Features Used
- **Cortex Analyst** — NL to SQL via REST API with semantic model
- **Cortex COMPLETE** — Executive summary generation (mistral-large2)
- **Streamlit in Snowflake** — Chat interface with auto-charting
- **Snowflake Marketplace** — Finance & Economics free dataset
- **Semantic Model YAML** — 4 tables, 2 joins, 10 verified queries, rich synonyms

## Setup
1. Get "Snowflake Data: Finance & Economics" from Marketplace
2. Create schema and stage:
```sql
CREATE SCHEMA IF NOT EXISTS HACKATHON_DB.CORTEX_BI;
CREATE STAGE HACKATHON_DB.CORTEX_BI.SEMANTIC_MODELS DIRECTORY = (ENABLE = TRUE);
```
3. Upload `semantic_model.yaml` to stage
4. Create Streamlit app, paste `cortex_bi_app.py`, add `plotly` package
