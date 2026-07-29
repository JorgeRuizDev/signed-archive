import hashlib
import time
from typing import Optional

import httpx
from asn1crypto import algos, cms, core, tsp, x509

from signed_archive.models.config import TSAConfiguration
from signed_archive.models.run_state import TSAStatus, TimestampSignature
from signed_archive.utils.timing import exponential_backoff


def _build_timestamp_request(file_hash: str, hash_algorithm: str = "sha256") -> bytes:
    hash_algo = algos.DigestAlgorithm()
    hash_algo["algorithm"] = algos.DigestAlgorithmId("sha256")
    hash_algo["parameters"] = core.Null()

    message_imprint = tsp.MessageImprint()
    message_imprint["hash_algorithm"] = hash_algo
    message_imprint["hashed_message"] = bytes.fromhex(file_hash)

    nonce = int.from_bytes(hashlib.sha256(str(time.time_ns()).encode()).digest()[:8], "big")

    req = tsp.TimeStampReq()
    req["version"] = 1
    req["message_imprint"] = message_imprint
    req["nonce"] = nonce
    req["cert_req"] = True

    return req.dump()


def _parse_timestamp_response(response_data: bytes) -> cms.ContentInfo:
    try:
        resp = tsp.TimeStampResp.load(response_data)
        status = resp["status"]["status"]
        if status.native != "granted" and status.native != 0:
            raise ValueError(f"TSA returned non-granted status: {status.native}")
        return resp["time_stamp_token"]
    except Exception as e:
        raise ValueError(f"Failed to parse TSA response: {e}")


def _extract_token_info(token: cms.ContentInfo) -> dict:
    signed_data = token["content"]
    signer_info = signed_data["signer_infos"][0]
    signed_attrs = signer_info["signed_attrs"]

    signing_time = None
    for attr in signed_attrs:
        if attr["type"].dotted == "1.2.840.113549.1.9.5":
            signing_time = attr["values"][0].native
            break

    if signing_time and hasattr(signing_time, "isoformat"):
        signing_time = signing_time.isoformat()

    certs = signed_data.get("certificates", [])
    tsa_cert = None
    for c in certs:
        try:
            tsa_cert = c.chosen
            break
        except Exception:
            pass

    subject = ""
    issuer = ""
    serial = 0
    if tsa_cert and hasattr(tsa_cert, "subject"):
        try:
            subject = str(tsa_cert.subject.human_friendly)
        except Exception:
            subject = str(tsa_cert.subject.native)
    if tsa_cert and hasattr(tsa_cert, "issuer"):
        try:
            issuer = str(tsa_cert.issuer.human_friendly)
        except Exception:
            issuer = str(tsa_cert.issuer.native)
    if tsa_cert and hasattr(tsa_cert, "serial_number"):
        serial = tsa_cert.serial_number.native

    digest_algo = signer_info.get("digest_algorithm", {})
    digest_oid = ""
    try:
        digest_oid = digest_algo["algorithm"].dotted
    except Exception:
        digest_oid = str(digest_algo)

    return {
        "signing_time": signing_time or "",
        "subject": subject,
        "issuer": issuer,
        "serial": serial,
        "digest_algorithm": digest_oid,
    }


def query_tsa_server(
    server_url: str,
    server_label: str,
    file_hash: str,
    config: TSAConfiguration,
) -> TimestampSignature:
    req_data = _build_timestamp_request(file_hash)

    last_error = None
    for delay in exponential_backoff(config.retry_backoff_base_seconds, config.max_retries):
        try:
            response = httpx.post(
                server_url,
                content=req_data,
                headers={"Content-Type": "application/timestamp-query"},
                timeout=config.request_timeout_seconds,
            )
            response.raise_for_status()

            token = _parse_timestamp_response(response.content)
            info = _extract_token_info(token)

            return TimestampSignature(
                tsa_server_url=server_url,
                tsa_server_label=server_label,
                signing_time=info["signing_time"],
                token_hex=token.dump().hex(),
                serial_number=info["serial"],
                tsa_cert_subject=info["subject"],
                tsa_cert_issuer=info["issuer"],
                digest_algorithm=info["digest_algorithm"],
                status=TSAStatus.SUCCESS,
            )
        except httpx.TimeoutException:
            last_error = "timeout"
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}"
        except Exception as e:
            last_error = str(e)

        if delay > 0:
            time.sleep(delay)

    if last_error:
        error_type = TSAStatus.TIMEOUT if "timeout" in str(last_error).lower() else TSAStatus.ERROR
        return TimestampSignature(
            tsa_server_url=server_url,
            tsa_server_label=server_label,
            signing_time="",
            token_hex="",
            serial_number=0,
            tsa_cert_subject="",
            tsa_cert_issuer="",
            digest_algorithm="",
            status=error_type,
            error_message=str(last_error),
        )


def _parse_hex_token(token_hex: str) -> Optional[cms.ContentInfo]:
    if not token_hex:
        return None
    try:
        return cms.ContentInfo.load(bytes.fromhex(token_hex))
    except Exception:
        return None


def verify_tsa_timestamp(token_hex: str, expected_hash: str) -> bool:
    token = _parse_hex_token(token_hex)
    if token is None:
        return False

    try:
        signed_data = token["content"]
        signer_info = signed_data["signer_infos"][0]
        signed_attrs = signer_info["signed_attrs"]

        for attr in signed_attrs:
            if attr["type"].dotted == "1.2.840.113549.1.9.4":
                message_digest = attr["values"][0].native
                actual_digest = hashlib.sha256(bytes.fromhex(expected_hash)).digest()
                return message_digest == actual_digest
        return False
    except Exception:
        return False
