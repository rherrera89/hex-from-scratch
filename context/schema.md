# Database Schema

This document describes the tables in our SaaS analytics database.

## Tables

### plans
Subscription plan definitions. All plans are **annual contracts**.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR | Plan name (Free, Starter, Pro, Enterprise) |
| price_annual | DECIMAL(10,2) | Annual price in USD |
| features | VARCHAR | Comma-separated list of features |

### users
Customer accounts.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR | Full name |
| email | VARCHAR | Email address |
| company | VARCHAR | Company name |
| signup_date | DATE | When the user signed up |
| initial_plan | VARCHAR | The plan they first signed up for |

### subscriptions
Subscription history for each user. A user can have multiple subscriptions over time as they upgrade, renew, or churn. **All subscriptions are annual contracts.**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users.id |
| plan | VARCHAR | Plan name for this subscription period |
| arr | DECIMAL(10,2) | Annual Recurring Revenue - what the customer pays per year |
| mrr | DECIMAL(10,2) | Monthly Recurring Revenue = ARR / 12 |
| start_date | DATE | When this subscription started |
| end_date | DATE | When this subscription ended (NULL if active) |
| status | VARCHAR | Current status: 'active', 'churned', 'upgraded', 'renewed' |

### events
User activity events tracking product usage.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users.id |
| event_type | VARCHAR | Type of event (see list below) |
| timestamp | TIMESTAMP | When the event occurred |
| properties | VARCHAR | JSON string with event-specific data |

**Event types:**
- `page_view` - User viewed a page (properties: page)
- `login` - User logged in
- `logout` - User logged out
- `query_run` - User ran a query (properties: duration_ms, rows_returned)
- `dashboard_created` - User created a dashboard (properties: chart_count)
- `chart_created` - User created a chart
- `export_data` - User exported data (properties: format, rows)
- `invite_user` - User invited another user
- `settings_changed` - User changed settings

## Relationships

```
plans
  ↑
  │ (plan name referenced in subscriptions.plan)
  │
users ──────┬──────→ subscriptions
            │
            └──────→ events
```

## Sample Queries

### Get current MRR (derived from ARR)
```sql
SELECT SUM(arr) / 12 as total_mrr
FROM subscriptions
WHERE status = 'active'
```

### Get current ARR
```sql
SELECT SUM(arr) as total_arr
FROM subscriptions
WHERE status = 'active'
```

### Get user signups by month
```sql
SELECT 
    DATE_TRUNC('month', signup_date) as month,
    COUNT(*) as signups
FROM users
GROUP BY 1
ORDER BY 1
```

### Get churn rate by plan
```sql
SELECT 
    plan,
    COUNT(CASE WHEN status = 'churned' THEN 1 END) as churned,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN status = 'churned' THEN 1 END) / COUNT(*), 2) as churn_rate
FROM subscriptions
GROUP BY plan
ORDER BY churn_rate DESC
```
