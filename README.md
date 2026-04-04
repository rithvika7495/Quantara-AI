# Quantara_AI 🚀

Quantara_AI is an AI-powered agentic analytics system that converts natural language queries into SQL and delivers structured data insights, trends, and predictions.

This project combines LLM-based query understanding with DuckDB-powered analytics to create a scalable and intelligent data analysis engine.

---

## ✨ Key Features

- 🧠 Natural Language → SQL (LLM-powered)
- ⚡ DuckDB-based high-performance query engine
- 🛡️ Schema-aware SQL generation (reduces hallucinations)
- 🔁 Automatic SQL correction loop
- 🧵 Thread-based conversational memory
- ⚡ Query result caching
- 📊 Business insights (trend + anomaly detection)
- 🔮 Predictive analytics (ML-based forecasting)
- 📂 Dynamic dataset loading (CSV or relational datasets)
- 🏗️ Supports large datasets (DuckDB streaming)
- 🔗 Relational dataset support (Instacart-style joins)

---

## 🧠 System Architecture
User Query
↓
LLM (SQL Generation)
↓
SQL Validation + Correction
↓
DuckDB Execution
↓
Result
↓
Insights + Prediction


---

## 📊 Dataset

This project uses the **Instacart Online Grocery Dataset (2017)**, a public dataset designed for market basket analysis.

It contains anonymized customer orders, products, aisles, and departments, enabling realistic retail analytics workflows.

Dataset source:  
https://www.instacart.com/datasets/grocery-shopping-2017

> Note: Revenue values in this project are synthetically generated for demonstration purposes, as the original dataset does not include pricing information.

---


## 📂 Supported Data Inputs

### ✅ Single CSV

/path/to/data.csv


### ✅ Large CSV (GB-scale)
- Processed efficiently using DuckDB (no full memory load)

### ✅ Relational Dataset (Instacart-style)
├── orders.csv
├── order_products__prior.csv
├── products.csv
├── aisles.csv
└── departments.csv

## ▶️ Usage

Run:  python app.py 
Then:

1. Enter dataset path (CSV or folder)
2. Ask questions in natural language

🧪 Example Queries:
 sales by department
top products in snacks
analyze revenue trend
which aisle is performing best
predict sales
forecast revenue next 7 days
predict sales for dairy department


🧠 Insights Engine

Automatically generates:

📈 Trend detection
⚠️ Anomaly detection
💡 Business explanations
📊 Summary statistics
⚠️ Version

Version 1 (V1)

This version includes:

Core agentic analytics pipeline
SQL generation + validation
Insight + prediction layers
🚀 Future Roadmap

Planned improvements include:

📂 Allow users to upload and analyze their own datasets seamlessly
🧠 Automatic schema detection and column mapping
🗄️ Direct integration with enterprise databases (PostgreSQL, MySQL, Snowflake, etc.)
🔗 Multi-table reasoning with LLM-driven joins
📊 Interactive UI / dashboard
🤖 Advanced ML models (XGBoost, Prophet, deep learning)
🤝 Contributing

This project is open for contributions 🚀

You can contribute by:

Improving SQL generation accuracy
Enhancing prediction models
Optimizing performance
Building UI / visualization layers

Pull requests are welcome!

🧑‍💻 Author

Built with focus on real-world AI + analytics system design.
