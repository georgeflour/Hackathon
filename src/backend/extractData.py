"""
Extract structured data from OCR lines of a DEH electricity bill.
Updated for new "Εκκαθαριστικός λογαριασμός" format.
"""
from dotenv import load_dotenv
load_dotenv()
import re
import os
import sys
from datetime import datetime
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

ENDPOINT = "https://hacktothefuture-resource.cognitiveservices.azure.com"
KEY = os.environ.get("AZURE_DOC_KEY", "")

def get_ocr_lines(file_path: str, debug: bool = False) -> list[str]:
    """Extract text lines from image using Azure Document Intelligence."""
    client = DocumentIntelligenceClient(endpoint=ENDPOINT, credential=AzureKeyCredential(KEY))
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-invoice", body=f)
    result = poller.result()
    lines = [line.content.strip() for page in result.pages for line in page.lines]
    
    if debug:
        print("\n" + "="*80)
        print("DEBUG: OCR OUTPUT")
        print("="*80)
        for i, line in enumerate(lines):
            print(f"{i:3d}: {line}")
        print("="*80 + "\n")
    
    return lines


def parse_date(s: str) -> str | None:
    """Parse Greek date format DD/MM/YYYY to ISO format."""
    if not s:
        return None
    m = re.search(r"(\d{2}/\d{2}/\d{4})", s)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d/%m/%Y").date().isoformat()
        except ValueError:
            pass
    return None


def after(lines: list[str], keyword: str, offset: int = 1) -> str | None:
    """Return the line N positions after the line containing keyword (case-insensitive)."""
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            idx = i + offset
            if idx < len(lines):
                return lines[idx].strip()
    return None


def find_re(text: str, pattern: str) -> str | None:
    """Find first regex match in text."""
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def extract_euro_amount(s: str) -> str | None:
    """Extract euro amount from string (handles both comma and dot decimals)."""
    if not s:
        return None
    # Match patterns like: 127,64 €, 100,55€, 147,19 €
    m = re.search(r"([\d]+[,.][\d]{2})\s*€?", s)
    return m.group(1) if m else None


