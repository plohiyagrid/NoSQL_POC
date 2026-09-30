#!/usr/bin/env python3
"""Demo CLI for the User Activity Log System."""

import argparse
import json
from datetime import datetime, timedelta
from uuid import UUID

from app.models import ActivityType
from app.repository import ActivityLogRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="User Activity Log System (Cassandra)")
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Create keyspace and table from schema/schema.cql",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a full demo: insert sample logs and query them",
    )
    parser.add_argument("--user-id", type=UUID, help="User UUID for queries")
    parser.add_argument(
        "--insert",
        nargs=2,
        metavar=("USER_ID", "ACTIVITY_TYPE"),
        help="Insert one activity log",
    )
    parser.add_argument(
        "--recent",
        type=int,
        metavar="LIMIT",
        help="Get recent activities for --user-id",
    )
    parser.add_argument(
        "--range-hours",
        type=int,
        metavar="HOURS",
        help="Get activities in the last N hours for --user-id",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Get all activities for --user-id",
    )
    return parser.parse_args()


def print_logs(logs: list) -> None:
    if not logs:
        print("No activities found.")
        return
    for log in logs:
        print(json.dumps(log.to_dict(), indent=2))


def run_demo(repo: ActivityLogRepository) -> UUID:
    user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    now = datetime.utcnow()

    print(f"\n=== Inserting sample activities for user {user_id} ===\n")

    samples = [
        (ActivityType.LOGIN.value, now - timedelta(days=5), "User logged in from web"),
        (ActivityType.PAGE_VIEW.value, now - timedelta(days=2), "Viewed /dashboard"),
        (ActivityType.SEARCH.value, now - timedelta(hours=6), 'Searched for "cassandra"'),
        (ActivityType.PAGE_VIEW.value, now - timedelta(hours=1), "Viewed /settings"),
        (ActivityType.LOGOUT.value, now - timedelta(minutes=10), "User logged out"),
    ]

    for activity_type, ts, details in samples:
        log = repo.insert_activity(user_id, activity_type, timestamp=ts, details=details)
        print(f"  Inserted: {log.activity_type} at {log.timestamp.isoformat()}")

    print("\n=== Recent activities (limit 3) ===\n")
    print_logs(repo.get_recent_activities(user_id, limit=3))

    print("\n=== Activities in last 3 days ===\n")
    start = now - timedelta(days=3)
    print_logs(repo.get_activities_in_range(user_id, start, now))

    print("\n=== All activities ===\n")
    print_logs(repo.get_all_activities(user_id))

    return user_id


def main() -> None:
    args = parse_args()

    repo = ActivityLogRepository()
    try:
        if args.init_schema:
            print("Applying schema...")
            repo.apply_schema()
            print("Schema applied successfully.")
        else:
            repo.connect()

        if args.demo:
            run_demo(repo)

        if args.insert:
            user_id = UUID(args.insert[0])
            activity_type = args.insert[1]
            log = repo.insert_activity(user_id, activity_type)
            print("Inserted:")
            print(json.dumps(log.to_dict(), indent=2))

        if args.user_id and args.recent is not None:
            print(f"\nRecent {args.recent} activities for {args.user_id}:\n")
            print_logs(repo.get_recent_activities(args.user_id, limit=args.recent))

        if args.user_id and args.range_hours is not None:
            end = datetime.utcnow()
            start = end - timedelta(hours=args.range_hours)
            print(f"\nActivities in last {args.range_hours}h for {args.user_id}:\n")
            print_logs(repo.get_activities_in_range(args.user_id, start, end))

        if args.user_id and args.all:
            print(f"\nAll activities for {args.user_id}:\n")
            print_logs(repo.get_all_activities(args.user_id))

        if not any(
            [
                args.init_schema,
                args.demo,
                args.insert,
                args.recent is not None,
                args.range_hours is not None,
                args.all,
            ]
        ):
            print("No action specified. Try --demo or --help")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
