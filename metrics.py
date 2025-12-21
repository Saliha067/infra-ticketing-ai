"""Generate metrics and reports from inquiry data."""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter
from dotenv import load_dotenv
from sqlalchemy import func, and_, extract

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db.models import get_db_engine, get_session_maker, Inquiry

load_dotenv()


def get_db_session():
    """Get database session."""
    db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    engine = get_db_engine(db_url)
    SessionMaker = get_session_maker(engine)
    return SessionMaker()


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def get_daily_metrics(session):
    """Get today's inquiry metrics."""
    today = datetime.now(timezone.utc).date()
    
    inquiries = session.query(Inquiry).filter(
        func.date(Inquiry.created_at) == today
    ).all()
    
    print_section("📊 TODAY'S METRICS")
    print(f"Total Inquiries: {len(inquiries)}")
    
    resolved_from_kb = len([i for i in inquiries if i.resolved_from_kb])
    needs_ticket = len([i for i in inquiries if not i.resolved_from_kb])
    
    print(f"  ✅ Resolved from KB: {resolved_from_kb}")
    print(f"  🎫 Needs Team Action: {needs_ticket}")
    
    if inquiries:
        teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
        print("\n  Team Distribution:")
        for team, count in teams.most_common():
            print(f"    • {team}: {count}")
        
        categories = Counter([i.category for i in inquiries if i.category])
        print("\n  Category Breakdown:")
        for category, count in categories.most_common():
            print(f"    • {category}: {count}")
        
        urgencies = Counter([i.urgency for i in inquiries if i.urgency])
        print("\n  Urgency Levels:")
        for urgency, count in urgencies.most_common():
            print(f"    • {urgency}: {count}")


def get_weekly_metrics(session):
    """Get this week's inquiry metrics."""
    today = datetime.now(timezone.utc)
    week_start = today - timedelta(days=today.weekday())
    
    inquiries = session.query(Inquiry).filter(
        Inquiry.created_at >= week_start
    ).all()
    
    print_section("📈 THIS WEEK'S METRICS")
    print(f"Total Inquiries: {len(inquiries)}")
    
    resolved_from_kb = len([i for i in inquiries if i.resolved_from_kb])
    needs_ticket = len([i for i in inquiries if not i.resolved_from_kb])
    
    print(f"  ✅ Resolved from KB: {resolved_from_kb} ({resolved_from_kb/len(inquiries)*100:.1f}%)" if inquiries else "  ✅ Resolved from KB: 0")
    print(f"  🎫 Needs Team Action: {needs_ticket} ({needs_ticket/len(inquiries)*100:.1f}%)" if inquiries else "  🎫 Needs Team Action: 0")
    
    if inquiries:
        # Daily breakdown
        daily_counts = Counter([i.created_at.date() for i in inquiries])
        print("\n  Daily Breakdown:")
        for date in sorted(daily_counts.keys()):
            print(f"    {date.strftime('%a, %b %d')}: {daily_counts[date]}")
        
        # Top teams
        teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
        print("\n  Top Teams:")
        for team, count in teams.most_common(5):
            print(f"    • {team}: {count}")


