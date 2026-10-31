"""
Quick utility to update the 2 message timestamps in MongoDB.
Run:
    python -m data_layer.tests.fix_timestamps
"""
from data_layer.mongo import get_db

def main():
    db = get_db()
    r1 = db.incident_messages.update_one(
        {"message_id": "MSG-0001"},
        {"$set": {"timestamp": "2026-10-28T13:55:00Z"}}
    )
    r2 = db.incident_messages.update_one(
        {"message_id": "MSG-0002"},
        {"$set": {"timestamp": "2026-10-28T13:56:00Z"}}
    )
    print(f"Updated MSG-0001 (modified={r1.modified_count}) and MSG-0002 (modified={r2.modified_count})")
    print("Timestamps updated successfully.")

if __name__ == "__main__":
    main()

