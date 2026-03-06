# AI Analytics Tool

A lightweight AI-powered analytics tool that lets you query your data warehouse using natural language and visualize results with auto-generated dashboards.

Built as a learning project to understand how tools like Hex, Mode, and ThoughtSpot work under the hood.

## Features

- **Natural Language Queries**: Ask questions like "What's our MRR by month?" and get SQL + results
- **Auto-generated Charts**: Results are automatically visualized based on data shape
- **Pre-built Dashboards**: MRR trends, user growth, churn analysis
- **Schema Context**: AI understands your data through context files you provide

## Tech Stack

- **DuckDB**: Embedded analytical database (no server needed)
- **Streamlit**: Python web app framework for the UI
- **OpenAI GPT-4**: Powers the natural language to SQL conversion
- **Plotly**: Interactive charts and visualizations

## Prerequisites

- Python 3.10 or higher
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

## Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd hex-from-scratch
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your API key**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Generate the sample data**
   ```bash
   python data/generate_data.py
   ```

6. **Run the app**
   ```bash
   streamlit run app.py
   ```

7. **Open in browser**
   Navigate to http://localhost:8501

## Example Questions to Try

- "What's our total MRR?"
- "Show me user signups by month"
- "Which plan has the highest churn rate?"
- "What's the average subscription length?"
- "How many active users do we have?"
- "Show revenue by plan type"

## Project Structure

```
hex-from-scratch/
├── app.py                    # Main Streamlit application
├── data/
│   ├── generate_data.py      # Script to create fake SaaS data
│   └── saas_data.duckdb      # DuckDB database file (generated)
├── context/
│   ├── schema.md             # Table definitions for AI context
│   └── business_rules.md     # Domain knowledge
├── src/
│   ├── database.py           # DuckDB connection utilities
│   ├── nlp_engine.py         # OpenAI text-to-SQL logic
│   └── charts.py             # Visualization helpers
├── requirements.txt          # Python dependencies
├── .env.example              # Template for API keys
└── README.md                 # This file
```

## How It Works

1. **You ask a question** in natural language
2. **The NLP engine** sends your question + schema context to OpenAI
3. **OpenAI returns SQL** that answers your question
4. **DuckDB executes** the query against your data
5. **Results display** as a table and auto-generated chart

## Customizing for Your Data

To use this with your own data:

1. Replace the data generation script with your own data loading
2. Update `context/schema.md` with your table definitions
3. Update `context/business_rules.md` with your domain knowledge
4. The AI will use these context files to understand your data

## Learning Goals

This project demonstrates:
- How text-to-SQL works with LLMs
- Why schema documentation matters for AI accuracy
- The engineering behind "simple" dashboard features
- Trade-offs in build vs. buy decisions
