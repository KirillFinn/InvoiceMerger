import pandas as pd
import numpy as np
import re
import io
import csv

def is_header_row(row):
    """
    Detect if a row is likely to be a header based on content patterns.
    
    Args:
        row: pandas Series representing a row
    
    Returns:
        bool: True if the row looks like a header
    """
    # Check if more than 50% of cells contain potential header keywords
    header_pattern = re.compile(r'(name|company|currency|price|amount|total|invoice|date|sum|vendor)', re.IGNORECASE)
    
    # Check for non-numeric content
    non_numeric_count = 0
    header_keyword_count = 0
    
    for cell in row:
        if cell is None or pd.isna(cell):
            continue
            
        cell_str = str(cell).strip()
        
        # Skip empty cells
        if not cell_str:
            continue
            
        # Check for header patterns
        if header_pattern.search(cell_str):
            header_keyword_count += 1
            
        # Check if cell is non-numeric (headers are typically non-numeric)
        try:
            float(cell_str.replace(',', '.'))
        except ValueError:
            non_numeric_count += 1
    
    # Calculate the proportion of non-empty cells that match header patterns
    non_empty_cells = sum(1 for cell in row if cell is not None and not pd.isna(cell) and str(cell).strip())
    
    if non_empty_cells == 0:
        return False
        
    header_keyword_ratio = header_keyword_count / non_empty_cells
    non_numeric_ratio = non_numeric_count / non_empty_cells
    
    # If high proportion of cells contain header keywords or are non-numeric, likely a header
    return header_keyword_ratio > 0.3 or non_numeric_ratio > 0.7


def detect_evse_id(df):
    """
    Detect the column containing the EVSE ID.
    
    Args:
        df: pandas DataFrame
    
    Returns:
        str: name of the column containing EVSE ID
    """
    # Check column names first
    evse_id_patterns = [
        re.compile(r'evse[\s_-]*id', re.IGNORECASE),
        re.compile(r'evse', re.IGNORECASE),
        re.compile(r'charge[\s_-]*point[\s_-]*id', re.IGNORECASE),
        re.compile(r'charging[\s_-]*station[\s_-]*id', re.IGNORECASE),
        re.compile(r'station[\s_-]*id', re.IGNORECASE),
        re.compile(r'charger[\s_-]*id', re.IGNORECASE),
        re.compile(r'cp[\s_-]*id', re.IGNORECASE)  # CP often stands for Charge Point
    ]
    
    # Check column names
    for pattern in evse_id_patterns:
        for col in df.columns:
            if pattern.search(str(col)):
                return col
    
    # If column names don't match, check contents
    # EVSE IDs typically have a pattern: alphanumeric with possible separators
    string_columns = []
    
    for col in df.columns:
        sample = df[col].dropna().astype(str).head(10)
        
        # Skip columns with purely numeric values
        if all(is_numeric(val) for val in sample):
            continue
            
        # Look for values that look like EVSE IDs
        # - Often have a consistent format
        # - May contain alphanumeric characters with separators
        # - Usually not too long or too short
        
        # Check for alphanumeric pattern with possible separators
        has_alphanumeric = sample.apply(lambda x: bool(re.search(r'^[A-Za-z0-9\-_\.]+$', str(x)))).mean() > 0.5
        
        # Average string length - EVSE IDs usually have moderate length
        avg_length = sample.apply(len).mean()
        length_score = 2 if 4 <= avg_length <= 20 else 0
        
        # Consistent length is a good indicator of IDs
        std_length = sample.apply(len).std()
        consistent_length = 2 if std_length < 2 else 0
        
        score = (has_alphanumeric * 3) + length_score + consistent_length
        
        string_columns.append((col, score))
    
    # Sort by score in descending order
    string_columns.sort(key=lambda x: x[1], reverse=True)
    
    # Return the highest scoring column or None if none found
    if string_columns and string_columns[0][1] > 2:
        return string_columns[0][0]
    
    return None


