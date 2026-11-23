import pytest
from app.crypto.ciphers import CryptoEngine
from app.crypto.keywrap import KeyWrapManager

def test_aes_encryption_decryption_roundtrip():
    """Test AES-128-CBC encryption and decryption with PKCS7 padding."""
    plaintext = b"Capstone Secret Data: Student Records 2026"
    key, iv, hmac_key = CryptoEngine.generate_keys_and_iv("AES-128-CBC")

    assert len(key) == 16
    assert len(iv) == 16
    assert len(hmac_key) == 32

    ciphertext = CryptoEngine.encrypt(plaintext, "AES-128-CBC", key, iv)
    assert ciphertext != plaintext

    decrypted = CryptoEngine.decrypt(ciphertext, "AES-128-CBC", key, iv)
    assert decrypted == plaintext


def test_blowfish_encryption_decryption_roundtrip():
    """Test Blowfish-CBC encryption and decryption with PKCS7 padding."""
    plaintext = b"Financial Transactions & Encrypted Medical History"
    key, iv, hmac_key = CryptoEngine.generate_keys_and_iv("Blowfish-CBC")

    assert len(key) == 16
    assert len(iv) == 8
    assert len(hmac_key) == 32

    ciphertext = CryptoEngine.encrypt(plaintext, "Blowfish-CBC", key, iv)
    assert ciphertext != plaintext

    decrypted = CryptoEngine.decrypt(ciphertext, "Blowfish-CBC", key, iv)
    assert decrypted == plaintext


def test_key_and_iv_uniqueness():
    """Verify keys and IVs are uniquely generated on each call."""
    k1, iv1, h1 = CryptoEngine.generate_keys_and_iv("AES-128-CBC")
    k2, iv2, h2 = CryptoEngine.generate_keys_and_iv("AES-128-CBC")

    assert k1 != k2
    assert iv1 != iv2
    assert h1 != h2


def test_hmac_tampering_rejection():
    """Verify that tampering with ciphertext causes HMAC verification failure."""
    plaintext = b"Confidential Report"
    key, iv, hmac_key = CryptoEngine.generate_keys_and_iv("AES-128-CBC")

    pkg = CryptoEngine.create_encrypted_package(
        data_bytes=plaintext,
        transfer_id="tr-test1234",
        algorithm="AES-128-CBC",
        key=key,
        iv=iv,
        hmac_key=hmac_key
    )

    # Valid package passes HMAC
    valid = CryptoEngine.verify_hmac(
        hmac_key=hmac_key,
        expected_hmac_hex=pkg["hmac_tag"],
        version=pkg["version"],
        transfer_id=pkg["transfer_id"],
        algorithm=pkg["algorithm"],
        iv_b64=pkg["iv"],
        ciphertext_b64=pkg["ciphertext"]
    )
    assert valid is True

    # Tampered ciphertext fails HMAC
    tampered_ciphertext = pkg["ciphertext"][:-2] + ("AA" if pkg["ciphertext"][-2:] != "AA" else "BB")
    invalid = CryptoEngine.verify_hmac(
        hmac_key=hmac_key,
        expected_hmac_hex=pkg["hmac_tag"],
        version=pkg["version"],
        transfer_id=pkg["transfer_id"],
        algorithm=pkg["algorithm"],
        iv_b64=pkg["iv"],
        ciphertext_b64=tampered_ciphertext
    )
    assert invalid is False


def test_key_wrapping_and_unwrapping():
    """Test PBKDF2 + AES-256-GCM key wrapping and unwrapping."""
    password = "SuperStrongPassword2026!"
    transfer_id = "tr-test-wrap"
    algorithm = "AES-128-CBC"
    key, iv, hmac_key = CryptoEngine.generate_keys_and_iv(algorithm)

    wrapped_pkg = KeyWrapManager.wrap_keys(
        password=password,
        transfer_id=transfer_id,
        algorithm=algorithm,
        encryption_key=key,
        iv=iv,
        hmac_key=hmac_key
    )

    assert "salt" in wrapped_pkg
    assert "nonce" in wrapped_pkg
    assert "tag" in wrapped_pkg
    assert "ciphertext" in wrapped_pkg

    # Successful unwrap
    unwrapped = KeyWrapManager.unwrap_keys(password, wrapped_pkg)
    assert unwrapped["encryption_key"] == key
    assert unwrapped["iv"] == iv
    assert unwrapped["hmac_key"] == hmac_key
    assert unwrapped["algorithm"] == algorithm


def test_wrong_password_unwrapping_rejection():
    """Verify wrong password raises authentication failure without leaking secrets."""
    password = "CorrectPassword123"
    wrong_password = "WrongPassword999"
    transfer_id = "tr-test-fail"
    algorithm = "Blowfish-CBC"
    key, iv, hmac_key = CryptoEngine.generate_keys_and_iv(algorithm)

    wrapped_pkg = KeyWrapManager.wrap_keys(
        password=password,
        transfer_id=transfer_id,
        algorithm=algorithm,
        encryption_key=key,
        iv=iv,
        hmac_key=hmac_key
    )

    with pytest.raises(ValueError) as excinfo:
        KeyWrapManager.unwrap_keys(wrong_password, wrapped_pkg)
    assert "Authentication failed" in str(excinfo.value)
