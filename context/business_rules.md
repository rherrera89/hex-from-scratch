# Business Rules and Definitions

This document explains the key metrics and business logic for our SaaS analytics.

## Key Metrics

### ARR (Annual Recurring Revenue)
The total annual contract value from active subscriptions. This is the PRIMARY revenue metric since all plans are annual contracts.

- **Current ARR**: `SUM(arr) FROM subscriptions WHERE status = 'active'`
- **ARR for a specific month**: Sum arr for subscriptions that overlapped with that month
- The `arr` column stores what the customer pays per year

### MRR (Monthly Recurring Revenue)
MRR is DERIVED from ARR. It represents the monthly equivalent of annual revenue.

- **Formula**: `MRR = ARR / 12`
- **Current MRR**: `SUM(arr) / 12 FROM subscriptions WHERE status = 'active'`
- The `mrr` column is pre-calculated as arr/12 for convenience, but you can also calculate it

**CRITICAL: MRR is time-sensitive.** A subscription contributes to MRR only during months it was active:
- **MRR for a specific month**: Sum (arr/12) for subscriptions where `start_date <= end_of_month AND (end_date >= start_of_month OR end_date IS NULL)`

**Common mistake**: Grouping by start_date shows "new MRR added" not "total MRR". Total MRR requires checking date overlaps.

### Churn
When a customer cancels their subscription and does not renew.

- **Identification**: `subscriptions.status = 'churned'`
- **Churn Rate**: `(churned subscriptions / total subscriptions) * 100`

### Active User
A user who has performed at least one event in the last 30 days.

- **Calculation**: Users with events where `timestamp >= CURRENT_DATE - INTERVAL 30 DAY`

### Cohort
A group of users who signed up in the same time period (usually month).

- **Grouping**: `DATE_TRUNC('month', users.signup_date)`
- **Usage**: Cohort analysis for retention and revenue trends

## Subscription Statuses

| Status | Meaning |
|--------|---------|
| `active` | Currently paying, subscription ongoing |
| `churned` | Cancelled and did not renew |
| `upgraded` | Moved to a higher-tier plan |
| `renewed` | Renewed at the same plan level |

## Plan Hierarchy

From lowest to highest tier:
1. **Free** - $0/month
2. **Starter** - $29/month
3. **Pro** - $99/month
4. **Enterprise** - $299/month

## Common Analysis Patterns

### Revenue Analysis
- MRR trend over time
- MRR by plan type
- Revenue per user (MRR / active users)

### User Analysis
- Signups over time
- Users by plan
- Active vs. inactive users
- Cohort retention

### Churn Analysis
- Churn rate by plan
- Time to churn (days from signup to churn)
- Churn by signup cohort

### Product Usage
- Most common events
- Events per user
- Feature adoption (dashboard_created, chart_created, etc.)

## Date Conventions

- All dates are in UTC
- Date ranges are inclusive on both ends
- "Current month" means the calendar month containing today
- "Last 30 days" means the rolling 30-day period ending today

## Data Quality Notes

- Some users have multiple subscription records (history of upgrades/renewals)
- The `mrr` field on subscriptions reflects the plan price at that time
- Event `properties` is a JSON string and may be NULL
- Enterprise subscriptions may have custom pricing (stored in mrr)
