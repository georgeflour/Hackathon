# Azure Bill Extraction - Quick Start

The Azure extraction functionality is now available as a module in `src/backend/`.

## Setup

### 1. Install Azure CLI and Login

The easiest way to authenticate with Azure is using Azure CLI:
```bash
# Install Azure CLI (macOS)
brew install azure-cli

# Login to Azure (opens browser for authentication)
az login

# Verify you're logged in
az account show
```

After logging in, Azure credentials will be automatically used by the Python SDK.

### 2. Environment Variables

Make sure you have your `.env` file with Azure credentials:
```bash
AZURE_DOC_KEY=your_azure_key_here
AZURE_EXISTING_AIPROJECT_ENDPOINT=your_endpoint_here
AZURE_EXISTING_AGENT_ID=your_agent_id_here
AZURE_SUBSCRIPTION_ID=your_subscription_id_here
```

**Note:** If you've run `az login`, you may not need all these variables depending on which Azure services you're using.

### 3. Install Python Requirements
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

## Authentication Methods

### Method 1: Azure CLI (Recommended for local development)
```bash
az login
```
Then run your scripts normally - authentication is handled automatically.

### Method 2: Environment Variables
Set these in your `.env` file for service principal authentication:
```bash
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
```

### Method 3: API Key
Some Azure services support direct API key authentication via `AZURE_DOC_KEY`.

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

## Troubleshooting

### Authentication Errors
If you see `DefaultAzureCredential failed to retrieve a token`:
1. Run `az login` to authenticate
2. Verify with `az account show`
3. Make sure your account has permissions on the Azure resources

### Permission Errors (403)
If you see permission errors, you need the appropriate role:
1. Go to Azure Portal
2. Navigate to your resource
3. Access Control (IAM) → Add role assignment
4. Assign "Azure ML Data Scientist" or "Contributor" role

Now all your other code is preserved, and you can easily import and use the extraction functions!
