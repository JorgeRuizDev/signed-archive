from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from endesive import pdf as endesive_pdf


def load_certificate_and_key(
    cert_path: Path,
    key_path: Path | None = None,
    password: str | None = None,
) -> tuple[bytes, bytes]:
    cert_data = cert_path.read_bytes()
    suffix = cert_path.suffix.lower()

    if suffix in (".p12", ".pfx"):
        pwd = password.encode() if password else b""
        _, cert, key = pkcs12.load_key_and_certificates(cert_data, pwd)
        if cert is None or key is None:
            raise ValueError("Failed to load certificate and key from P12/PFX file")
        return cert.public_bytes(serialization.Encoding.DER), key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    else:
        cert_obj = serialization.load_pem_x509_certificate(cert_data)
        cert_der = cert_obj.public_bytes(serialization.Encoding.DER)

        if key_path:
            key_data = key_path.read_bytes()
            pwd = password.encode() if password else None
            key_obj = serialization.load_pem_private_key(key_data, password=pwd)
        else:
            raise ValueError("Private key file (--cert-key) required for PEM certificates")

        key_der = key_obj.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        return cert_der, key_der


def sign_pdf(
    pdf_path: Path,
    cert_der: bytes,
    key_der: bytes,
    output_path: Path | None = None,
) -> Path:
    output_path = output_path or pdf_path
    pdf_data = pdf_path.read_bytes()

    dct = {
        "sigflags": 3,
        "contact": "",
        "location": "",
        "signingdate": b"",
        "reason": "TSA Sign & Archive Report Signature",
    }

    signed_data = endesive_pdf.cms.sign(pdf_data, dct, key_der, cert_der, [])
    output_path.write_bytes(signed_data)
    return output_path


def sign_zip_cades(
    zip_path: Path,
    cert_der: bytes,
    key_der: bytes,
    output_path: Path | None = None,
) -> Path:
    from cryptography.hazmat.primitives.serialization import load_der_private_key
    from cryptography.x509 import load_der_x509_certificate
    from asn1crypto import cms as asn1_cms

    from signed_archive.services.hasher import hash_file

    sha256, _ = hash_file(zip_path)

    sig_path = output_path or Path(str(zip_path) + ".sig")

    cert = load_der_x509_certificate(cert_der)
    key = load_der_private_key(key_der, password=None)

    signature = key.sign(
        sha256.encode(),
        hashes.SHA256(),
    )

    sig_path.write_bytes(signature)
    return sig_path
