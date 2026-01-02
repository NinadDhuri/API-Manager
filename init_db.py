from db import init_db_schema, add_partner

def main():
    print("Initializing database...")
    init_db_schema()

    print("Seeding data...")
    add_partner("Partner A", "key_a", rate_limit=10) # 10 req/min
    add_partner("Partner B", "key_b", rate_limit=5)  # 5 req/min
    add_partner("Unlimited Power", "god_mode", rate_limit=1000)

    print("Database initialized.")

if __name__ == "__main__":
    main()
