# Database Migrations

This directory contains database migration files for the Honest Portfolio application.

## Current Status

The project uses SQLAlchemy but does not have Flask-Migrate installed. Migrations are currently managed manually.

## Migration Files

- `versions/001_add_sales_tables.py` - Adds sales and purchase_sale_assignments tables for stock sales tracking with FIFO cost basis

## Applying Migrations

Since Flask-Migrate is not installed, you have two options:

### Option 1: Use db.create_all() (Recommended for development)

The application uses `db.create_all()` in the app factory which will automatically create any new tables defined in models.py:

```bash
python run.py
```

### Option 2: Install Flask-Migrate and use Alembic

```bash
# Install Flask-Migrate
pip install Flask-Migrate

# Initialize migrations (if needed)
flask db init

# Create a migration
flask db migrate -m "Add sales tables"

# Apply migrations
flask db upgrade
```

### Option 3: Manual SQL Execution

You can manually apply the SQL from the migration files if needed:

```bash
sqlite3 instance/portfolio.db < migrations/versions/001_add_sales_tables.sql
```

## Migration Structure

Each migration file contains:
- `upgrade()` - Function to apply the migration
- `downgrade()` - Function to revert the migration
- Revision metadata for tracking

## Notes

- The migration files follow Alembic format for future Flask-Migrate compatibility
- All foreign keys have proper cascade behavior defined in models.py
- Indexes are created for performance on frequently queried columns
