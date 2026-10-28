import os

from dotenv import load_dotenv

from app import create_app
from app.extensions import db
from app.models import User


def seed_admin():
    email = os.getenv("SEED_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("SEED_ADMIN_PASSWORD", "")
    if not email or len(password) < 12:
        raise RuntimeError(
            "Set SEED_ADMIN_EMAIL and a SEED_ADMIN_PASSWORD of at least 12 characters."
        )
    existing = User.query.filter_by(email=email).first()
    if existing:
        raise RuntimeError("The configured seed administrator already exists.")
    admin = User(email=email, role="Admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return admin


def main():
    load_dotenv()
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = seed_admin()
        print(f"Database initialized; administrator created for {admin.email}.")


if __name__ == "__main__":
    main()
