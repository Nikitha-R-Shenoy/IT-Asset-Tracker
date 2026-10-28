# Northstar IT Asset Tracker (ITAMS)

A server-rendered IT asset management application built with Python 3.11+, Flask 3, Flask-SQLAlchemy, MySQL 8, Flask-WTF, Bootstrap 5 and pytest. It supports role-based inventory management, custody history, condition-audited returns, maintenance, employee repair requests, straight-line depreciation, reports and an append-only audit ledger.

## Features

- **Roles:** Admin, IT Manager, and Employee. Employee records include a department cost center. Authorization is enforced on server routes, not only in the UI.
- **Inventory:** Unique asset tags and serial numbers; search, status filtering, pagination, CSV import with all-or-nothing validation, asset detail/history, and soft retirement.
- **Custody:** Atomic check-out and check-in with return condition and audit records. Good returns become Available; damaged/defective returns become In Repair.
- **Maintenance and requests:** Maintenance costs/vendors/completion, status synchronization, employee repair requests for their currently assigned assets, and request tracking.
- **Finance and reporting:** Straight-line depreciation, inventory status, warranties expiring within 30 days, repair-cost aggregates, CSV export.
- **Security:** PBKDF2-SHA256 password hashes (600,000 iterations), HTTP-only/SameSite session cookies, Flask-WTF CSRF protection, parameterized ORM access, and generic error pages.

## Requirements

- Python 3.11 or newer
- MySQL Server 8.0 with InnoDB

## Local setup (Windows PowerShell)

1. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Create a MySQL database and a dedicated least-privilege application account. Update the account/database names to match the local MySQL setup. Run the provided database creation SQL as an administrator:

   ```powershell
   Get-Content .\setup_db.sql | mysql -u root -p
   ```

   Create a unique application-user password locally and grant that account privileges on `it_asset_tracker_db.*`. Do not put database credentials in source control.

4. Configure environment variables by copying `.env.example` to `.env` and replacing the placeholders with local values:

   ```powershell
   Copy-Item .env.example .env
   ```

   `DATABASE_URL` must be a SQLAlchemy URL such as `mysql+pymysql://USER:PASSWORD@localhost:3306/it_asset_tracker_db?charset=utf8mb4`. Set a long, random `SECRET_KEY`. `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` are needed for the initial administrator; choose a unique password of at least 12 characters. The seed command refuses to overwrite an existing account.

5. Create tables and the initial administrator:

   ```powershell
   python run.py --seed-db
   ```

6. Start the development server and open http://127.0.0.1:5000:

   ```powershell
   python run.py
   ```

   Use a production WSGI server and HTTPS in deployment. Set `SESSION_COOKIE_SECURE=true` when serving exclusively over HTTPS.

Alternatively, run the schema/administrator setup with `python seed.py` after configuring `.env`. To create only the tables after initial setup, use `python -m flask --app run.py init-db`.

## CSV asset import

The inventory page accepts UTF-8 CSV files with a header row. Required headers:

```text
asset_tag,serial_number,category,manufacturer,model,purchase_date,purchase_cost,salvage_value,useful_life_years
```

Optional headers are `vendor`, `warranty_expiry`, and `notes`. Dates use `YYYY-MM-DD`; import rejects invalid rows, repeated tag/serial values, and any conflict with existing inventory. A failed file makes no changes. The maximum upload size is 2 MB.

## Roles

| Action | Admin | IT Manager | Employee |
|---|---:|---:|---:|
| Executive dashboard / inventory browsing / reports | Yes | Yes | Own equipment only |
| Register assets | Yes | Yes | No |
| Edit/import assets, assign, return, maintenance | No | Yes | No |
| Retire assets | Yes | Yes | No |
| Employee registry management | Yes | Yes | No |
| Submit repair requests | No | No | Yes |
| Update service requests | No | Yes | No |
| Inspect audit ledger | Yes | No | No |

Seed only the first administrator. Admins can provision IT Manager accounts through the employee registry; Admins and IT Managers can create employee portal accounts. When setting an initial password, provide it to the employee securely.

## Database notes

Tables are created by `flask init-db` or `python run.py --seed-db`; there are no destructive or implicit schema migrations. Before schema changes in an existing deployment, back up the database and use a migration plan. Audit records are retained and rejected by ORM-level update/delete operations.

## Tests and static checks

The test suite uses an isolated in-memory SQLite database and does not require MySQL:

```powershell
pytest -v
flake8 app tests run.py seed.py config.py
```

Coverage includes depreciation boundaries, lifecycle rules, login, route authorization, duplicate asset validation, and assignment/audit behavior. MySQL-specific deployment behavior should also be smoke-tested against the target MySQL 8 instance before production.
