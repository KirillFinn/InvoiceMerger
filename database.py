import sqlite3
import pandas as pd
from datetime import datetime

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect('invoices.db')
    cursor = conn.cursor()
    
    # Create invoices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evse_id TEXT,
        session_id TEXT,
        currency TEXT,
        price REAL,
        file_name TEXT,
        processed_date TIMESTAMP,
        UNIQUE(session_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_invoice_data(df, file_name):
    """Save invoice data to the database."""
    conn = sqlite3.connect('invoices.db')
    
    # Add file name and processed date to the dataframe
    df['file_name'] = file_name
    df['processed_date'] = datetime.now()
    
    # Save to database
    # df.to_sql('invoices', conn, if_exists='append', index=False) # Old method

    cursor = conn.cursor()
    inserted_count = 0
    skipped_count = 0

    # Prepare column names and placeholders
    # Ensure columns in DataFrame match the table structure or are handled appropriately
    # For this table, columns are: id (auto), evse_id, session_id, currency, price, file_name, processed_date
    
    # Filter DataFrame columns to only include those that exist in the 'invoices' table
    # and are not the auto-incrementing 'id'
    table_columns = ['evse_id', 'session_id', 'currency', 'price', 'file_name', 'processed_date']
    df_filtered = df[[col for col in table_columns if col in df.columns]]

    cols_str = ', '.join(df_filtered.columns)
    placeholders_str = ', '.join(['?'] * len(df_filtered.columns))
    sql = f"INSERT INTO invoices ({cols_str}) VALUES ({placeholders_str})"

    for _, row in df_filtered.iterrows():
        try:
            cursor.execute(sql, tuple(row))
            inserted_count += 1
        except sqlite3.IntegrityError:  # Specifically for UNIQUE constraint failed
            skipped_count += 1
        except sqlite3.Error as e: # Catch other potential SQLite errors during insert
            # For now, we'll count these as skipped too, or log them differently
            # print(f"SQLite error during insert: {e} for row: {row}") # Optional: for debugging
            skipped_count += 1 # Or handle more granularly

    conn.commit()
    conn.close()
    return inserted_count, skipped_count

def get_all_invoices():
    """Retrieve all invoices from the database."""
    conn = sqlite3.connect('invoices.db')
    query = "SELECT * FROM invoices"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_invoices_by_date_range(start_date, end_date):
    """Retrieve invoices within a date range."""
    conn = sqlite3.connect('invoices.db')
    query = "SELECT * FROM invoices WHERE processed_date BETWEEN ? AND ?"
    df = pd.read_sql_query(query, conn, params=[start_date, end_date])
    conn.close()
    return df

def get_invoices_by_evse(evse_id):
    """Retrieve invoices for a specific EVSE ID."""
    conn = sqlite3.connect('invoices.db')
    query = "SELECT * FROM invoices WHERE evse_id = ?"
    df = pd.read_sql_query(query, conn, params=[evse_id])
    conn.close()
    return df 