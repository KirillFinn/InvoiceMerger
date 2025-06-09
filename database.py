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
    df.to_sql('invoices', conn, if_exists='append', index=False)
    
    conn.close()

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