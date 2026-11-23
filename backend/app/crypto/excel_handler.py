import csv
import io
from typing import Tuple, List, Dict, Any
import openpyxl

class ExcelHandler:
    """Handles Excel workbook parsing, CSV conversion, and Excel reconstruction."""

    @staticmethod
    def validate_excel(file_bytes: bytes, filename: str) -> bool:
        """Validate filename extension and zip magic bytes for XLSX."""
        if not filename.lower().endswith(".xlsx"):
            return False
        # XLSX files are ZIP archives starting with PK\x03\x04
        if len(file_bytes) < 4 or file_bytes[:4] != b"PK\x03\x04":
            return False
        return True

    @classmethod
    def excel_to_csv(cls, excel_bytes: bytes) -> bytes:
        """
        Convert the active sheet of an Excel (.xlsx) file into UTF-8 CSV bytes.
        """
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True)
        sheet = wb.active

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        for row in sheet.iter_rows(values_only=True):
            # Convert None to empty string, and stringify other values
            clean_row = ["" if cell is None else str(cell) for cell in row]
            # Skip completely empty rows
            if any(cell != "" for cell in clean_row):
                writer.writerow(clean_row)

        csv_str = output.getvalue()
        return csv_str.encode("utf-8")

    @classmethod
    def csv_to_structured_data(cls, csv_bytes: bytes) -> Dict[str, Any]:
        """
        Parse CSV bytes into structured records for frontend table display.
        """
        csv_text = csv_bytes.decode("utf-8", errors="replace")
        f = io.StringIO(csv_text)
        reader = csv.reader(f)

        rows = list(reader)
        if not rows:
            return {"headers": [], "rows": [], "total_rows": 0}

        headers = rows[0]
        data_rows = rows[1:]

        # Create structured objects
        records: List[Dict[str, Any]] = []
        for row in data_rows:
            record: Dict[str, Any] = {}
            for i, header in enumerate(headers):
                record[header] = row[i] if i < len(row) else ""
            records.append(record)

        return {
            "headers": headers,
            "rows": records,
            "raw_rows": data_rows,
            "total_rows": len(records),
        }

    @classmethod
    def csv_to_excel(cls, csv_bytes: bytes) -> bytes:
        """
        Reconstruct an Excel (.xlsx) workbook from CSV bytes.
        """
        csv_text = csv_bytes.decode("utf-8", errors="replace")
        f = io.StringIO(csv_text)
        reader = csv.reader(f)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Decrypted Data"

        for row in reader:
            ws.append(row)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
