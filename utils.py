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


def detect_full_company_name(df):
    """
    Detect the column containing the full company name.
    
    Args:
        df: pandas DataFrame
    
    Returns:
        str: name of the column containing full company name
    """
    # Check column names first
    company_name_patterns = [
        re.compile(r'company\s*(?:full)*\s*name', re.IGNORECASE),
        re.compile(r'full\s*name', re.IGNORECASE),
        re.compile(r'vendor\s*name', re.IGNORECASE),
        re.compile(r'supplier\s*name', re.IGNORECASE),
        re.compile(r'business\s*name', re.IGNORECASE),
        re.compile(r'client\s*name', re.IGNORECASE),
        re.compile(r'full\s*company', re.IGNORECASE),
        re.compile(r'company', re.IGNORECASE)
    ]
    
    # Check column names
    for pattern in company_name_patterns:
        for col in df.columns:
            if pattern.search(str(col)):
                return col
    
    # If column names don't match, check contents
    # Look for columns that have string values with capital letters, spaces, and longer length
    # Characteristic of company names
    string_columns = []
    
    for col in df.columns:
        sample = df[col].dropna().astype(str).head(10)
        
        # Skip columns with numeric values
        if all(is_numeric(val) for val in sample):
            continue
            
        # Look for values that look like company names
        # - Contain multiple words
        # - Contain both uppercase and lowercase letters
        # - Longer average length
        
        word_counts = sample.apply(lambda x: len(str(x).split()))
        avg_words = word_counts.mean()
        
        # Has capitalization pattern typical of names
        has_capitalization = sample.apply(lambda x: bool(re.search(r'[A-Z][a-z]', str(x)))).mean() > 0.5
        
        # Average string length
        avg_length = sample.apply(len).mean()
        
        # Check for presence of business identifiers
        business_terms = sample.apply(lambda x: bool(re.search(r'\b(Inc|LLC|Ltd|GmbH|Corp|Company|Co)\b', str(x)))).mean() > 0.2
        
        score = (avg_words * 2) + (has_capitalization * 3) + (avg_length * 0.1) + (business_terms * 4)
        
        string_columns.append((col, score))
    
    # Sort by score in descending order
    string_columns.sort(key=lambda x: x[1], reverse=True)
    
    # Return the highest scoring column or None if none found
    if string_columns and string_columns[0][1] > 2:
        return string_columns[0][0]
    
    return None


def detect_short_company_name(df, full_name_col=None):
    """
    Detect the column containing the short company name.
    
    Args:
        df: pandas DataFrame
        full_name_col: column containing full company name
    
    Returns:
        str: name of the column containing short company name
    """
    # Check column names first
    short_name_patterns = [
        re.compile(r'short\s*(?:company)*\s*name', re.IGNORECASE),
        re.compile(r'company\s*short\s*name', re.IGNORECASE),
        re.compile(r'abbrev', re.IGNORECASE),
        re.compile(r'short', re.IGNORECASE),
        re.compile(r'code', re.IGNORECASE),
        re.compile(r'acronym', re.IGNORECASE)
    ]
    
    # Check column names
    for pattern in short_name_patterns:
        for col in df.columns:
            if pattern.search(str(col)):
                return col
    
    # Look for columns with abbreviations/short text
    # that are not the full name column
    string_columns = []
    
    for col in df.columns:
        if col == full_name_col:
            continue
            
        sample = df[col].dropna().astype(str).head(10)
        
        # Skip columns with numeric values
        if all(is_numeric(val) for val in sample):
            continue
            
        # Characteristics of short names:
        # - Short average length
        # - Often uppercase
        # - Few words
        
        word_counts = sample.apply(lambda x: len(str(x).split()))
        avg_words = word_counts.mean()
        
        # Mainly uppercase or short codes
        is_uppercase = sample.apply(lambda x: str(x).isupper()).mean() > 0.5
        
        # Average string length
        avg_length = sample.apply(len).mean()
        
        # Short names would be shorter than full names
        length_score = 10 / (avg_length + 1) if avg_length < 15 else 0
        
        # Adjust for uppercase text
        uppercase_score = 2 if is_uppercase else 0
        
        # Ideally just 1-2 words
        word_score = 3 if avg_words <= 2 else 0
        
        score = length_score + uppercase_score + word_score
        
        string_columns.append((col, score))
    
    # Sort by score in descending order
    string_columns.sort(key=lambda x: x[1], reverse=True)
    
    # Return the highest scoring column or None if none found
    if string_columns and string_columns[0][1] > 2:
        return string_columns[0][0]
    
    # If we have a full name but no good short name, create one
    if full_name_col:
        return None  # Will be handled in standardize_dataframe
    
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
        dict: detected column names for full_name, short_name, currency, price
    """
    # Initialize with None values
    detected = {
        'full_name': None,
        'short_name': None,
        'currency': None,
        'price': None
    }
    
    # Detect each column
    detected['full_name'] = detect_full_company_name(df)
    detected['short_name'] = detect_short_company_name(df, detected['full_name'])
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
    if detected_columns['full_name']:
        standardized_df['company_full_name'] = df[detected_columns['full_name']]
    else:
        standardized_df['company_full_name'] = "Unknown"
    
    # Handle short name - generate from full name if not detected
    if detected_columns['short_name']:
        standardized_df['company_short_name'] = df[detected_columns['short_name']]
    elif detected_columns['full_name']:
        # Generate short name from full name
        standardized_df['company_short_name'] = standardized_df['company_full_name'].apply(
            lambda x: generate_short_name(x) if pd.notna(x) else "Unknown"
        )
    else:
        standardized_df['company_short_name'] = "Unknown"
    
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
