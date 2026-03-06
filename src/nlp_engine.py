"""
NLP Engine for converting natural language questions to SQL queries.

Uses OpenAI's GPT models to understand questions and generate appropriate SQL
based on schema context and business rules.
"""

import os
from pathlib import Path
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

CONTEXT_DIR = Path(__file__).parent.parent / "context"


def load_context() -> str:
    """Load schema and business rules context files."""
    schema_path = CONTEXT_DIR / "schema.md"
    rules_path = CONTEXT_DIR / "business_rules.md"
    
    context_parts = []
    
    if schema_path.exists():
        context_parts.append(schema_path.read_text())
    
    if rules_path.exists():
        context_parts.append(rules_path.read_text())
    
    return "\n\n---\n\n".join(context_parts)


SYSTEM_PROMPT = """You are a SQL expert assistant for a SaaS analytics database. Your job is to help users understand and query their data.

## What You Can Do

1. **Generate SQL queries** for data questions
2. **Answer schema questions** like "what columns are available?" or "what tables do you have?"
3. **Suggest alternatives** if a requested column doesn't exist

## SQL Generation Rules

1. Generate valid SQL that will run on DuckDB
2. Use ONLY SELECT statements - never INSERT, UPDATE, DELETE, DROP, or any DDL
3. Always include appropriate column aliases for clarity
4. Use DATE_TRUNC for time-based grouping
5. Order results in a logical way (usually by date or by the metric being analyzed)
6. Limit results to 1000 rows maximum unless the user asks for more
7. When calculating percentages, round to 2 decimal places

## Handling Missing Columns

If a user asks for something that doesn't exist (like "segment"), suggest the closest alternative:
- "segment" → suggest using `plan` (subscription tier)
- "revenue" → suggest using `arr` or `mrr`
- "customer" → suggest using `users` table
- "activity" → suggest using `events` table

Respond helpfully with what's available and how to get similar insights.

## Critical: Revenue Calculations (Annual Plans)

ALL subscriptions are ANNUAL CONTRACTS. Key columns:
- `arr` = Annual Recurring Revenue (what customer pays per year)
- `mrr` = Monthly Recurring Revenue = arr / 12 (pre-calculated)
- `start_date`, `end_date` (NULL if active), `status`

### ARR is the primary metric
- Current ARR: `SUM(arr) WHERE status = 'active'`

### MRR is DERIVED from ARR
- MRR = ARR / 12
- Current MRR: `SUM(arr) / 12 WHERE status = 'active'` OR `SUM(mrr) WHERE status = 'active'`

### Time-based calculations
A subscription contributes to revenue only during months it was active:
- Active during a month if: `start_date <= end_of_month AND (end_date >= start_of_month OR end_date IS NULL)`

## Example Queries

Question: "What's our current ARR?"
SQL: SELECT SUM(arr) as current_arr FROM subscriptions WHERE status = 'active'

Question: "What's our current MRR?"
SQL: SELECT SUM(arr) / 12 as current_mrr FROM subscriptions WHERE status = 'active'

Question: "What was MRR in January 2025?"
SQL: SELECT SUM(arr) / 12 as mrr FROM subscriptions WHERE start_date <= '2025-01-31' AND (end_date >= '2025-01-01' OR end_date IS NULL)

Question: "Show MRR trend by month"
SQL: WITH months AS (SELECT DISTINCT DATE_TRUNC('month', start_date) as month FROM subscriptions) SELECT m.month, COALESCE(SUM(s.arr) / 12, 0) as mrr FROM months m LEFT JOIN subscriptions s ON s.start_date <= (m.month + INTERVAL '1 month' - INTERVAL '1 day') AND (s.end_date >= m.month OR s.end_date IS NULL) GROUP BY m.month ORDER BY m.month

Question: "Show new ARR added each month"
SQL: SELECT DATE_TRUNC('month', start_date) as month, SUM(arr) as new_arr FROM subscriptions GROUP BY 1 ORDER BY 1

Question: "What's the churn rate by plan?"
SQL: SELECT plan, COUNT(CASE WHEN status = 'churned' THEN 1 END) as churned, COUNT(*) as total, ROUND(100.0 * COUNT(CASE WHEN status = 'churned' THEN 1 END) / COUNT(*), 2) as churn_rate FROM subscriptions GROUP BY plan ORDER BY churn_rate DESC

Question: "How many active users in the last 30 days?"
SQL: SELECT COUNT(DISTINCT user_id) as active_users FROM events WHERE timestamp >= CURRENT_DATE - INTERVAL 30 DAY

## Response Format

For data questions: Respond with ONLY the SQL query, no explanations or markdown code blocks.

For schema questions (like "what columns do you have?"): Start your response with "SCHEMA:" and then provide a helpful explanation of the available tables and columns.

For questions where you need to suggest alternatives: Start with "SUGGESTION:" and explain what's available.

If you truly cannot help, respond with: ERROR: <brief explanation>

## Context

{context}
"""


