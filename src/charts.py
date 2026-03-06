"""
Chart generation utilities using Plotly.

Automatically creates appropriate visualizations based on data shape.
"""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def auto_chart(df: pd.DataFrame, title: Optional[str] = None) -> Optional[go.Figure]:
    """
    Automatically create an appropriate chart based on the DataFrame structure.
    
    Heuristics:
    - Single value: Display as metric (no chart)
    - Date + numeric: Line chart
    - Category + numeric: Bar chart
    - Two numerics: Scatter plot
    - Multiple numerics: Table only (no chart)
    """
    if df.empty or len(df.columns) < 2:
        return None
    
    date_cols = df.select_dtypes(include=["datetime64", "object"]).columns.tolist()
    date_cols = [c for c in date_cols if _is_date_like(df[c])]
    
    numeric_cols = df.select_dtypes(include=["int64", "float64", "int32", "float32"]).columns.tolist()
    
    categorical_cols = [c for c in df.columns if c not in date_cols and c not in numeric_cols]
    
    if len(df) == 1 and len(numeric_cols) == 1:
        return None
    
    if date_cols and numeric_cols:
        fig = px.line(
            df, 
            x=date_cols[0], 
            y=numeric_cols[0],
            title=title,
            markers=True
        )
        fig.update_layout(
            xaxis_title=_format_column_name(date_cols[0]),
            yaxis_title=_format_column_name(numeric_cols[0])
        )
        return fig
    
    if categorical_cols and numeric_cols:
        if len(df) <= 20:
            fig = px.bar(
                df,
                x=categorical_cols[0],
                y=numeric_cols[0],
                title=title
            )
        else:
            fig = px.bar(
                df.head(20),
                x=categorical_cols[0],
                y=numeric_cols[0],
                title=f"{title} (top 20)" if title else "Top 20"
            )
        fig.update_layout(
            xaxis_title=_format_column_name(categorical_cols[0]),
            yaxis_title=_format_column_name(numeric_cols[0])
        )
        return fig
    
    if len(numeric_cols) >= 2:
        fig = px.scatter(
            df,
            x=numeric_cols[0],
            y=numeric_cols[1],
            title=title
        )
        fig.update_layout(
            xaxis_title=_format_column_name(numeric_cols[0]),
            yaxis_title=_format_column_name(numeric_cols[1])
        )
        return fig
    
    return None


def line_chart(df: pd.DataFrame, x: str, y: str, title: Optional[str] = None) -> go.Figure:
    """Create a line chart."""
    fig = px.line(df, x=x, y=y, title=title, markers=True)
    fig.update_layout(
        xaxis_title=_format_column_name(x),
        yaxis_title=_format_column_name(y)
    )
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: Optional[str] = None) -> go.Figure:
    """Create a bar chart."""
    fig = px.bar(df, x=x, y=y, title=title)
    fig.update_layout(
        xaxis_title=_format_column_name(x),
        yaxis_title=_format_column_name(y)
    )
    return fig


def pie_chart(df: pd.DataFrame, names: str, values: str, title: Optional[str] = None) -> go.Figure:
    """Create a pie chart."""
    fig = px.pie(df, names=names, values=values, title=title)
    return fig


def area_chart(df: pd.DataFrame, x: str, y: str, title: Optional[str] = None) -> go.Figure:
    """Create an area chart."""
    fig = px.area(df, x=x, y=y, title=title)
    fig.update_layout(
        xaxis_title=_format_column_name(x),
        yaxis_title=_format_column_name(y)
    )
    return fig


def _is_date_like(series: pd.Series) -> bool:
    """Check if a series looks like dates."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    
    if series.dtype == object:
        sample = series.dropna().head(5)
        if len(sample) == 0:
            return False
        
        try:
            pd.to_datetime(sample)
            return True
        except (ValueError, TypeError):
            return False
    
    return False


def _format_column_name(name: str) -> str:
    """Format a column name for display."""
    return name.replace("_", " ").title()


def format_metric(value: float, prefix: str = "", suffix: str = "") -> str:
    """Format a numeric value for display as a metric."""
    if abs(value) >= 1_000_000:
        formatted = f"{value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        formatted = f"{value / 1_000:.1f}K"
    else:
        formatted = f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
    
    return f"{prefix}{formatted}{suffix}"
