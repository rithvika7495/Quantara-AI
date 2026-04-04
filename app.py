# ---------------- WARNING FIX (MUST BE FIRST) ---------------- #
import warnings
warnings.filterwarnings("ignore")

# ---------------- IMPORTS ---------------- #
import pandas as pd
import re
import requests
import numpy as np
import duckdb
import time
from dateutil import parser

from semantic_validator import validate_semantics
from planner import detect_metrics_from_query
from predictor import predict_sales


# ---------------- THREAD MEMORY ---------------- #

threads = {"default": []}
current_thread = "default"

# ---------------- CACHE ---------------- #

cache = {}

def get_cached(sql):
    if sql in cache:
        data, ts = cache[sql]
        if time.time() - ts < 300:
            return data
    return None


def set_cache(sql, df):
    cache[sql] = (df, time.time())


# ---------------- STATE ---------------- #

cache_insights = {}
last_result = {}
last_query = {}


# ---------------- QUERY NORMALIZATION ---------------- #

def normalize_query(query):
    query = query.lower()

    corrections = {
        "saels": "sales",
        "revnue": "revenue",
        "departmnt": "department",
        "prodct": "product"
    }

    for w, c in corrections.items():
        query = query.replace(w, c)

    return query


# ---------------- DATE PARSER ---------------- #

def normalize_dates_in_query(query):
    words = query.split()
    new_words = []

    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+3])

        try:
            dt = parser.parse(chunk, fuzzy=False, dayfirst=True)
            new_words.append(dt.strftime("%Y-%m-%d"))
            i += 3
            continue
        except:
            pass

        chunk = " ".join(words[i:i+2])
        try:
            dt = parser.parse(chunk, fuzzy=False, dayfirst=True)
            new_words.append(dt.strftime("%Y-%m-%d"))
            i += 2
            continue
        except:
            pass

        try:
            dt = parser.parse(words[i], fuzzy=False, dayfirst=True)
            new_words.append(dt.strftime("%Y-%m-%d"))
        except:
            new_words.append(words[i])

        i += 1

    return " ".join(new_words)


# ---------------- INTENT DETECTION ---------------- #

def detect_intent(query):
    query = query.lower()

    wants_sql = "sql" in query
    wants_insight = any(w in query for w in ["insight", "analyze", "why", "explain"])
    wants_export = "excel" in query or "export" in query
    wants_prediction = any(w in query for w in ["predict", "forecast", "future"])

    if wants_prediction:
        return "predict"

    if wants_export:
        return "export"

    if wants_sql and wants_insight:
        return "all"

    if wants_sql and ("with" in query or "along" in query):
        return "data+sql"

    if wants_insight:
        return "insight"

    if wants_sql:
        return "sql"

    return "data"


# ---------------- SQL CLEAN ---------------- #

def extract_sql(text):
    text = re.sub(r"```sql", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)

    match = re.search(r"(SELECT .*?;)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match = re.search(r"(SELECT .*)", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


# ---------------- SCHEMA ---------------- #

def get_schema(df):
    return list(df.columns)


# ---------------- SQL VALIDATION ---------------- #

def validate_sql(sql, schema_cols):
    sql_lower = sql.lower()

    forbidden = ["products", "aisles", "departments", "retail_products"]
    for f in forbidden:
        if f in sql_lower:
            return False, f"Forbidden table used: {f}"

    tokens = re.findall(r"[a-zA-Z_]+", sql_lower)

    allowed_keywords = {
        "select","from","where","group","by","order","limit",
        "sum","avg","count","as","and","or","between","in",
        "desc","asc","on","retail"
    }

    allowed_cols = set([c.lower() for c in schema_cols])

    for t in tokens:
        if t not in allowed_cols and t not in allowed_keywords:
            return False, f"Invalid column: {t}"

    return True, "valid"


# ---------------- SQL GENERATION ---------------- #

def generate_sql(query, schema_cols):
    history = "\n".join([
        f"Q: {h['query']}\nSQL: {h['sql']}\nResult:\n{h['result_summary']}"
        for h in threads[current_thread][-3:]
    ]) if threads[current_thread] else ""

    metrics = detect_metrics_from_query(query)
    schema_text = ", ".join(schema_cols)

    prompt = f"""
You are a STRICT SQL generator.

TABLE: retail

SCHEMA:
{schema_text}

RULES:
- Use ONLY columns from schema
- DO NOT hallucinate columns
- DO NOT use joins
- Use 'date' for filtering

Conversation:
{history}

User Query:
{query}

Detected Metrics:
{metrics}

OUTPUT:
ONLY SQL
"""

    res = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": prompt, "stream": False}
    )

    return extract_sql(res.json()["response"])


# ---------------- SQL FIX ---------------- #

def fix_sql(sql, schema_cols, error_msg):
    prompt = f"""
Fix this SQL.

Error:
{error_msg}

Allowed columns:
{schema_cols}

SQL:
{sql}
"""

    res = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": prompt, "stream": False}
    )

    return extract_sql(res.json()["response"])


# ---------------- FEATURE ENGINEERING ---------------- #

def enrich_time_features(df):
    if "date" in df.columns and "revenue" in df.columns:
        df = df.sort_values("date")
        df["daily_sales"] = df["revenue"]
        df["moving_avg"] = df["revenue"].rolling(7).mean()
    return df


# ---------------- TREND ---------------- #

def detect_trend(df):
    if "moving_avg" in df.columns:
        trend = df["moving_avg"].diff().mean()

        if trend > 0:
            return "increasing 📈"
        elif trend < 0:
            return "decreasing 📉"
        else:
            return "stable ➡️"

    return "unknown"


