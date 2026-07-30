from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


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
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    sig_path.write_bytes(signature)
    return sig_path
