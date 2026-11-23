import io
import openpyxl
from app.crypto.excel_handler import ExcelHandler

def test_excel_to_csv_and_back():
    """Verify Excel to CSV conversion and round-trip reconstruction."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "Role", "Email"])
    ws.append(["Alice Smith", "Security Analyst", "alice@example.com"])
    ws.append(["Bob Jones", "Crypto Engineer", "bob@example.com"])

    buf = io.BytesIO()
    wb.save(buf)
    excel_bytes = buf.getvalue()

    # Validate Excel format
    assert ExcelHandler.validate_excel(excel_bytes, "records.xlsx") is True
    assert ExcelHandler.validate_excel(b"fake data", "records.xlsx") is False
    assert ExcelHandler.validate_excel(excel_bytes, "records.txt") is False

    # Convert to CSV
    csv_bytes = ExcelHandler.excel_to_csv(excel_bytes)
    assert b"Alice Smith" in csv_bytes
    assert b"Crypto Engineer" in csv_bytes

    # Convert to structured data
    structured = ExcelHandler.csv_to_structured_data(csv_bytes)
    assert structured["headers"] == ["Name", "Role", "Email"]
    assert structured["total_rows"] == 2
    assert structured["rows"][0]["Name"] == "Alice Smith"

    # Reconstruct Excel from CSV
    reconstructed_excel = ExcelHandler.csv_to_excel(csv_bytes)
    assert ExcelHandler.validate_excel(reconstructed_excel, "test.xlsx") is True
