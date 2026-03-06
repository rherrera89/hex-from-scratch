"""
AI Analytics Tool - Main Streamlit Application

A natural language interface for querying and visualizing SaaS data.
"""

import streamlit as st
import pandas as pd

from src.database import get_database, QueryError
from src.nlp_engine import NLPEngine
from src.charts import auto_chart, format_metric, line_chart, bar_chart

st.set_page_config(
    page_title="AI Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# No custom CSS - using Streamlit's default theme for better compatibility


@st.cache_resource
def get_db():
    """Get cached database connection."""
    return get_database()


@st.cache_resource
def get_nlp():
    """Get cached NLP engine."""
    try:
        return NLPEngine()
    except ValueError as e:
        return None


def render_sidebar():
    """Render the sidebar with navigation and info."""
    with st.sidebar:
        st.title("📊 AI Analytics")
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["💬 Ask Questions", "📈 Dashboards", "🔍 Explore Data"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### Example Questions")
        st.markdown("""
        - What's our total MRR?
        - Show user signups by month
        - Which plan has highest churn?
        - How many active users?
        - Revenue by plan type
        """)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This tool uses AI to convert your 
        questions into SQL queries and 
        visualize the results.
        
        Built with DuckDB, Streamlit, 
        and OpenAI.
        """)
        
        return page


def render_ask_questions():
    """Render the natural language query interface."""
    st.header("💬 Ask Questions About Your Data")
    
    nlp = get_nlp()
    if nlp is None:
        st.error("""
        ⚠️ OpenAI API key not configured.
        
        To use the AI query feature:
        1. Copy `.env.example` to `.env`
        2. Add your OpenAI API key
        3. Restart the app
        """)
        return
    
    db = get_db()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sql" in message:
                with st.expander("View SQL"):
                    st.code(message["sql"], language="sql")
            if "df" in message and message["df"] is not None:
                st.dataframe(message["df"], use_container_width=True)
                chart = auto_chart(message["df"])
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
    
    if prompt := st.chat_input("Ask a question about your data..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = nlp.generate_sql(prompt)
            
            if result["error"]:
                response = f"Sorry, I couldn't generate a query: {result['error']}"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                sql = result["sql"]
                
                with st.expander("View SQL", expanded=False):
                    st.code(sql, language="sql")
                
                try:
                    df = db.query(sql)
                    
                    if len(df) == 1 and len(df.columns) == 1:
                        value = df.iloc[0, 0]
                        col_name = df.columns[0]
                        if isinstance(value, (int, float)):
                            st.metric(col_name.replace("_", " ").title(), format_metric(value))
                        else:
                            st.metric(col_name.replace("_", " ").title(), str(value))
                    else:
                        st.dataframe(df, use_container_width=True)
                    
                    chart = auto_chart(df)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                    
                    with st.spinner("Generating explanation..."):
                        summary = df.head(10).to_string() if len(df) > 0 else "No results"
                        explanation = nlp.explain_results(prompt, sql, summary)
                    
                    st.markdown(f"**Summary:** {explanation}")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"**Summary:** {explanation}",
                        "sql": sql,
                        "df": df
                    })
                    
                except QueryError as e:
                    error_msg = f"Query failed: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


def render_dashboards():
    """Render pre-built dashboard views."""
    st.header("📈 Dashboards")
    
    db = get_db()
    
    tab1, tab2, tab3 = st.tabs(["Revenue", "Users", "Product Usage"])
    
    with tab1:
        st.subheader("Revenue Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            arr_result = db.query("SELECT SUM(arr) as arr FROM subscriptions WHERE status = 'active'")
            arr_value = arr_result.iloc[0, 0] or 0
            st.metric("Current ARR", format_metric(arr_value, prefix="$"))
        
        with col2:
            mrr_value = arr_value / 12 if arr_value else 0
            st.metric("Current MRR", format_metric(mrr_value, prefix="$"))
        
        with col3:
            active_subs = db.query("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'")
            st.metric("Active Subscriptions", format_metric(active_subs.iloc[0, 0]))
        
        with col4:
            avg_arr = db.query("SELECT AVG(arr) as avg FROM subscriptions WHERE status = 'active' AND arr > 0")
            avg_arr_value = avg_arr.iloc[0, 0] or 0
            st.metric("Avg ARR/Sub", format_metric(avg_arr_value, prefix="$"))
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            arr_trend = db.query("""
                SELECT 
                    DATE_TRUNC('month', start_date) as month,
                    SUM(arr) as new_arr
                FROM subscriptions
                GROUP BY 1
                ORDER BY 1
            """)
            fig = line_chart(arr_trend, "month", "new_arr", "New ARR Added by Month")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            arr_by_plan = db.query("""
                SELECT 
                    plan,
                    SUM(arr) as arr
                FROM subscriptions
                WHERE status = 'active'
                GROUP BY 1
                ORDER BY 2 DESC
            """)
            fig = bar_chart(arr_by_plan, "plan", "arr", "ARR by Plan")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("User Analytics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_users = db.query("SELECT COUNT(*) as count FROM users")
            st.metric("Total Users", format_metric(total_users.iloc[0, 0]))
        
        with col2:
            active_users = db.query("""
                SELECT COUNT(DISTINCT user_id) as count 
                FROM events 
                WHERE timestamp >= CURRENT_DATE - INTERVAL 30 DAY
            """)
            st.metric("Active Users (30d)", format_metric(active_users.iloc[0, 0]))
        
        with col3:
            churned = db.query("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'churned'")
            st.metric("Churned Subscriptions", format_metric(churned.iloc[0, 0]))
        
        with col4:
            churn_rate = db.query("""
                SELECT 
                    ROUND(100.0 * COUNT(CASE WHEN status = 'churned' THEN 1 END) / COUNT(*), 1) as rate
                FROM subscriptions
            """)
            st.metric("Overall Churn Rate", f"{churn_rate.iloc[0, 0]}%")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            signups = db.query("""
                SELECT 
                    DATE_TRUNC('month', signup_date) as month,
                    COUNT(*) as signups
                FROM users
                GROUP BY 1
                ORDER BY 1
            """)
            fig = line_chart(signups, "month", "signups", "User Signups Over Time")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            users_by_plan = db.query("""
                SELECT 
                    initial_plan as plan,
                    COUNT(*) as users
                FROM users
                GROUP BY 1
                ORDER BY 2 DESC
            """)
            fig = bar_chart(users_by_plan, "plan", "users", "Users by Initial Plan")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Product Usage")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_events = db.query("SELECT COUNT(*) as count FROM events")
            st.metric("Total Events", format_metric(total_events.iloc[0, 0]))
        
        with col2:
            dashboards = db.query("SELECT COUNT(*) as count FROM events WHERE event_type = 'dashboard_created'")
            st.metric("Dashboards Created", format_metric(dashboards.iloc[0, 0]))
        
        with col3:
            queries = db.query("SELECT COUNT(*) as count FROM events WHERE event_type = 'query_run'")
            st.metric("Queries Run", format_metric(queries.iloc[0, 0]))
        
        with col4:
            exports = db.query("SELECT COUNT(*) as count FROM events WHERE event_type = 'export_data'")
            st.metric("Data Exports", format_metric(exports.iloc[0, 0]))
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            events_by_type = db.query("""
                SELECT 
                    event_type,
                    COUNT(*) as count
                FROM events
                GROUP BY 1
                ORDER BY 2 DESC
            """)
            fig = bar_chart(events_by_type, "event_type", "count", "Events by Type")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            events_trend = db.query("""
                SELECT 
                    DATE_TRUNC('month', timestamp) as month,
                    COUNT(*) as events
                FROM events
                GROUP BY 1
                ORDER BY 1
            """)
            fig = line_chart(events_trend, "month", "events", "Events Over Time")
            st.plotly_chart(fig, use_container_width=True)


def render_explore():
    """Render data exploration interface."""
    st.header("🔍 Explore Data")
    
    db = get_db()
    
    tables = db.get_tables()
    selected_table = st.selectbox("Select a table", tables)
    
    if selected_table:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Schema")
            schema = db.get_schema(selected_table)
            st.dataframe(schema, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Sample Data")
            sample = db.get_sample(selected_table, limit=10)
            st.dataframe(sample, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Run Custom Query")
        
        default_query = f"SELECT * FROM {selected_table} LIMIT 100"
        query = st.text_area("SQL Query", value=default_query, height=100)
        
        if st.button("Run Query", type="primary"):
            try:
                result = db.query(query)
                st.success(f"Returned {len(result)} rows")
                st.dataframe(result, use_container_width=True)
                
                chart = auto_chart(result)
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
            except QueryError as e:
                st.error(f"Query failed: {e}")


def main():
    """Main application entry point."""
    try:
        db = get_db()
        db.get_tables()
    except FileNotFoundError:
        st.error("""
        ## Database not found
        
        The data hasn't been generated yet. Run:
        
        ```bash
        python data/generate_data.py
        ```
        
        Then refresh this page.
        """)
        return
    
    page = render_sidebar()
    
    if page == "💬 Ask Questions":
        render_ask_questions()
    elif page == "📈 Dashboards":
        render_dashboards()
    elif page == "🔍 Explore Data":
        render_explore()


if __name__ == "__main__":
    main()
