import streamlit as st
import pandas as pd
import io
import re
from utils import detect_columns, standardize_dataframe, process_file

# Set page configuration
st.set_page_config(
    page_title="Invoice Combiner",
    page_icon="📊",
    layout="centered"
)

# Application title and description
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

# Process files when uploaded
if uploaded_files:
    # Reset processing state when new files are uploaded
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
                
                # Append to combined data
                if st.session_state.combined_data is None or st.session_state.combined_data.empty:
                    st.session_state.combined_data = processed_df
                else:
                    st.session_state.combined_data = pd.concat([st.session_state.combined_data, processed_df], ignore_index=True)
                
                st.session_state.processed_files += 1
                
            except Exception as e:
                st.session_state.processing_errors.append(f"Error processing {file.name}: {str(e)}")
            
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
        st.subheader("Processing Errors")
        for error in st.session_state.processing_errors:
            st.error(error)

else:
    st.info("Please upload one or more invoice files (CSV, XLSX, or XLS) to begin.")

# Add some helpful information at the bottom
st.markdown("---")
st.markdown("""
### How it works
1. Upload multiple invoice files (CSV, XLSX, or XLS formats)
2. The application automatically detects columns for:
   - EVSE ID (charging station identifier)
   - Session ID (transaction identifier)
   - Currency
   - Price (net price, intelligently distinguished from VAT rates)
3. Smart price detection analyzes VAT rate columns to find the correct price column
4. Header rows are automatically detected and skipped
5. Data is combined into a single standardized output
6. Download the combined file
""")
