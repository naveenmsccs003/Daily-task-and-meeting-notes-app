"""Initialize the database: create tables/indexes and an initial admin user.

Usage:
    python init_db.py

Safe to re-run: it never drops existing tables or data. If a user with
username 'admin' does not already exist, one is created so you can log in
immediately. Change the password after first login in a real deployment.
"""
import database
from app import create_app
from models import User

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def main():
    app = create_app()
    with app.app_context():
        database.init_db(app)
        print(f"Database ready at: {app.config['DATABASE_PATH']}")

        existing = User.get_by_username(DEFAULT_USERNAME)
        if existing:
            print(f"User '{DEFAULT_USERNAME}' already exists. Skipping user creation.")
            return

        print(f"No admin user found. Creating default user '{DEFAULT_USERNAME}'.")
        User.create(
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD,
            full_name="Administrator",
            email="",
        )
        print(f"Created user '{DEFAULT_USERNAME}' with password '{DEFAULT_PASSWORD}'.")
        print("IMPORTANT: change this password after your first login.")


if __name__ == "__main__":
    main()