class NLPEngine:
    """Converts natural language questions to SQL queries using OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.context = load_context()
        self.system_prompt = SYSTEM_PROMPT.format(context=self.context)
    
    def generate_sql(self, question: str, conversation_history: list = None) -> dict:
        """
        Convert a natural language question to SQL.
        
        Args:
            question: The current question
            conversation_history: Optional list of previous Q&A pairs for context
                Each item: {"question": str, "sql": str, "summary": str}
        
        Returns:
            dict with keys:
                - sql: The generated SQL query (or None if error)
                - error: Error message (or None if success)
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            if conversation_history:
                for item in conversation_history[-5:]:  # Keep last 5 exchanges for context
                    messages.append({"role": "user", "content": item["question"]})
                    messages.append({"role": "assistant", "content": item["sql"]})
            
            messages.append({"role": "user", "content": question})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=1000,
            )
            
            response_text = response.choices[0].message.content.strip()
            
            if response_text.startswith("ERROR:"):
                return {"sql": None, "error": response_text[6:].strip(), "message": None}
            
            if response_text.startswith("SCHEMA:"):
                return {"sql": None, "error": None, "message": response_text[7:].strip()}
            
            if response_text.startswith("SUGGESTION:"):
                return {"sql": None, "error": None, "message": response_text[11:].strip()}
            
            sql = self._clean_sql(response_text)
            
            if not self._is_safe_sql(sql):
                return {"sql": None, "error": "Query contains unsafe operations", "message": None}
            
            return {"sql": sql, "error": None, "message": None}
            
        except Exception as e:
            return {"sql": None, "error": str(e)}
    
    def _clean_sql(self, sql: str) -> str:
        """Remove markdown code blocks and clean up the SQL."""
        if sql.startswith("```"):
            lines = sql.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            sql = "\n".join(lines)
        
        return sql.strip()
    
    def _is_safe_sql(self, sql: str) -> bool:
        """Check if the SQL is safe to execute (SELECT only)."""
        sql_upper = sql.upper().strip()
        
        unsafe_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
            "TRUNCATE", "GRANT", "REVOKE", "EXECUTE", "EXEC"
        ]
        
        for keyword in unsafe_keywords:
            if keyword in sql_upper.split():
                return False
        
        return sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")
    
    def explain_results(self, question: str, sql: str, results_summary: str) -> str:
        """
        Generate a natural language explanation of the query results.
        
        Args:
            question: The original question
            sql: The SQL that was executed
            results_summary: A text summary of the results (first few rows, stats)
        
        Returns:
            Natural language explanation of the results
        """
        prompt = f"""Based on the following query and results, provide a brief, 
conversational explanation of the findings.

Original question: {question}

SQL executed:
{sql}

Results summary:
{results_summary}

Provide a 1-3 sentence explanation of what the data shows. Be specific with numbers 
and trends. Don't explain the SQL, just interpret the results."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst explaining query results."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Could not generate explanation: {e}"


def get_nlp_engine() -> NLPEngine:
    """Get an NLP engine instance."""
    return NLPEngine()
