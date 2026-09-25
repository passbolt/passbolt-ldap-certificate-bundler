import os
import sys

# Add project root to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from ldaps_cert_chain_retriever import validate_certificate_chain

GOOGLE_PEM_PATH = os.path.join(os.path.dirname(__file__), "google-ldap.pem")


def _make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _make_cert_der(subject_cn, issuer_cn, public_key, signing_key):
    """Build a DER certificate with the given names, key, and signing key."""
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_cn)]))
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .sign(signing_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.DER)


@pytest.mark.skipif(not os.path.exists(GOOGLE_PEM_PATH), reason="google-ldap.pem not present")
def test_google_ldap_chain_is_valid():
    with open(GOOGLE_PEM_PATH, "r") as f:
        pem_data = f.read()

    # Split full PEM chain into individual certs
    pem_blocks = []
    current_cert = []
    in_cert = False

    for line in pem_data.splitlines():
        if "-----BEGIN CERTIFICATE-----" in line:
            in_cert = True
            current_cert = [line]
        elif "-----END CERTIFICATE-----" in line:
            current_cert.append(line)
            pem_blocks.append("\n".join(current_cert))
            in_cert = False
        elif in_cert:
            current_cert.append(line)

    # Load and convert each cert to DER
    cert_ders = [
        x509.load_pem_x509_certificate(pem.encode(), default_backend()).public_bytes(
            encoding=serialization.Encoding.DER
        )
        for pem in pem_blocks
    ]

    # Run validation
    is_valid, msg = validate_certificate_chain(cert_ders)
    assert is_valid, f"Google LDAPS cert chain should be valid, but got: {msg}"


def test_forged_chain_is_rejected():
    """A leaf whose issuer DN matches the CA but is NOT signed by the CA key
    must be rejected (PB-54784, CWE-295: names alone are not a chain)."""
    ca_key = _make_key()
    leaf_key = _make_key()
    ca_der = _make_cert_der("Evil CA", "Evil CA", ca_key.public_key(), ca_key)
    # Leaf claims to be issued by "Evil CA" but is signed by its own key
    forged_leaf_der = _make_cert_der("ldap.example.com", "Evil CA", leaf_key.public_key(), leaf_key)

    is_valid, msg = validate_certificate_chain([forged_leaf_der, ca_der])
    assert not is_valid, f"Forged chain must be rejected, but got: {msg}"
    assert "not signed by" in msg


def test_fake_self_signed_certificate_is_rejected():
    """A certificate with issuer == subject that is signed by a DIFFERENT key
    must not be reported as a valid self-signed certificate."""
    real_key = _make_key()
    other_key = _make_key()
    fake_der = _make_cert_der("Root CA", "Root CA", real_key.public_key(), other_key)

    is_valid, msg = validate_certificate_chain([fake_der])
    assert not is_valid, f"Fake self-signed certificate must be rejected, but got: {msg}"


def test_genuine_self_signed_certificate_is_valid():
    """A genuinely self-signed certificate (common for internal LDAP servers)
    must still validate."""
    key = _make_key()
    self_signed_der = _make_cert_der("ldap.internal", "ldap.internal", key.public_key(), key)

    is_valid, msg = validate_certificate_chain([self_signed_der])
    assert is_valid, f"Genuine self-signed certificate should be valid, but got: {msg}"


def test_internal_pki_chain_is_valid():
    """A leaf genuinely signed by a self-signed root CA (internal PKI)
    must still validate."""
    ca_key = _make_key()
    leaf_key = _make_key()
    ca_der = _make_cert_der("Internal Root CA", "Internal Root CA", ca_key.public_key(), ca_key)
    leaf_der = _make_cert_der("ldap.internal", "Internal Root CA", leaf_key.public_key(), ca_key)

    is_valid, msg = validate_certificate_chain([leaf_der, ca_der])
    assert is_valid, f"Internal PKI chain should be valid, but got: {msg}"
    assert "signatures verified" in msg


def test_duplicate_self_signed_roots_are_tolerated():
    """Servers sometimes send extra self-signed roots with the same name
    (e.g. an old and a renewed CA certificate). A genuinely self-signed
    certificate must not fail the chain just because the next certificate
    shares its name but not its key."""
    old_key = _make_key()
    new_key = _make_key()
    old_root_der = _make_cert_der("Root CA", "Root CA", old_key.public_key(), old_key)
    new_root_der = _make_cert_der("Root CA", "Root CA", new_key.public_key(), new_key)

    is_valid, msg = validate_certificate_chain([old_root_der, new_root_der])
    assert is_valid, f"Duplicate self-signed roots should be tolerated, but got: {msg}"
    assert "self-signed" in msg
