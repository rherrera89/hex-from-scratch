"""
Generate fake SaaS data for the analytics tool.

Creates realistic data for:
- users: Customer accounts
- plans: Subscription tiers
- subscriptions: User subscription history
- events: User activity events
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DATA_DIR = Path(__file__).parent
DB_PATH = DATA_DIR / "saas_data.duckdb"

PLANS = [
    {"id": 1, "name": "Free", "price_annual": 0, "features": "Basic analytics, 1 user, 1GB storage"},
    {"id": 2, "name": "Starter", "price_annual": 348, "features": "Advanced analytics, 5 users, 10GB storage"},  # $29/month equivalent
    {"id": 3, "name": "Pro", "price_annual": 1188, "features": "Full analytics, 25 users, 100GB storage, API access"},  # $99/month equivalent
    {"id": 4, "name": "Enterprise", "price_annual": 3588, "features": "Unlimited analytics, unlimited users, 1TB storage, API, SSO, dedicated support"},  # $299/month equivalent
]

EVENT_TYPES = [
    "page_view",
    "dashboard_created",
    "query_run",
    "chart_created",
    "export_data",
    "invite_user",
    "settings_changed",
    "login",
    "logout",
]

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2026, 2, 28)


def generate_users(n: int = 1000) -> list[dict]:
    """Generate fake user accounts with signup dates spread over time."""
    users = []
    for i in range(1, n + 1):
        days_since_start = random.randint(0, (END_DATE - START_DATE).days - 30)
        signup_date = START_DATE + timedelta(days=days_since_start)
        
        if random.random() < 0.6:
            initial_plan = "Free"
        elif random.random() < 0.7:
            initial_plan = "Starter"
        elif random.random() < 0.8:
            initial_plan = "Pro"
        else:
            initial_plan = "Enterprise"
        
        users.append({
            "id": i,
            "name": fake.name(),
            "email": fake.email(),
            "company": fake.company(),
            "signup_date": signup_date.strftime("%Y-%m-%d"),
            "initial_plan": initial_plan,
        })
    return users


def generate_subscriptions(users: list[dict]) -> list[dict]:
    """Generate subscription history for each user."""
    subscriptions = []
    sub_id = 1
    plan_arr = {p["name"]: p["price_annual"] for p in PLANS}
    
    for user in users:
        signup = datetime.strptime(user["signup_date"], "%Y-%m-%d")
        current_plan = user["initial_plan"]
        current_start = signup
        
        while current_start < END_DATE:
            duration_months = random.choices(
                [1, 3, 6, 12, 24],
                weights=[0.1, 0.2, 0.3, 0.3, 0.1]
            )[0]
            end_date = current_start + timedelta(days=duration_months * 30)
            
            if end_date > END_DATE:
                end_date = None
                status = "active"
            else:
                churn_prob = 0.3 if current_plan == "Free" else 0.15
                if random.random() < churn_prob:
                    status = "churned"
                else:
                    status = "upgraded" if random.random() < 0.4 else "renewed"
            
            arr = plan_arr[current_plan]
            subscriptions.append({
                "id": sub_id,
                "user_id": user["id"],
                "plan": current_plan,
                "arr": arr,
                "mrr": round(arr / 12, 2),  # MRR = ARR / 12
                "start_date": current_start.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
                "status": status,
            })
            sub_id += 1
            
            if status == "churned" or end_date is None:
                break
            elif status == "upgraded":
                plan_order = ["Free", "Starter", "Pro", "Enterprise"]
                current_idx = plan_order.index(current_plan)
                if current_idx < len(plan_order) - 1:
                    current_plan = plan_order[current_idx + 1]
            
            current_start = end_date
    
    return subscriptions


def generate_events(users: list[dict], n_events: int = 5000) -> list[dict]:
    """Generate user activity events."""
    events = []
    
    event_weights = {
        "page_view": 0.35,
        "login": 0.15,
        "query_run": 0.15,
        "dashboard_created": 0.08,
        "chart_created": 0.10,
        "export_data": 0.05,
        "invite_user": 0.02,
        "settings_changed": 0.03,
        "logout": 0.07,
    }
    
    for i in range(1, n_events + 1):
        user = random.choice(users)
        signup = datetime.strptime(user["signup_date"], "%Y-%m-%d")
        
        days_active = (END_DATE - signup).days
        if days_active <= 0:
            continue
            
        event_day = signup + timedelta(days=random.randint(0, days_active))
        event_time = event_day + timedelta(
            hours=random.randint(8, 20),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        event_type = random.choices(
            list(event_weights.keys()),
            weights=list(event_weights.values())
        )[0]
        
        properties = {}
        if event_type == "page_view":
            properties["page"] = random.choice(["/dashboard", "/queries", "/settings", "/reports", "/home"])
        elif event_type == "query_run":
            properties["duration_ms"] = random.randint(50, 5000)
            properties["rows_returned"] = random.randint(0, 10000)
        elif event_type == "dashboard_created":
            properties["chart_count"] = random.randint(1, 8)
        elif event_type == "export_data":
            properties["format"] = random.choice(["csv", "xlsx", "json"])
            properties["rows"] = random.randint(100, 50000)
        
        events.append({
            "id": i,
            "user_id": user["id"],
            "event_type": event_type,
            "timestamp": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "properties": str(properties) if properties else None,
        })
    
    return events


def create_database(users: list, plans: list, subscriptions: list, events: list):
    """Create DuckDB database and load all data."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    con = duckdb.connect(str(DB_PATH))
    
    con.execute("""
        CREATE TABLE plans (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            price_annual DECIMAL(10,2) NOT NULL,
            features VARCHAR
        )
    """)
    
    con.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            email VARCHAR NOT NULL,
            company VARCHAR,
            signup_date DATE NOT NULL,
            initial_plan VARCHAR NOT NULL
        )
    """)
    
    con.execute("""
        CREATE TABLE subscriptions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plan VARCHAR NOT NULL,
            arr DECIMAL(10,2) NOT NULL,
            mrr DECIMAL(10,2) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            status VARCHAR NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    con.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            event_type VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            properties VARCHAR,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    for plan in plans:
        con.execute(
            "INSERT INTO plans VALUES (?, ?, ?, ?)",
            [plan["id"], plan["name"], plan["price_annual"], plan["features"]]
        )
    
    for user in users:
        con.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
            [user["id"], user["name"], user["email"], user["company"], 
             user["signup_date"], user["initial_plan"]]
        )
    
    for sub in subscriptions:
        con.execute(
            "INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [sub["id"], sub["user_id"], sub["plan"], sub["arr"], sub["mrr"],
             sub["start_date"], sub["end_date"], sub["status"]]
        )
    
    for event in events:
        con.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            [event["id"], event["user_id"], event["event_type"],
             event["timestamp"], event["properties"]]
        )
    
    con.close()


def main():
    print("Generating fake SaaS data...")
    
    print("  Creating users...")
    users = generate_users(1000)
    print(f"    Generated {len(users)} users")
    
    print("  Creating subscriptions...")
    subscriptions = generate_subscriptions(users)
    print(f"    Generated {len(subscriptions)} subscriptions")
    
    print("  Creating events...")
    events = generate_events(users, 5000)
    print(f"    Generated {len(events)} events")
    
    print("  Loading into DuckDB...")
    create_database(users, PLANS, subscriptions, events)
    
    print(f"\nDone! Database created at: {DB_PATH}")
    
    con = duckdb.connect(str(DB_PATH))
    print("\nData summary:")
    for table in ["plans", "users", "subscriptions", "events"]:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count:,} rows")
    con.close()


if __name__ == "__main__":
    main()