def get_monthly_metrics(session):
    """Get this month's inquiry metrics."""
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    inquiries = session.query(Inquiry).filter(
        Inquiry.created_at >= month_start
    ).all()
    
    print_section("📅 THIS MONTH'S METRICS")
    print(f"Total Inquiries: {len(inquiries)}")
    
    resolved_from_kb = len([i for i in inquiries if i.resolved_from_kb])
    needs_ticket = len([i for i in inquiries if not i.resolved_from_kb])
    
    kb_rate = (resolved_from_kb/len(inquiries)*100) if inquiries else 0
    
    print(f"  ✅ Resolved from KB: {resolved_from_kb} ({kb_rate:.1f}%)")
    print(f"  🎫 Needs Team Action: {needs_ticket}")
    print(f"\n  📊 KB Hit Rate: {kb_rate:.1f}%")
    
    if inquiries:
        # Weekly breakdown
        weekly_counts = {}
        for inquiry in inquiries:
            week = inquiry.created_at.isocalendar()[1]
            weekly_counts[week] = weekly_counts.get(week, 0) + 1
        
        print("\n  Weekly Breakdown:")
        for week in sorted(weekly_counts.keys()):
            print(f"    Week {week}: {weekly_counts[week]}")
        
        # Team distribution
        teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
        print("\n  Team Distribution:")
        for team, count in teams.most_common():
            pct = (count/len(inquiries)*100)
            print(f"    • {team}: {count} ({pct:.1f}%)")
        
        # Top categories
        categories = Counter([i.category for i in inquiries if i.category])
        print("\n  Top Categories:")
        for category, count in categories.most_common(5):
            print(f"    • {category}: {count}")
        
        # Status breakdown
        statuses = Counter([i.status for i in inquiries])
        print("\n  Status Distribution:")
        for status, count in statuses.most_common():
            print(f"    • {status}: {count}")


def get_all_time_metrics(session):
    """Get all-time inquiry metrics."""
    inquiries = session.query(Inquiry).all()
    
    print_section("🏆 ALL-TIME METRICS")
    print(f"Total Inquiries: {len(inquiries)}")
    
    if not inquiries:
        print("  No data yet!")
        return
    
    resolved_from_kb = len([i for i in inquiries if i.resolved_from_kb])
    needs_ticket = len([i for i in inquiries if not i.resolved_from_kb])
    kb_rate = (resolved_from_kb/len(inquiries)*100)
    
    print(f"  ✅ Resolved from KB: {resolved_from_kb} ({kb_rate:.1f}%)")
    print(f"  🎫 Created Tickets: {needs_ticket}")
    
    # First and last inquiry
    first = min(inquiries, key=lambda i: i.created_at)
    last = max(inquiries, key=lambda i: i.created_at)
    print(f"\n  First Inquiry: {first.created_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Latest Inquiry: {last.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    # Most active users
    users = Counter([i.slack_user_id for i in inquiries])
    print("\n  Most Active Users:")
    for user, count in users.most_common(5):
        print(f"    • {user}: {count} inquiries")
    
    # Team workload
    teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
    print("\n  Team Workload (All Time):")
    for team, count in teams.most_common():
        pct = (count/len(inquiries)*100)
        print(f"    • {team}: {count} ({pct:.1f}%)")


def get_recent_inquiries(session, limit=10):
    """Get most recent inquiries."""
    inquiries = session.query(Inquiry).order_by(
        Inquiry.created_at.desc()
    ).limit(limit).all()
    
    print_section(f"🕒 RECENT {limit} INQUIRIES")
    
    if not inquiries:
        print("  No inquiries yet!")
        return
    
    for i, inquiry in enumerate(inquiries, 1):
        status_icon = "✅" if inquiry.resolved_from_kb else "🎫"
        print(f"\n  {i}. {status_icon} {inquiry.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"     Question: {inquiry.question[:80]}...")
        print(f"     Team: {inquiry.assigned_team or 'N/A'} | Category: {inquiry.category or 'N/A'}")
        print(f"     Environment: {inquiry.environment or 'N/A'} | Status: {inquiry.status}")


def main():
    """Generate all metrics reports."""
    print("\n" + "=" * 70)
    print("  🤖 INFRASTRUCTURE INQUIRY BOT - METRICS DASHBOARD")
    print("=" * 70)
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    session = get_db_session()
    
    try:
        get_daily_metrics(session)
        get_weekly_metrics(session)
        get_monthly_metrics(session)
        get_all_time_metrics(session)
        get_recent_inquiries(session, limit=10)
        
        print("\n" + "=" * 70)
        print("  ✅ Report Complete!")
        print("=" * 70 + "\n")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()
