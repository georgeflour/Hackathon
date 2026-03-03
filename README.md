# Azure Bill Extraction - Quick Start

The Azure extraction functionality is now available as a module in `src/backend/`.

## Setup

1. Make sure you have your `.env` file with Azure credentials:
```bash
AZURE_DOC_KEY=your_azure_key_here
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

## Usage Options

### Option 1: Run directly from command line

```bash
python src/backend/extractData.py front.jpg back.jpg
```

### Option 2: Import as a module

```python
from src.backend import get_ocr_lines, parse_front, parse_back, print_results

# Extract data
lines = get_ocr_lines("front.jpg")
front_data = parse_front(lines)

# Access fields
account = front_data.get("account_number")
total = front_data.get("invoice_total_eur")
```

### Option 3: Use the example script

```bash
python example_usage.py
```

## Available Functions

- `get_ocr_lines(file_path)` - Extract text lines from image using Azure
- `parse_front(lines)` - Parse front page data
- `parse_back(lines)` - Parse back page data  
- `print_results(front_data, back_data)` - Pretty print extracted data
- `parse_date(s)` - Helper to parse dates
- `after(lines, keyword, offset)` - Helper to find text after keyword
- `find_re(text, pattern)` - Helper to find regex patterns

## What Gets Extracted

### Front Page
- Customer info (name, address, account)
- Invoice details (number, dates, total)
- Service period and consumption

### Back Page
- Meter readings
- All charge breakdowns (supply, regulated, misc, VAT, municipality)

Now all your other code is preserved, and you can easily import and use the extraction functions!