def detect_session_id(df, evse_id_col=None):
    """
    Detect the column containing the Session ID.
    
    Args:
        df: pandas DataFrame
        evse_id_col: column containing EVSE ID (to avoid selecting the same column)
    
    Returns:
        str: name of the column containing Session ID
    """
    # Check column names first
    session_id_patterns = [
        re.compile(r'session[\s_-]*id', re.IGNORECASE),
        re.compile(r'transaction[\s_-]*id', re.IGNORECASE),
        re.compile(r'charge[\s_-]*session[\s_-]*id', re.IGNORECASE),
        re.compile(r'charging[\s_-]*session', re.IGNORECASE),
        re.compile(r'session[\s_-]*number', re.IGNORECASE)
    ]
    
    # Check column names
    for pattern in session_id_patterns:
        for col in df.columns:
            if pattern.search(str(col)):
                return col
    
    # Look for columns with values that look like session IDs
    # that are not the EVSE ID column
    string_columns = []
    
    for col in df.columns:
        if col == evse_id_col:
            continue
            
        sample = df[col].dropna().astype(str).head(10)
        
        # Skip columns with purely numeric short values
        if all(is_numeric(val) and len(str(val)) < 6 for val in sample):
            continue
            
        # Characteristics of session IDs based on user description:
        # - Long strings with numbers and small letters
        # - Often separated by hyphens
        
        # Check for pattern matching session ID format (letters, numbers, hyphens)
        has_session_format = sample.apply(lambda x: bool(re.search(r'[a-z0-9\-]+', str(x)))).mean() > 0.8
        
        # Check specifically for hyphens which are common in session IDs
        has_hyphens = sample.apply(lambda x: '-' in str(x)).mean() > 0.5
        
        # Average string length - session IDs often longer than other IDs
        avg_length = sample.apply(len).mean()
        length_score = 3 if avg_length > 10 else 0
        
        # Consistent formatting is a good indicator
        consistent_format = sample.apply(lambda x: bool(re.match(r'^[a-z0-9\-]+$', str(x).lower()))).mean() > 0.7
        
        score = (has_session_format * 2) + (has_hyphens * 3) + length_score + (consistent_format * 2)
        
        string_columns.append((col, score))
    
    # Sort by score in descending order
    string_columns.sort(key=lambda x: x[1], reverse=True)
    
    # Return the highest scoring column or None if none found
    if string_columns and string_columns[0][1] > 3:
        return string_columns[0][0]
    
    return None


def detect_currency(df):
    """
    Detect the column containing currency information.
    
    Args:
        df: pandas DataFrame
    
    Returns:
        str: name of the column containing currency
    """
    # Check column names first
    currency_patterns = [
        re.compile(r'currency', re.IGNORECASE),
        re.compile(r'curr', re.IGNORECASE),
        re.compile(r'ccy', re.IGNORECASE)
    ]
    
    # Check column names
    for pattern in currency_patterns:
        for col in df.columns:
            if pattern.search(str(col)):
                return col
    
    # Check for columns with currency codes or symbols
    currency_codes = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'INR']
    currency_symbols = ['$', '€', '£', '¥', '₹', '₽', '₩']
    
    best_match = None
    best_score = 0
    
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue  # Skip numeric columns
            
        sample = df[col].dropna().astype(str).head(20)
        
        # Count how many values match common currency codes
        code_matches = sum(1 for val in sample if any(code == val.strip().upper() for code in currency_codes))
        
        # Count how many values contain currency symbols
        symbol_matches = sum(1 for val in sample if any(symbol in val for symbol in currency_symbols))
        
        # Check for short length (currency codes are typically 3 chars)
        avg_length = sample.apply(len).mean()
        length_score = 2 if 1 <= avg_length <= 4 else 0
        
        # Calculate match score
        score = (code_matches * 2) + (symbol_matches * 2) + length_score
        
        if score > best_score:
            best_score = score
            best_match = col
    
    # Return the best match if above threshold
    if best_score >= 2:
        return best_match
    
    return None


