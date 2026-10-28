import argparse

from dotenv import load_dotenv

from app import create_app
from app.extensions import db
from seed import seed_admin


load_dotenv()
app = create_app()


def main():
    parser = argparse.ArgumentParser(description="Northstar IT Asset Tracker")
    parser.add_argument(
        "--seed-db",
        action="store_true",
        help="Create schema and initial administrator",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    if args.seed_db:
        with app.app_context():
            db.create_all()
            admin = seed_admin()
            print(
                "Database initialized; administrator created for "
                f"{admin.email}."
            )
        return
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
