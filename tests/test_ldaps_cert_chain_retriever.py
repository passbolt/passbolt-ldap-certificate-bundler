import os
import sys

# Add project root to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from ldaps_cert_chain_retriever import validate_certificate_chain

GOOGLE_PEM_PATH = os.path.join(os.path.dirname(__file__), "google-ldap.pem")

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
