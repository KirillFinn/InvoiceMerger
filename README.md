# Invoice Merger

A Streamlit application that helps combine multiple CSV and Excel invoice files with different column structures into a single standardized output file.

## Features

- Automatically detects relevant columns:
  - EVSE ID (Electric Vehicle Supply Equipment identifier)
  - Session ID (unique transaction identifier for charging sessions)
  - Currency
  - Price (net price, distinguishing it from VAT rates)
- Supports multiple file formats (CSV, XLSX, XLS)
- Smart price detection that analyzes VAT rate columns
- Automatic header row detection
- Standardized output format
- User-friendly interface with progress tracking
- Error handling and reporting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/InvoiceMerger.git
cd InvoiceMerger
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the provided local URL (typically http://localhost:8501)

3. Upload your invoice files and follow the on-screen instructions

## Requirements

- Python 3.7+
- Streamlit
- Pandas
- Other dependencies listed in requirements.txt

## License

This project is licensed under the MIT License - see the LICENSE file for details.