# ── FRONT PAGE (New Format) ───────────────────────────────────────
def parse_front_new(lines: list[str]) -> dict:
    """Parse new DEH settlement bill format (Εκκαθαριστικός λογαριασμός)."""
    text = "\n".join(lines)
    data = {}

    # Vendor info
    data["vendor_name"] = "ΔΕΗ Α.Ε."
    
    # Bill type and tariff
    data["bill_type"] = find_re(text, r"(Εκκαθαριστικός\s+λογαριασμός|Εκτίμηση ΔΕΔΔΗΕ)")
    if not data["bill_type"]:
        # Try alternate pattern
        if "Εκκαθαριστικός" in text and "λογαριασμός" in text:
            data["bill_type"] = "Εκκαθαριστικός λογαριασμός"
    # Clean up extra whitespace/newlines
    if data["bill_type"]:
        data["bill_type"] = " ".join(data["bill_type"].split())
    
    data["tariff_status"] = find_re(text, r"(Σταθερό προϊόν|Κυμαινόμενο προϊόν)")
    data["tariff_type"] = find_re(text, r"Τιμολόγιο:\s*\n?([^\n]+)")
    if not data["tariff_type"]:
        # Try alternate pattern for tariff on same line
        data["tariff_type"] = find_re(text, r"Τιμολόγιο:\s+([^\n]+)")
    
    # Customer address
    data["customer_address"] = find_re(text, r"Διεύθυνση ακινήτου:\s*\n?([^\n]+)")
    if not data["customer_address"]:
        # Fallback: look for address pattern after "ακινήτου"
        data["customer_address"] = after(lines, "Διεύθυνση ακινήτου")
    
    # Dates
    data["invoice_due_date"] = parse_date(find_re(text, r"ΕΞΟΦΛΗΣΗ ΕΩΣ\s+(\d{2}/\d{2}/\d{4})"))
    data["next_meter_read_date"] = parse_date(find_re(text, r"Επόμενη καταμέτρηση:\s+(\d{2}/\d{2}/\d{4})"))
    data["issue_date"] = parse_date(find_re(text, r"Ημ/νία Έκδοσης\s+(\d{2}/\d{2}/\d{4})"))
    
    # Period
    period_match = re.search(r"Περίοδος Κατανάλωσης\s+(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})", text)
    if period_match:
        data["service_period_start"] = period_match.group(1)
        data["service_period_end"] = period_match.group(2)
    else:
        # Try alternate pattern - period might be on separate lines
        period_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})", text)
        if period_match:
            data["service_period_start"] = period_match.group(1)
            data["service_period_end"] = period_match.group(2)
    
    # Billing days and consumption
    data["billing_days"] = find_re(text, r"Ημέρες\s+(\d+)")
    data["kwh_consumed"] = find_re(text, r"Κατανάλωση Ηλεκτρικής Ενέργειας\s+([\d]+)\s*kWh")
    
    # Account and supply numbers
    data["supply_number"] = find_re(text, r"Αριθμός παροχής\s+([\d]+)")
    if not data["supply_number"]:
        data["supply_number"] = find_re(text, r"παροχής\s+([\d]+)")
    
    data["account_number"] = find_re(text, r"Α/Α Λογαριασμού\s+([\d]+)")
    if not data["account_number"]:
        data["account_number"] = find_re(text, r"Λογαριασμού\s+([\d]+)")
    if not data["account_number"]:
        # Sometimes OCR reads number before label - scan backwards
        for i, line in enumerate(lines):
            if "Α/Α Λογαριασμού" in line or "Λογαριασμού" in line:
                # Check previous lines for an 11-digit number
                for j in range(max(0, i-5), i):
                    if re.match(r"^\d{11}$", lines[j].strip()):
                        data["account_number"] = lines[j].strip()
                        break
                if data["account_number"]:
                    break
    
    # Payment reference (barcode) - try multiple patterns
    # Note: May only be visible as barcode image or on back page
    data["payment_reference"] = find_re(text, r"(RF[\d]{2}[\d]+)")
    if not data["payment_reference"]:
        # Try scanning for RF pattern anywhere in lines
        for line in lines:
            if line.startswith("RF") and len(line) > 10:
                # Remove spaces and check if mostly digits after RF
                clean = line.replace(" ", "")
                if clean.startswith("RF") and clean[2:4].isdigit():
                    data["payment_reference"] = clean
                    break
    
    # Amounts - Main charges
    data["supply_charges_eur"] = extract_euro_amount(after(lines, "Χρεώσεις προμήθειας ΔΕΗ"))
    data["regulated_charges_eur"] = extract_euro_amount(after(lines, "Ρυθμιζόμενες χρεώσεις"))
    data["opposite_consumption_eur"] = extract_euro_amount(after(lines, "Έναντι Κατανάλωσης"))
    data["misc_charges_eur"] = extract_euro_amount(after(lines, "Διάφορα - Δήμος - ΕΡΤ"))
    if not data["misc_charges_eur"]:
        # Sometimes amount appears before the label in multi-column layout
        for i, line in enumerate(lines):
            if "Διάφορα" in line and "Δήμος" in line and "ΕΡΤ" in line:
                # Search backward for euro amount
                for j in range(max(0, i-10), i):
                    amount = extract_euro_amount(lines[j])
                    if amount and j > 0:
                        # Make sure it's not already captured by other fields
                        # (check it's not the VAT, regulated, or supply charges)
                        prev_context = ' '.join(lines[max(0, j-2):j+1]).lower()
                        if not any(word in prev_context for word in ['φπα', 'ρυθμιζόμενες', 'προμήθειας', 'κατανάλωσης']):
                            data["misc_charges_eur"] = amount
                            break
                if data["misc_charges_eur"]:
                    break
    data["vat_eur"] = extract_euro_amount(after(lines, "ΦΠΑ"))
    
    # Previous unpaid amount
    data["previous_unpaid_eur"] = extract_euro_amount(after(lines, "Προηγούμενο Ανεξόφλητο Ποσό"))
    # If label exists but no amount, check if it's on the same line or next line
    if not data["previous_unpaid_eur"]:
        for i, line in enumerate(lines):
            if "Προηγούμενο Ανεξόφλητο Ποσό" in line:
                # Check same line
                amount = extract_euro_amount(line)
                if amount:
                    data["previous_unpaid_eur"] = amount
                    break
                # Check next line
                if i + 1 < len(lines):
                    amount = extract_euro_amount(lines[i + 1])
                    if amount:
                        data["previous_unpaid_eur"] = amount
                        break
                # If label exists but no amount found, it means 0
                data["previous_unpaid_eur"] = "0,00"
                break
    
    # Total amounts
    data["invoice_total_eur"] = extract_euro_amount(find_re(text, r"ΠΟΣΟ ΠΛΗΡΩΜΗΣ\s+([\d]+[,.][\d]{2})\s*€"))
    if not data["invoice_total_eur"]:
        data["invoice_total_eur"] = extract_euro_amount(find_re(text, r"Συνολικό ποσό πληρωμής\s+([\d]+[,.][\d]{2})\s*€"))
    
    return data


