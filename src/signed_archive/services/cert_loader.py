from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12

_PKCS12_EXTENSIONS = {".p12", ".pfx", ".pdoce"}


def load_certificate_and_key(
    cert_path: Path,
    key_path: Path | None = None,
    password: str | None = None,
) -> tuple[bytes, bytes]:
    cert_data = cert_path.read_bytes()
    suffix = cert_path.suffix.lower()

    if suffix in _PKCS12_EXTENSIONS:
        pwd = password.encode() if password else b""
        key, cert, _ = pkcs12.load_key_and_certificates(cert_data, pwd)
        if cert is None or key is None:
            raise ValueError("Failed to load certificate and key from P12/PFX file")
        return cert.public_bytes(serialization.Encoding.DER), key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    else:
        cert_obj = x509.load_pem_x509_certificate(cert_data)
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