def detect_price(df):
    """
    Detect the column containing price information.
    
    Args:
        df: pandas DataFrame
    
    Returns:
        str: name of the column containing price
    """
    # Check column names first
    price_patterns = [
        re.compile(r'price', re.IGNORECASE),
        re.compile(r'amount', re.IGNORECASE),
        re.compile(r'total', re.IGNORECASE),
        re.compile(r'sum', re.IGNORECASE),
        re.compile(r'cost', re.IGNORECASE),
        re.compile(r'fee', re.IGNORECASE),
        re.compile(r'value', re.IGNORECASE)
    ]
    
    # Check column names
    for pattern in price_patterns:
        for col in df.columns:
            if pattern.search(str(col)):
                # Verify it contains numeric data
                if is_numeric_column(df[col]):
                    return col
    
    # Look for numeric columns
    numeric_cols = []
    
    for col in df.columns:
        # Check if column has numeric values
        if is_numeric_column(df[col]):
            # Calculate statistics to identify price column
            # Prices are typically positive numbers with decimal places
            values = pd.to_numeric(df[col], errors='coerce')
            
            # Skip columns with many NaN values
            if values.isna().sum() > len(df) * 0.7:
                continue
                
            non_na_values = values.dropna()
            
            if len(non_na_values) == 0:
                continue
                
            # Calculate score based on characteristics of price values
            # Prices are typically positive
            positive_ratio = (non_na_values > 0).mean()
            
            # Prices often have decimal places
            has_decimals = non_na_values.apply(lambda x: x % 1 != 0).mean()
            
            # Prices typically have reasonable magnitude (not too small or large)
            magnitude_score = 0
            mean_value = non_na_values.mean()
            
            if 0.1 <= mean_value <= 1000000:
                magnitude_score = 1
            
            # Calculate overall score
            score = (positive_ratio * 2) + (has_decimals * 2) + magnitude_score
            
            numeric_cols.append((col, score))
    
    # Sort by score in descending order
    numeric_cols.sort(key=lambda x: x[1], reverse=True)
    
    # Return the highest scoring column or None if none found
    if numeric_cols and numeric_cols[0][1] >= 2:
        return numeric_cols[0][0]
    
    return None


def is_numeric(value):
    """Check if a value is numeric."""
    try:
        # Replace comma with dot for European number formats
        float(str(value).replace(',', '.'))
        return True
    except (ValueError, TypeError):
        return False


def is_numeric_column(column):
    """Check if a column contains numeric values."""
    # Try to convert to numeric
    numeric_values = pd.to_numeric(column, errors='coerce')
    
    # Calculate the ratio of non-NA values
    non_na_ratio = numeric_values.notna().mean()
    
    # If at least 50% of values are numeric, consider it a numeric column
    return non_na_ratio >= 0.5


def detect_columns(df):
    """
    Detect relevant columns in the dataframe.
    
    Args:
        df: pandas DataFrame
    
    Returns:
        dict: detected column names for evse_id, session_id, currency, price
    """
    # Initialize with None values
    detected = {
        'evse_id': None,
        'session_id': None,
        'currency': None,
        'price': None
    }
    
    # Detect each column
    detected['evse_id'] = detect_evse_id(df)
    detected['session_id'] = detect_session_id(df, detected['evse_id'])
    detected['currency'] = detect_currency(df)
    detected['price'] = detect_price(df)
    
    return detected