# ── BACK PAGE (New Format) ────────────────────────────────────────
def parse_back_new(lines: list[str]) -> dict:
    """Parse back page of new DEH settlement bill."""
    text = "\n".join(lines)
    data = {}
    
    # Customer info
    data["customer_code"] = find_re(text, r"Κωδικός Εταίρου\s*[:.]?\s*\n([^\n]+)")
    data["contract_number"] = find_re(text, r"Λογ\. Συμβολαίου\s*[:.]?\s*\n([^\n]+)")
    data["tax_id_invoice"] = find_re(text, r"Αρ\. Παραστατικού\s*[:.]?\s*\n([^\n]+)")
    data["afm_adt"] = find_re(text, r"ΑΦΜ/ΑΔΤ\s*[:.]?\s*\n([^\n]+)")
    data["maaht"] = find_re(text, r"ΜΑΑΗΤ\s*[:.]?\s*\n([^\n]+)")
    data["address_identification"] = find_re(text, r"Αδρ\. Αναγνώρισης/ΑΔΑμ\s*[:.]?\s*\n([^\n]+)")
    
    # Meter readings
    meter_readings = []
    # Look for meter reading table pattern
    # Pattern: Meter_ID | Type | Last_Reading | Previous_Reading | Difference | Coefficient | Total_kWh
    meter_pattern = r"(\d{7,8})\s+([\d]{1,2})\s+([\d]+)\s+([\d]+)\s+([\d]+)\s+([\d]+)\s+([\d]+)"
    for match in re.finditer(meter_pattern, text):
        meter_readings.append({
            "meter_id": match.group(1),
            "type": match.group(2),
            "last_reading": match.group(3),
            "previous_reading": match.group(4),
            "difference": match.group(5),
            "coefficient": match.group(6),
            "total_kwh": match.group(7),
        })
    data["meter_readings"] = meter_readings
    
    # Detailed charges breakdown
    # Supply charges (Χρεώσεις Προμήθειας ΔΕΗ)
    data["supply_charges_total_eur"] = extract_euro_amount(after(lines, "Χρεώσεις Προμήθειας ΔΕΗ"))
    data["fixed_charge_eur"] = extract_euro_amount(after(lines, "Πάγια Χρέωση"))
    data["energy_charge_normal_eur"] = extract_euro_amount(find_re(text, r"Χρέωση Ενέργειας Κανονική[^\n]*\n[^\n]*\n([\d,\.]+)"))
    data["energy_charge_reduced_eur"] = extract_euro_amount(find_re(text, r"Χρέωση Ενέργειας Μειωμένη[^\n]*\n[^\n]*\n([\d,\.]+)"))
    
    # Regulated charges (Ρυθμιζόμενες Χρεώσεις)
    data["regulated_charges_total_eur"] = extract_euro_amount(after(lines, "Ρυθμιζόμενες Χρεώσεις"))
    data["admie_eur"] = extract_euro_amount(find_re(text, r"ΑΔΜΗΕ[:\s]+Σύστημα Μεταφοράς Η/Ε[^\n]*\n[^\n]*\n([\d,\.]+)"))
    data["deddie_eur"] = extract_euro_amount(find_re(text, r"ΔΕΔΔΗΕ[:\s]+Δίκτυο Διανομής Η/Ε[^\n]*\n[^\n]*\n([\d,\.]+)"))
    data["yko_eur"] = extract_euro_amount(find_re(text, r"ΥΚΩ[:\s]+Υπηρεσίες Κοινής Ωφέλειας[^\n]*\n[^\n]*\n([\d,\.]+)"))
    data["etmeap_eur"] = extract_euro_amount(find_re(text, r"ΕΤΜΕΑΡ[^\n]*\n[^\n]*\n([\d,\.]+)"))
    
    # Opposite consumption
    data["opposite_consumption_total_eur"] = extract_euro_amount(after(lines, "Έναντι Κατανάλωσης"))
    
    # Misc charges
    data["misc_total_eur"] = extract_euro_amount(after(lines, "Διάφορα"))
    data["efk_eur"] = extract_euro_amount(find_re(text, r"ΕΦΚ \(Ν\. 3336/05\)[^\n]*\n([\d,\.]+)"))
    data["special_tax_eur"] = extract_euro_amount(find_re(text, r"ΕΙΔ\.ΤΕΛ\. 5ο/οο[^\n]*\n([\d,\.]+)"))
    data["late_interest_eur"] = extract_euro_amount(after(lines, "Τόκοι Υπερημερίας"))
    data["stamp_duty_eur"] = extract_euro_amount(find_re(text, r"Χαρτόσημο[^\n]*\n([\d,\.]+)"))
    data["rounding_eur"] = extract_euro_amount(after(lines, "Στρογγ/ση Πληρ. Ποσού"))
    data["prev_rounding_eur"] = extract_euro_amount(after(lines, "Ποσό Στρογγ. Προηγ. Λογ."))
    
    # VAT
    data["vat_eur"] = extract_euro_amount(find_re(text, r"ΦΠΑ[^\n]*\n.*?=\s*([\d,\.]+)"))
    data["vat_base_eur"] = find_re(text, r"ΦΠΑ ΡΕΥΜΑΤΟΣ\s+([\d,\.]+)\s+x")
    data["vat_rate_pct"] = find_re(text, r"x\s+(\d+)%")
    
    # Municipality charges (Δήμος ΑΘΗΝΑΙΩΝ)
    data["municipality_total_eur"] = extract_euro_amount(after(lines, "ΑΘΗΝΑΙΩΝ"))
    data["dt_eur"] = extract_euro_amount(find_re(text, r"ΔΤ:\s*[\d]+\s*[Xx]\s*[\d,\.]+\s*[Xx]\s*[\d/]+\s*=\s*([\d,\.]+)"))
    data["df_eur"] = extract_euro_amount(find_re(text, r"ΔΦ:\s*[\d]+\s*[Xx]\s*[\d,\.]+\s*[Xx]\s*[\d/]+\s*=\s*([\d,\.]+)"))
    data["tap_eur"] = extract_euro_amount(find_re(text, r"ΤΑΠ:\s*[\d]+\s*[Xx]\s*[\d,\.]+\s*[Xx]\s*[\d/]+\s*=\s*([\d,\.]+)"))
    
    # ERT
    data["ert_eur"] = extract_euro_amount(find_re(text, r"ΕΡΤ[^\n]*\n.*?=\s*([\d,\.]+)"))
    data["ert_annual_charge"] = extract_euro_amount(find_re(text, r"ετήσια χρέωση[^\n]*\n[^\n]*\n\s*([\d,\.]+)"))
    
    return data


