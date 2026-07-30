from signed_archive.models.config import TSAServer, TSAConfiguration


DEFAULT_TSA_SERVERS = [
    TSAServer(
        url="http://tss.accv.es:8318/tsa",
        label="ACCV - Comunidad Valenciana (ISTEC)",
        certificate_url="https://www.accv.es/fileadmin/Archivos/certificados/tsa1accv2016.cer",
        enabled=True,
    ),
    TSAServer(
        url="https://freetsa.org/tsr",
        label="FreeTSA",
        enabled=True,
    ),
    TSAServer(
        url="http://timestamp.digicert.com",
        label="DigiCert",
        enabled=True,
    ),
    TSAServer(
        url="http://timestamp.sectigo.com",
        label="Sectigo",
        enabled=True,
    ),
]


DEFAULT_CONFIG = TSAConfiguration(
    servers=DEFAULT_TSA_SERVERS,
    min_servers_required=1,
    request_timeout_seconds=30,
    max_retries=3,
    retry_backoff_base_seconds=2.0,
    clock_skew_warning_threshold_seconds=5.0,
)
