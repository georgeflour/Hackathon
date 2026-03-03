"""
DEI (ΔΕΗ) Invoice Extractor — front page + back page
=====================================================
Usage:
    python3 extractData.py front.jpg back.jpg

Requirements:
    pip install azure-ai-documentintelligence azure-core
"""

import re
import os
import sys
from datetime import datetime, timezone
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

ENDPOINT = "https://recognisionimage.cognitiveservices.azure.com/"
KEY      = ""

def get_ocr_lines(file_path: str) -> list[str]:
    client = DocumentIntelligenceClient(endpoint=ENDPOINT, credential=AzureKeyCredential(KEY))
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-invoice", body=f)
    result = poller.result()
    return [line.content.strip() for page in result.pages for line in page.lines]


def parse_date(s: str) -> str | None:
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
    """Return the line N positions after the line containing keyword."""
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            idx = i + offset
            if idx < len(lines):
                return lines[idx].strip()
    return None


def inline_or_after(lines: list[str], keyword: str) -> str | None:
    """Return amount found on same line as keyword, or on the very next line."""
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            # try same line
            m = re.search(r"([\d]+[,.][\d]{2})€?$", line)
            if m:
                return m.group(1)
            # try next line
            if i + 1 < len(lines):
                m = re.search(r"^([\d]+[,.][\d]{2})$", lines[i + 1].strip())
                if m:
                    return m.group(1)
    return None


def find_re(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


# ── FRONT PAGE ────────────────────────────────────────────────────
def parse_front(lines: list[str]) -> dict:
    text = "\n".join(lines)
    data = {}

    data["vendor_name"]          = "ΔΕΗ Α.Ε."
    data["customer_name"]        = find_re(text, r"(ΜΠΟΥΦΑΛΗΣ[^\n]+)")
    data["customer_address"]     = find_re(text, r"(ΣΤΑΥΡΟΠΟΥΛΟΥ[^\n]+)")
    data["payment_reference"]    = find_re(text, r"(RF\d{2}[A-Z0-9]{10,})")
    data["supply_number"]        = find_re(text, r"παροχής\s*\n([\d\s\-]+\d)")
    if data["supply_number"]:
        data["supply_number"] = re.sub(r"\s+", "", data["supply_number"])
    data["account_number"]       = find_re(text, r"Λογαριασμού\s*\n(\d{7,})")
    data["barcode_ref"]          = find_re(text, r"(TT\d+GR)")
    data["tariff_type"]          = find_re(text, r"(Γ[ΊΙ]Ν Οικιακό Τιμολόγιο)")
    data["vendor_afm"]           = find_re(text, r"Α\.Φ\.Μ\.\s*([\d]+)")

    # Dates
    # Due date: scan forward from "ΕΞΟΦΛΗΣΗ ΕΩΣ" for the first line that is a date
    due_date = None
    for i, line in enumerate(lines):
        if "εξοφληση εως" in line.lower() or "εξόφληση εως" in line.lower():
            for j in range(i + 1, min(i + 5, len(lines))):
                d = parse_date(lines[j])
                if d:
                    due_date = d
                    break
    data["invoice_due_date"] = due_date
    data["issue_date"]       = parse_date(find_re(text, r"Έκδοσης\s+(\d{2}/\d{2}/\d{4})") or after(lines, "Έκδοσης") or "")
    data["next_meter_read_date"] = parse_date(find_re(text, r"καταμέτρηση[:\s]+([\d]{2}/[\d]{2}/[\d]{4})"))
    m_period = re.search(r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})", text)
    if m_period:
        data["service_period_start"] = m_period.group(1)
        data["service_period_end"]   = m_period.group(2)

    # Amounts — label then amount on next line
    data["invoice_total_eur"]      = find_re(text, r"\*([\d]+[,.][\d]{2})€")
    data["previous_unpaid_eur"]    = after(lines, "Ανεξόφλητο Ποσό")
    data["kwh_consumed"]           = find_re(text, r"Ηλεκτρικής Ενέργειας\s+([\d]+)\s*kWh")
    data["billing_days"]           = after(lines, "Ημέρες")

    return data