# Aliases for backward compatibility
parse_front = parse_front_new
parse_back = parse_back_new


# ── PRINT RESULTS ─────────────────────────────────────────────────
def print_results(front: dict, back: dict):
    """Print extracted data in formatted tables."""
    def show(label, d):
        print(f"\n{'═'*70}")
        print(f"  {label}")
        print(f"{'═'*70}")
        meter_readings = d.pop("meter_readings", [])
        for k, v in d.items():
            status = "✅" if v is not None and v != "" else "❌"
            print(f"  {status} {k:<40}: {v}")
        if meter_readings:
            print(f"\n  📊 METER READINGS")
            print(f"  {'Meter ID':<12} {'Type':<6} {'Last':<8} {'Prev':<8} {'Diff':<8} {'Coef':<6} {'Total kWh'}")
            print(f"  {'-'*65}")
            for r in meter_readings:
                print(f"  {r['meter_id']:<12} {r['type']:<6} {r['last_reading']:<8} {r['previous_reading']:<8} {r['difference']:<8} {r['coefficient']:<6} {r['total_kwh']}")

    if front:
        show("FRONT PAGE — Customer & Invoice Summary", front)
    if back:
        show("BACK PAGE  — Charges & Meter Detail", back)
    print(f"\n{'═'*70}")


# ── MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract data from DEH electricity bills')
    parser.add_argument('front', help='Front page image file')
    parser.add_argument('back', nargs='?', help='Back page image file (optional)')
    parser.add_argument('--debug', '-d', action='store_true', help='Show OCR debug output')
    
    args = parser.parse_args()

    front_file = args.front
    back_file = args.back
    debug_mode = args.debug or os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")

    front_data = back_data = None

    if front_file and os.path.exists(front_file):
        print(f"🔍 OCR front page: {front_file}")
        front_lines = get_ocr_lines(front_file, debug=debug_mode)
        front_data = parse_front_new(front_lines)
        front_data["source_file"] = os.path.basename(front_file)
    else:
        print(f"⚠️  Front file not found: {front_file}")

    if back_file and os.path.exists(back_file):
        print(f"🔍 OCR back page:  {back_file}")
        back_lines = get_ocr_lines(back_file, debug=debug_mode)
        back_data = parse_back_new(back_lines)
        back_data["source_file"] = os.path.basename(back_file)
    else:
        if back_file:
            print(f"⚠️  Back file not found: {back_file}")
        else:
            print(f"ℹ️  No back file provided (optional)")

    print_results(front_data, back_data)