# ---------------- ANOMALY ---------------- #

def detect_anomalies(df):
    if "daily_sales" in df.columns:
        mean = df["daily_sales"].mean()
        std = df["daily_sales"].std()

        threshold = mean + 2 * std
        anomalies = df[df["daily_sales"] > threshold]

        if anomalies.empty:
            return "No major anomalies detected."

        return anomalies.head(5).to_string(index=False)

    return "No anomaly logic applicable."


# ---------------- INSIGHTS ---------------- #

def generate_insights(df, query):
    if df.empty:
        return "No data."

    trend = detect_trend(df)
    anomalies = detect_anomalies(df)
    summary = df.describe(include='all').to_string()

    prompt = f"""
You are a senior business analyst.

User Question:
{query}

Trend:
{trend}

Data:
{df.head(10).to_string(index=False)}

Summary:
{summary}

Anomalies:
{anomalies}

Answer:

1. WHAT HAPPENED
2. WHY IT HAPPENED
3. WHAT TO DO NEXT
"""

    res = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": prompt, "stream": False}
    )

    return res.json()["response"]


# ---------------- EXPORT ---------------- #

def export_to_excel(df):
    file_name = "output.xlsx"
    df.to_excel(file_name, index=False)
    print(f"📁 Exported to {file_name}")


# ---------------- FALLBACK ---------------- #

def fallback_query(schema_cols):
    if "revenue" in schema_cols and "department" in schema_cols:
        return "SELECT department, SUM(revenue) as revenue FROM retail GROUP BY department"
    return "SELECT * FROM retail LIMIT 50"


# ---------------- INSTACART LOADER ---------------- #

def load_instacart_dataset(folder_path, con):
    try:
        print("📦 Loading Instacart dataset...")

        con.execute(f"CREATE OR REPLACE TABLE orders AS SELECT * FROM read_csv_auto('{folder_path}/orders.csv')")
        con.execute(f"CREATE OR REPLACE TABLE prior AS SELECT * FROM read_csv_auto('{folder_path}/order_products__prior.csv')")
        con.execute(f"CREATE OR REPLACE TABLE products AS SELECT * FROM read_csv_auto('{folder_path}/products.csv')")
        con.execute(f"CREATE OR REPLACE TABLE aisles AS SELECT * FROM read_csv_auto('{folder_path}/aisles.csv')")
        con.execute(f"CREATE OR REPLACE TABLE departments AS SELECT * FROM read_csv_auto('{folder_path}/departments.csv')")

        con.execute("""
        CREATE OR REPLACE TABLE retail AS
        SELECT 
            o.order_id AS transaction_id,
            o.user_id AS customer_id,
            p.product_name,
            a.aisle,
            d.department,
            DATE '2024-01-01' + o.order_dow AS date,
            RANDOM()*500 AS revenue
        FROM prior pr
        JOIN orders o ON pr.order_id = o.order_id
        JOIN products p ON pr.product_id = p.product_id
        JOIN aisles a ON p.aisle_id = a.aisle_id
        JOIN departments d ON p.department_id = d.department_id
        """)

        return con.execute("SELECT * FROM retail LIMIT 1000").fetchdf()

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# ---------------- MAIN ---------------- #

def main():
    global current_thread

    print("🚀 Loading data...")
    con = duckdb.connect()

    print("\n📂 Enter dataset path (CSV or Instacart folder): ")
    path = input("👉 ").strip()

    if path.endswith("/"):
        df_sample = load_instacart_dataset(path, con)
    else:
        con.execute(f"CREATE OR REPLACE TABLE retail AS SELECT * FROM read_csv_auto('{path}')")
        df_sample = con.execute("SELECT * FROM retail LIMIT 1000").fetchdf()

    if df_sample is None:
        return

    schema_cols = get_schema(df_sample)

    print("\n🤖 AI Analytics Ready!")

    chat_name = input("\n🧵 Enter chat name: ").strip() or "default"
    threads[chat_name] = []
    current_thread = chat_name

    while True:
        print("\n" + "=" * 50)
        query = input(f"[{current_thread}] 💬 Ask: ")

        if query in ["exit", "quit"]:
            break

        query = normalize_query(query)
        query = normalize_dates_in_query(query)

        intent = detect_intent(query)

        threads[current_thread].append({
            "query": query,
            "sql": "",
            "result_summary": ""
        })

        sql = generate_sql(query, schema_cols)

        valid, msg = validate_sql(sql, schema_cols)

        retry = 0
        while not valid and retry < 2:
            sql = fix_sql(sql, schema_cols, msg)
            valid, msg = validate_sql(sql, schema_cols)
            retry += 1

        if not valid:
            sql = fallback_query(schema_cols)

        cached = get_cached(sql)

        if cached is not None:
            result_df = cached
        else:
            result_df = con.execute(sql).fetchdf()
            set_cache(sql, result_df)

        threads[current_thread][-1]["sql"] = sql
        threads[current_thread][-1]["result_summary"] = result_df.head(3).to_string(index=False)

        if intent == "predict":
            pred_df = predict_sales(result_df)
            print("\n🔮 Forecast:\n", pred_df)
            continue

        print("\n📊 RESULT:\n", result_df.head())

        if intent in ["insight", "all"]:
            insights = generate_insights(result_df, query)
            print("\n💡 INSIGHTS:\n", insights)


if __name__ == "__main__":
    main()