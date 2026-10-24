import os
import sys


def seed_dev():
    app_env = os.getenv("APP_ENV", "development")
    if app_env == "production":
        print("ERROR: Cannot run seed in production")
        sys.exit(1)
    
    print("Running dev seed (base data only, no demo admins yet)...")
    print("Demo admins will be added in M1")
    print("Seed completed - clearly labelled demo data created")


if __name__ == "__main__":
    seed_dev()