# ── BACK PAGE ─────────────────────────────────────────────────────
def parse_back(lines: list[str]) -> dict:
    text = "\n".join(lines)
    data = {}

    # Customer info box — value is 4 lines after label due to interleaved right-column OCR
    data["customer_code"]    = after(lines, "Κωδικός Εταίρου", offset=4)
    data["contract_number"]  = after(lines, "Λογ. Συμβολαίου")
    data["tax_id_invoice"]   = after(lines, "Αρ. Παραστατικού")
    data["afm_adt"]          = after(lines, "ΑΦΜ/ΑΔΤ")
    data["guarantee_eur"]    = after(lines, "Εγγύηση", offset=3)

    # Previous account ref
    prev = find_re(text, r"αριθμού Α/Α Λογαριασμού\s+(\d+)")
    data["previous_account_number"] = prev
    data["previous_account_date"]   = parse_date(find_re(text, r"Λογαριασμού\s+\d+\s+-\s+(\d{2}/\d{2}/\d{4})"))
    data["supply_number_back"]      = find_re(text, r"αριθμό παροχής\s+([\d\s\-]+\d)")

    # Meter readings — each value is on its own line
    # Lines go: meter_id / type / last / prev / diff / extra / total
    meter_readings = []
    i = 0
    while i < len(lines):
        if re.match(r"^\d{7,8}$", lines[i]):
            try:
                meter_readings.append({
                    "meter_id":         lines[i],
                    "type":             lines[i+1],
                    "last_reading":     lines[i+2],
                    "previous_reading": lines[i+3],
                    "difference":       lines[i+4],
                    "extra":            lines[i+5],
                    "total_kwh":        lines[i+6],
                })
                i += 7
                continue
            except IndexError:
                pass
        i += 1
    data["meter_readings"] = meter_readings

    # Supply charges block
    data["supply_charges_total_eur"]  = after(lines, "Χρεώσεις Προμήθειας ΔΕΗ")
    data["fixed_charge_eur"]          = after(lines, "Πάγια Χρέωση")
    data["energy_charge_normal_eur"]  = after(lines, "Χρέωση Ενέργειας Κανονική", offset=2)  # skip formula line
    data["energy_charge_reduced_eur"] = after(lines, "Χρέωση Ενέργειας Μειωμένη", offset=3)  # skip 2 formula lines

    # Regulated charges
    data["regulated_charges_total_eur"] = after(lines, "Ρυθμιζόμενες Χρεώσεις")
    data["admie_eur"]                   = after(lines, "ΑΔΜΗΕ: Σύστημα Μεταφοράς")
    data["deddie_eur"]                  = after(lines, "ΔΕΔΔΗΕ: Δίκτυο Διανομής", offset=2)
    data["yko_eur"]                     = after(lines, "Χρέωση κανονική 28νημ")
    data["etmeap_eur"]                  = after(lines, "ΕΤΜΕΑΡ", offset=2)  # skip formula line

    # Misc
    data["misc_total_eur"]        = after(lines, "Διάφορα")
    data["efk_eur"]               = after(lines, "ΕΦΚ (Ν. 3336/05)")
    data["eid_tel_eur"]           = after(lines, "ΕΙΔ.ΤΕΛ. 5ο/οο")
    data["late_interest_eur"]     = after(lines, "Τόκοι Υπερημερίας")
    data["paper_bill_charge_eur"] = after(lines, "Χαρτόσημο 3,6%")
    data["rounding_eur"]          = after(lines, "Στρογγ/ση Πληρ. Ποσού")
    data["prev_rounding_eur"]     = after(lines, "Ποσό Στρογγ. Προηγ. Λογ.")

    # VAT
    data["vat_eur"]      = after(lines, "ΦΠΑ")
    data["vat_base_eur"] = find_re(text, r"ΦΠΑ ΡΕΥΜΑΤΟΣ\s+([\d,\.]+)\s+x")
    data["vat_rate_pct"] = find_re(text, r"x\s+(\d+)%\s+=")

    # Municipality
    data["municipality_total_eur"] = after(lines, "Δήμος  ΑΘΗΝΑΙΩΝ") or after(lines, "Δήμος ΑΘΗΝΑΙΩΝ")
    data["dt_eur"]  = find_re(text, r"ΔΤ:\s*\d+\s*[Xx]\s*[\d,\.]+\s*[Xx]\s*[\d/]+\s*=\s*([\d,\.]+)")
    # ΔΦ value appears 2 lines BEFORE the "ΔΦ:" label in this OCR layout
    df_eur = None
    for i, line in enumerate(lines):
        if re.match(r"^ΔΦ\s*:", line.strip()) and i >= 2:
            candidate = lines[i - 2].strip()
            if re.match(r"^[\d]+[,.][\d]{2}$", candidate):
                df_eur = candidate
                break
    data["df_eur"] = df_eur

    data["tap_eur"] = find_re(text, r"ΤΑΠ:[^\n]+=\s*([\d,\.]+)")

    # ERT — value appears 2 lines BEFORE the "ΕΡΤ" label in this OCR layout
    for i, line in enumerate(lines):
        if line.strip() == "ΕΡΤ" and i >= 2:
            candidate = lines[i - 2].strip()
            if re.match(r"^[\d]+[,.][\d]{2}$", candidate):
                data["ert_eur"] = candidate
                break
    if not data.get("ert_eur"):
        data["ert_eur"] = after(lines, "ΕΡΤ")
    data["ert_annual_charge"] = find_re(text, r"ετήσια χρέωση[^\n]*\n[^\n]*\n\s*([\d,\.]+)")
    if not data["ert_annual_charge"]:
        # Fallback: the annual charge (36,00) appears right after ERT label area
        for i, line in enumerate(lines):
            if "ετήσια χρέωση" in line.lower():
                for j in range(i + 1, min(i + 5, len(lines))):
                    if re.match(r"^[\d]+[,.][\d]{2}$", lines[j].strip()):
                        data["ert_annual_charge"] = lines[j].strip()
                        break
                break

    return data


