import io
import json
import pytest
from app import create_app
from app.database import db
from app.models import Transfer, ReceiverSession
import openpyxl

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def create_sample_excel_bytes():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Name", "Department", "Salary"])
    ws.append([101, "Alice", "Security", 95000])
    ws.append([102, "Bob", "Cryptography", 88000])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()

def test_full_workflow_and_state_machine(client):
    """
    Test complete sender-to-receiver workflow:
    1. Create transfer with Excel upload
    2. Scan QR -> state QR_OK
    3. Verify password -> state KEY_SHOWN
    4. Attempt decrypt BEFORE eye verification -> 403 Forbidden!
    5. Enroll eye -> state EYE_ENROLLED
    6. Verify live eye -> state EYE_VERIFIED
    7. Decrypt file -> state DATA_VIEW (succeeds)
    """
    excel_bytes = create_sample_excel_bytes()
    data = {
        "file": (io.BytesIO(excel_bytes), "sample.xlsx"),
        "algorithm": "AES-128-CBC",
        "password": "ValidPassword2026!"
    }
    # 1. Create transfer
    res = client.post("/api/transfers", data=data, content_type="multipart/form-data")
    assert res.status_code == 201
    transfer_data = res.get_json()
    transfer_id = transfer_data["transfer_id"]

    # 2. Scan QR
    scan_res = client.post(f"/api/transfers/{transfer_id}/scan")
    assert scan_res.status_code == 200
    session_data = scan_res.get_json()
    token = session_data["session_token"]
    assert session_data["current_state"] == "QR_OK"

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Attempt decrypt directly -> 403 Forbidden
    early_decrypt = client.post(
        f"/api/transfers/{transfer_id}/decrypt",
        headers=headers,
        json={"password": "ValidPassword2026!"}
    )
    assert early_decrypt.status_code == 403

    # 4. Password verification
    pwd_res = client.post(
        f"/api/transfers/{transfer_id}/password",
        headers=headers,
        json={"password": "ValidPassword2026!"}
    )
    assert pwd_res.status_code == 200
    pwd_data = pwd_res.get_json()
    assert pwd_data["current_state"] == "KEY_SHOWN"
    assert "masked_key" in pwd_data

    # 5. Enroll eye
    # Create 5 synthetic frames (non-empty strings)
    mock_frames = ["frame_data_placeholder" for _ in range(6)]
    enroll_res = client.post(
        f"/api/transfers/{transfer_id}/eye/enroll",
        headers=headers,
        json={"frames": mock_frames}
    )
    assert enroll_res.status_code == 200
    assert enroll_res.get_json()["current_state"] == "EYE_ENROLLED"

    # 6. Verify live eye with blink sequence
    verify_res = client.post(
        f"/api/transfers/{transfer_id}/eye/verify",
        headers=headers,
        json={
            "frames": mock_frames,
            # Sequence exhibiting closure (< 0.17) and reopening (> 0.22)
            "openness_history": [0.24, 0.23, 0.14, 0.12, 0.23, 0.25]
        }
    )
    assert verify_res.status_code == 200
    assert verify_res.get_json()["current_state"] == "EYE_VERIFIED"

    # 7. Final Decryption
    final_decrypt = client.post(
        f"/api/transfers/{transfer_id}/decrypt",
        headers=headers,
        json={"password": "ValidPassword2026!"}
    )
    assert final_decrypt.status_code == 200
    decrypted_body = final_decrypt.get_json()
    assert decrypted_body["current_state"] == "DATA_VIEW"
    assert "structured_data" in decrypted_body
    assert decrypted_body["structured_data"]["total_rows"] == 2


def test_password_lockout(client):
    """Test 5 failed passwords trigger 15-minute lockout."""
    excel_bytes = create_sample_excel_bytes()
    res = client.post("/api/transfers", data={
        "file": (io.BytesIO(excel_bytes), "sample.xlsx"),
        "algorithm": "Blowfish-CBC",
        "password": "RealPassword123"
    }, content_type="multipart/form-data")
    transfer_id = res.get_json()["transfer_id"]

    scan_res = client.post(f"/api/transfers/{transfer_id}/scan")
    token = scan_res.get_json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4 wrong password attempts
    for _ in range(4):
        f_res = client.post(f"/api/transfers/{transfer_id}/password", headers=headers, json={"password": "Wrong"})
        assert f_res.status_code == 401

    # 5th attempt -> triggers 403 lockout!
    lock_res = client.post(f"/api/transfers/{transfer_id}/password", headers=headers, json={"password": "Wrong"})
    assert lock_res.status_code == 403
    assert "locked" in lock_res.get_json()["error"].lower()
