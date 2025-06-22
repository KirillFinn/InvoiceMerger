import streamlit as st
import pandas as pd
import sqlite3 # Added for specific exception handling
from database import init_db, get_all_invoices, save_invoice_data
from datetime import datetime, timedelta
from utils import process_file

# Initialize database
init_db()

st.set_page_config(
    page_title="Invoice Combiner",
    page_icon="📊",
    layout="centered"
)

st.title("Invoice File Combiner")
st.markdown("""
This application helps you combine multiple CSV and Excel invoice files with different column structures 
into a single standardized output file. It automatically detects the relevant columns:
- EVSE ID (Electric Vehicle Supply Equipment identifier)
- Session ID (the unique transaction identifier for charging sessions)
- Currency
- Price (net price, distinguishing it from VAT rates)
""")

# File uploader for multiple CSV and Excel files
uploaded_files = st.file_uploader(
    "Upload your invoice files (CSV, XLSX, XLS)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# Initialize session state for combined data if not already initialized
if 'combined_data' not in st.session_state:
    st.session_state.combined_data = None
    
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = 0
    
if 'processing_errors' not in st.session_state:
    st.session_state.processing_errors = []

# Add database query section
st.sidebar.title("Database Queries")
if st.sidebar.button("Show All Records"):
    try:
        df = get_all_invoices()
        st.sidebar.dataframe(df)
    except Exception as e:
        st.sidebar.error(f"Error accessing database: {str(e)}")

# Process files when uploaded
if uploaded_files:
    if st.button("Process Files"):
        st.session_state.combined_data = pd.DataFrame()
        st.session_state.processed_files = 0
        st.session_state.processing_errors = []
        
        # Progress bar for processing
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process each file
        for i, file in enumerate(uploaded_files):
            status_text.text(f"Processing file {i+1}/{len(uploaded_files)}: {file.name}")
            
            try:
                # Read the file
                file_content = file.read()
                
                # Process the file content
                processed_df = process_file(file_content, file.name)
                
                # Save to database
                inserted_count, skipped_count = save_invoice_data(processed_df, file.name)
                
                # Append to combined data (shows what was attempted from the file)
                if st.session_state.combined_data is None or st.session_state.combined_data.empty:
                    st.session_state.combined_data = processed_df
                else:
                    st.session_state.combined_data = pd.concat([st.session_state.combined_data, processed_df], ignore_index=True)
                
                if inserted_count > 0:
                    st.session_state.processed_files += 1
                
                if skipped_count > 0:
                    # Using st.session_state.processing_errors for warnings as well, or create a new list
                    st.session_state.processing_errors.append(
                        (f"File '{file.name}': {skipped_count} records were skipped due to being duplicates. "
                         f"{inserted_count} new records were added.", "warning")
                    )
                elif inserted_count == 0 and not processed_df.empty: # No new records added, but file wasn't empty (implies all were duplicates)
                    st.session_state.processing_errors.append(
                        (f"File '{file.name}': All records were found to be duplicates. No new records added.", "info")
                    )

            except sqlite3.Error as db_err: # Catch other potential DB errors not caught in save_invoice_data's loop
                st.session_state.processing_errors.append((f"Database error processing {file.name}: {str(db_err)}", "error"))
            except ValueError as val_err: # Errors from utils.process_file (e.g. empty file, columns not found)
                 st.session_state.processing_errors.append((f"Validation error processing {file.name}: {str(val_err)}", "error"))
            except Exception as e: # Other unexpected errors
                st.session_state.processing_errors.append((f"Unexpected error processing {file.name}: {str(e)}", "error"))
            
            # Update progress
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        # Complete the progress
        progress_bar.progress(100)
        status_text.text("Processing complete!")
    
    # Display processing results
    if st.session_state.processed_files > 0:
        st.success(f"Successfully processed {st.session_state.processed_files} files.")
        
        # Display combined data
        if st.session_state.combined_data is not None and not st.session_state.combined_data.empty:
            st.subheader("Combined Invoice Data")
            st.dataframe(st.session_state.combined_data)
            
            # Provide download option for the combined file
            csv = st.session_state.combined_data.to_csv(index=False)
            st.download_button(
                label="Download Combined CSV",
                data=csv,
                file_name="combined_invoices.csv",
                mime="text/csv"
            )
    
    # Display errors if any
    if st.session_state.processing_errors:
        st.subheader("Processing Notifications")
        for msg, level in st.session_state.processing_errors:
            if level == "error":
                st.error(msg)
            elif level == "warning":
                st.warning(msg)
            elif level == "info":
                st.info(msg)
            else: # Default to info
                st.info(msg)


else:
    st.info("Please upload one or more invoice files (CSV, XLSX, or XLS) to begin.")