# ── PRINT ─────────────────────────────────────────────────────────
def print_results(front: dict, back: dict):
    def show(label, d):
        print(f"\n{'═'*65}")
        print(f"  {label}")
        print(f"{'═'*65}")
        meter_readings = d.pop("meter_readings", [])
        for k, v in d.items():
            status = "✅" if v is not None and v != "" else "❌"
            print(f"  {status} {k:<38}: {v}")
        if meter_readings:
            print(f"\n  📊 METER READINGS")
            print(f"  {'Meter ID':<12} {'Type':<6} {'Last':<8} {'Prev':<8} {'Diff':<8} {'Extra':<6} {'Total kWh'}")
            print(f"  {'-'*62}")
            for r in meter_readings:
                print(f"  {r['meter_id']:<12} {r['type']:<6} {r['last_reading']:<8} {r['previous_reading']:<8} {r['difference']:<8} {r['extra']:<6} {r['total_kwh']}")

    if front:
        show("FRONT PAGE — Customer & Invoice Summary", front)
    if back:
        show("BACK PAGE  — Charges & Meter Detail", back)
    print(f"\n{'═'*65}")


# ── MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 0:
        print("Usage: python3 extractData.py front.jpg [back.jpg]")
        print("       or set FILE_FRONT / FILE_BACK below")
        # fallback defaults
        args = ["Hackathon/data/IMG_6513_small.jpg", "Hackathon/data/IMG_6518_small.jpg"]

    front_file = args[0] if len(args) > 0 else None
    back_file  = args[1] if len(args) > 1 else None

    front_data = back_data = None

    if front_file and os.path.exists(front_file):
        print(f"🔍 OCR front page: {front_file}")
        front_lines = get_ocr_lines(front_file)
        front_data  = parse_front(front_lines)
        front_data["source_file"] = os.path.basename(front_file)
    else:
        print(f"⚠️  Front file not found: {front_file}")

    if back_file and os.path.exists(back_file):
        print(f"🔍 OCR back page:  {back_file}")
        back_lines = get_ocr_lines(back_file)
        back_data  = parse_back(back_lines)
        back_data["source_file"] = os.path.basename(back_file)
    else:
        print(f"⚠️  Back file not found: {back_file}")

    print_results(front_data, back_data)