def standardize_dataframe(df, detected_columns):
    """
    Standardize dataframe based on detected columns.
    
    Args:
        df: pandas DataFrame
        detected_columns: dict with detected column names
    
    Returns:
        pandas DataFrame: standardized dataframe
    """
    # Create a new dataframe with standardized columns
    standardized_df = pd.DataFrame()
    
    # Map detected columns to standardized column names
    if detected_columns['evse_id']:
        standardized_df['evse_id'] = df[detected_columns['evse_id']]
    else:
        standardized_df['evse_id'] = "Unknown"
    
    # Session ID is the most important column according to the user
    if detected_columns['session_id']:
        standardized_df['session_id'] = df[detected_columns['session_id']]
    else:
        standardized_df['session_id'] = "Unknown"
    
    if detected_columns['currency']:
        standardized_df['currency'] = df[detected_columns['currency']]
    else:
        standardized_df['currency'] = "Unknown"
    
    if detected_columns['price']:
        # Ensure price is numeric
        standardized_df['price'] = pd.to_numeric(df[detected_columns['price']], errors='coerce')
    else:
        standardized_df['price'] = np.nan
    
    return standardized_df


def generate_short_name(full_name):
    """
    Generate a short name from a full company name.
    
    Args:
        full_name: string with the full name
    
    Returns:
        str: short name
    """
    if not full_name or pd.isna(full_name):
        return "Unknown"
    
    full_name = str(full_name).strip()
    
    # Look for common company identifiers and remove them
    identifiers = [
        r'\b(Inc|LLC|Ltd|GmbH|Corp|Company|Co|Corporation|Limited|Group)\b',
        r',\s*\w+$'  # Remove commas and everything after
    ]
    
    cleaned_name = full_name
    for pattern in identifiers:
        cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE).strip()
    
    # If the name has multiple words, try to create an acronym
    words = cleaned_name.split()
    
    if len(words) > 1:
        # Create acronym from first letters
        acronym = ''.join(word[0].upper() for word in words if word)
        if len(acronym) >= 2:
            return acronym
    
    # If the name is short enough, return it as is
    if len(cleaned_name) <= 10:
        return cleaned_name
    
    # Otherwise, use the first 10 characters
    return cleaned_name[:10]


def detect_encoding_and_delimiter(file_content):
    """
    Detect the encoding and delimiter of a CSV file.
    
    Args:
        file_content: bytes content of the file
    
    Returns:
        tuple: (encoding, delimiter)
    """
    # Try common encodings
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            # Try to decode with the current encoding
            decoded_content = file_content.decode(encoding)
            
            # Use csv sniffer to detect delimiter
            dialect = csv.Sniffer().sniff(decoded_content[:4096])
            delimiter = dialect.delimiter
            
            return encoding, delimiter
        except (UnicodeDecodeError, csv.Error):
            continue
    
    # Default fallback
    return 'utf-8', ','


def process_file(file_content, filename):
    """
    Process a single file and return standardized dataframe.
    
    Args:
        file_content: bytes content of the file
        filename: name of the file
    
    Returns:
        pandas DataFrame: standardized dataframe
    """
    # Detect encoding and delimiter
    encoding, delimiter = detect_encoding_and_delimiter(file_content)
    
    # Read the file into a dataframe
    try:
        df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, delimiter=delimiter, engine='python')
    except:
        # If first attempt fails, try with more flexible parsing
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=None, engine='python')
        except Exception as e:
            raise ValueError(f"Failed to parse file {filename}: {str(e)}")
    
    # Handle empty dataframe
    if df.empty:
        raise ValueError(f"File {filename} is empty")
    
    # Check for and drop header rows
    rows_to_drop = []
    for i, row in df.iterrows():
        if is_header_row(row):
            rows_to_drop.append(i)
    
    # Drop header rows
    if rows_to_drop:
        df = df.drop(rows_to_drop).reset_index(drop=True)
    
    # Skip if dataframe is now empty
    if df.empty:
        raise ValueError(f"File {filename} contains only headers and no data")
    
    # Detect relevant columns
    detected_columns = detect_columns(df)
    
    # Check if any required columns are missing
    missing_columns = [k for k, v in detected_columns.items() if v is None]
    if len(missing_columns) > 2:  # Allow at most 2 missing columns
        raise ValueError(f"Failed to detect required columns in {filename}: {', '.join(missing_columns)}")
    
    # Standardize the dataframe
    standardized_df = standardize_dataframe(df, detected_columns)
    
    return standardized_df
