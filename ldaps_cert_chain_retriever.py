#!/usr/bin/env python3

"""
LDAPS Certificate Chain Retriever

This tool retrieves SSL/TLS certificate chains from LDAPS servers for use with Passbolt.
It supports both standard certificate chains and self-signed certificates, making it
suitable for various LDAP server configurations in enterprise environments.

Key features:
- Retrieves complete certificate chains from LDAPS servers
- Handles self-signed certificates commonly used in internal LDAP servers
- Validates certificate chain integrity
- Supports both PEM and DER output formats
- Provides detailed debugging information
- Compatible with Passbolt's LDAPS configuration requirements

Usage:
1. Retrieve certificates: python3 ldaps_cert_chain_retriever.py --server ldap.example.com
2. Save to file: python3 ldaps_cert_chain_retriever.py --server ldap.example.com --output ldap-certs.pem
3. Configure Passbolt: Use the generated certificate bundle in your Passbolt LDAPS configuration

For more information on Passbolt LDAPS setup, visit:
https://www.passbolt.com/docs/hosting/configure/ldap/ldaps/
"""

import sys
import subprocess
import argparse
import logging
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# ANSI color codes for better readability in terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def setup_colored_logging():
    """Setup colored logging for better readability of debug output"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(message)s'
    )

def print_colored(message, color=Colors.ENDC):
    """Print a colored message to the terminal"""
    print(f"{color}{message}{Colors.ENDC}")

def is_self_signed(cert):
    """
    Check if a certificate is self-signed by comparing issuer and subject.

    This is important for enterprise LDAP servers that often use self-signed
    certificates for internal PKI.
    """
    return cert.issuer == cert.subject

def print_certificate_info(cert_data, is_root=False):
    """
    Print human-readable certificate information.

    Displays certificate details in a format useful for Passbolt administrators
    to verify the correct certificates were retrieved.

    Args:
        cert_data (bytes): The certificate data in DER format
        is_root (bool): Whether this is a root certificate
    """
    cert = x509.load_der_x509_certificate(cert_data, default_backend())

    # Get common name from subject
    subject_cn = None
    for name in cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME):
        subject_cn = name.value
        break

    # Get common name from issuer
    issuer_cn = None
    for name in cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME):
        issuer_cn = name.value
        break

    cert_type = "Root Certificate" if is_root else "Certificate"
    if is_self_signed(cert):
        cert_type = "Self-signed " + cert_type

    print_colored(f"\n{cert_type}:", Colors.BOLD)
    print_colored(f"  Subject: {subject_cn} | Issuer: {issuer_cn}", Colors.BLUE)
    print_colored(f"  Valid: {cert.not_valid_before_utc.strftime('%Y-%m-%d')} to {cert.not_valid_after_utc.strftime('%Y-%m-%d')}", Colors.GREEN)
    print_colored(f"  Serial: {cert.serial_number}", Colors.YELLOW)

def validate_certificate_chain(cert_ders):
    """
    Validate the certificate chain is complete and properly ordered.

    Handles various certificate scenarios commonly found in enterprise LDAP setups:
    - Standard certificate chains from public CAs
    - Self-signed certificates (common in test/dev environments)
    - Internal PKI chains with self-signed root CAs

    Returns:
        tuple: (bool, str) - (is_valid, validation_message)
    """
    if not cert_ders:
        return False, "No certificates found in chain"

    try:
        # Load all certificates
        certs = [x509.load_der_x509_certificate(cert, default_backend())
                for cert in cert_ders]

        # Check if single self-signed certificate
        if len(certs) == 1 and is_self_signed(certs[0]):
            return True, "Valid self-signed certificate"

        # Check if each certificate's issuer matches the subject of the next certificate
        for i in range(len(certs) - 1):
            cert = certs[i]
            issuer = certs[i + 1]

            # Get issuer and subject DNs
            cert_issuer_dn = cert.issuer
            next_cert_subject_dn = issuer.subject

            if cert_issuer_dn != next_cert_subject_dn:
                # Check if current certificate is self-signed
                if is_self_signed(cert):
                    return True, f"Chain contains self-signed certificate at position {i}"
                return False, f"Certificate chain broken at position {i}: issuer does not match next certificate's subject"

        # Check if the last certificate is self-signed (root CA)
        if is_self_signed(certs[-1]):
            return True, "Certificate chain is valid and ends with self-signed root CA"

        return True, "Certificate chain is valid and properly ordered"

    except Exception as e:
        return False, f"Error validating certificate chain: {str(e)}"

def get_ldap_ssl_certificates(ldap_server_host, port=636, debug=False):
    """
    Retrieve SSL certificates from an LDAPS server using OpenSSL.

    This function connects to the LDAPS server and retrieves its certificate chain,
    handling both standard and self-signed certificates. The certificates can then
    be used in Passbolt's LDAPS configuration.

    Args:
        ldap_server_host (str): The LDAP server hostname
        port (int): The LDAPS port (default: 636)
        debug (bool): Enable detailed debug output

    Returns:
        dict: Dictionary containing:
            - peer_certificate: The server's certificate
            - peer_certificate_chain: List of CA certificates in the chain
    """
    if debug:
        setup_colored_logging()
        print_colored(f"\nConnecting to {ldap_server_host}:{port}", Colors.BLUE)

    try:
        # First, try to get the certificate using openssl s_client
        cmd = [
            'openssl', 's_client',
            '-connect', f'{ldap_server_host}:{port}',
            '-showcerts',
            '-servername', ldap_server_host
        ]

        if debug:
            print_colored(f"Running command: {' '.join(cmd)}", Colors.YELLOW)

        # Run OpenSSL command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )

        # Send empty input and get output
        stdout, stderr = process.communicate(input=b'\n')
        output = stdout.decode('utf-8')

        if debug and stderr:
            stderr_output = stderr.decode('utf-8')
            print_colored("\nOpenSSL Connection Details:", Colors.BOLD)
            for line in stderr_output.splitlines():
                if line.strip() and not line.startswith('DONE'):
                    if 'verify return:1' in line:
                        print_colored(f"  {line}", Colors.GREEN)
                    else:
                        print_colored(f"  {line}", Colors.BLUE)

        # Parse the certificates from the output
        certs = []
        current_cert = []
        in_cert = False

        for line in output.splitlines():
            if '-----BEGIN CERTIFICATE-----' in line:
                in_cert = True
                current_cert = [line]
            elif '-----END CERTIFICATE-----' in line:
                in_cert = False
                current_cert.append(line)
                certs.append('\n'.join(current_cert))
            elif in_cert:
                current_cert.append(line)

        if not certs:
            if debug:
                print_colored("\nRaw output from OpenSSL:", Colors.RED)
                print_colored(output, Colors.RED)
            raise Exception("No certificates found in the server response")

        if debug:
            print_colored(f"\nFound {len(certs)} certificates in chain", Colors.GREEN)

        # Convert PEM to DER for consistency with the rest of the code
        cert_ders = []
        for cert_pem in certs:
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
            cert_ders.append(cert.public_bytes(serialization.Encoding.DER))

        # Validate the certificate chain
        is_valid, validation_message = validate_certificate_chain(cert_ders)
        if debug:
            if is_valid:
                print_colored(f"\nCertificate Chain Validation: {validation_message}", Colors.GREEN)
            else:
                print_colored(f"\nCertificate Chain Validation: {validation_message}", Colors.RED)

        # Print certificate information in debug mode
        if debug:
            for i, cert_der in enumerate(cert_ders):
                is_root = (i == len(cert_ders) - 1)
                print_certificate_info(cert_der, is_root)

        return {
            'peer_certificate': cert_ders[0],
            'peer_certificate_chain': cert_ders[1:] if len(cert_ders) > 1 else []
        }

    except subprocess.CalledProcessError as e:
        if debug:
            print_colored(f"\nOpenSSL command failed: {e}", Colors.RED)
        raise
    except Exception as e:
        if debug:
            print_colored(f"\nUnexpected error: {str(e)}", Colors.RED)
        raise

def format_certificate(cert_data, format='pem'):
    """
    Format certificate data in the specified format.

    Passbolt typically expects certificates in PEM format, but DER is also
    supported for special cases.

    Args:
        cert_data (bytes): Raw certificate data in DER format
        format (str): Output format ('pem' or 'der')

    Returns:
        str/bytes: Formatted certificate
    """
    cert = x509.load_der_x509_certificate(cert_data, default_backend())
    if format == 'pem':
        return cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    elif format == 'der':
        return cert.public_bytes(serialization.Encoding.DER)
    else:
        raise ValueError(f"Unsupported format: {format}")

def main():
    parser = argparse.ArgumentParser(
        description='Retrieve SSL certificates from an LDAPS server for Passbolt configuration',
        epilog='For more information on Passbolt LDAPS setup, visit: https://www.passbolt.com/docs/hosting/configure/ldap/ldaps/'
    )
    parser.add_argument('--server', default='host.yourldapdomain.com',
                      help='LDAP server hostname (default: host.yourldapdomain.com)')
    parser.add_argument('--port', type=int, default=636,
                      help='LDAPS port (default: 636)')
    parser.add_argument('--test', action='store_true',
                      help='Use test server (ldap.google.com with fallback to ldap.forumsys.com)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug output')
    parser.add_argument('--format', choices=['pem', 'der'],
                      default='pem',
                      help='Output format (default: pem)')
    parser.add_argument('--output', type=str,
                      help='Output file path (default: stdout)')

    # If no arguments provided, show help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.test:
        # Try Google's LDAP server first, fall back to Forumsys if it fails
        test_servers = ['ldap.google.com', 'ldap.forumsys.com']
        last_error = None

        for server in test_servers:
            try:
                print_colored(f"Trying test server: {server}", Colors.BLUE)
                args.server = server
                certificates = get_ldap_ssl_certificates(args.server, args.port, args.debug)

                # Format and combine certificates
                bundle = format_certificate(certificates['peer_certificate'], args.format)
                for cert in certificates['peer_certificate_chain']:
                    if args.format == 'pem':
                        bundle += format_certificate(cert, args.format)
                    else:
                        bundle += cert

                if args.output:
                    with open(args.output, 'wb' if args.format == 'der' else 'w') as f:
                        f.write(bundle)
                else:
                    print(bundle)
                return

            except Exception as e:
                last_error = e
                if args.debug:
                    print_colored(f"Failed to connect to {server}: {str(e)}", Colors.RED)
                continue

        # If we get here, all test servers failed
        print_colored(f"Error: All test servers failed. Last error: {str(last_error)}", Colors.RED)
        sys.exit(1)

    try:
        certificates = get_ldap_ssl_certificates(args.server, args.port, args.debug)

        # Format and combine certificates
        bundle = format_certificate(certificates['peer_certificate'], args.format)
        for cert in certificates['peer_certificate_chain']:
            if args.format == 'pem':
                bundle += format_certificate(cert, args.format)
            else:
                bundle += cert

        if args.output:
            with open(args.output, 'wb' if args.format == 'der' else 'w') as f:
                f.write(bundle)
        else:
            print(bundle)

    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        sys.exit(1)


if __name__ == '__main__':
    main()
