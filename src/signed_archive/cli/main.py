import os
from pathlib import Path
from typing import Optional

import typer

from signed_archive.cli.archive import _run_archive_pipeline
from signed_archive.cli.config import config_app
from signed_archive.cli.verify import verify_command

app = typer.Typer(
    name="signed-archive",
    help="TSA Sign & Archive CLI — timestamp, archive, and generate eIDAS-compliant reports",
    invoke_without_command=True,
    no_args_is_help=True,
)


def _env_or_default(env_var: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(env_var, default)


@app.command("archive")
def archive_command(
    input_dir: Path = typer.Option(
        ..., "--input", "-i", help="Directory to archive", exists=True, dir_okay=True
    ),
    output_dir: Path = typer.Option(
        Path.cwd(), "--output", "-o", help="Output directory for archive and reports"
    ),
    cert: Optional[Path] = typer.Option(
        None, "--cert", "-c", help="X.509 certificate file (PEM or P12/PFX) for signing"
    ),
    cert_key: Optional[Path] = typer.Option(
        None, "--cert-key", "-k", help="Private key file (PEM). Required if --cert is PEM"
    ),
    cert_password: Optional[str] = typer.Option(
        None, "--cert-password", "-p", help="Password for P12/PFX certificate or encrypted private key"
    ),
    tsa_config: Optional[Path] = typer.Option(
        None, "--tsa-config", help="Path to TSA config YAML file"
    ),
    skip_ffmpeg_meta: bool = typer.Option(
        False, "--skip-ffmpeg-meta", help="Skip ffmpeg metadata extraction"
    ),
    max_retries: Optional[int] = typer.Option(
        None, "--max-retries", help="Max TSA request retries per server"
    ),
    timeout: Optional[int] = typer.Option(
        None, "--timeout", help="TSA request timeout in seconds"
    ),
    no_sign: bool = typer.Option(
        False, "--no-sign", help="Skip digital signing of report and archive"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Compute hashes and metadata only, do not create archive"
    ),
) -> int:
    cert_path = cert or _parse_path_env("SIGNED_ARCHIVE_CERT")
    cert_key_path = cert_key or _parse_path_env("SIGNED_ARCHIVE_CERT_KEY")
    cert_pw = cert_password or _env_or_default("SIGNED_ARCHIVE_CERT_PASSWORD")
    tsa_cfg = tsa_config or _parse_path_env("SIGNED_ARCHIVE_TSA_CONFIG")
    skip_ffmpeg = skip_ffmpeg_meta or _parse_bool_env("SIGNED_ARCHIVE_SKIP_FFMPEG")

    if not no_sign and not cert_path:
        typer.echo("Warning: No certificate provided. Use --no-sign to skip signing or provide --cert.", err=True)

    return _run_archive_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        cert_path=cert_path,
        cert_key_path=cert_key_path,
        cert_password=cert_pw,
        tsa_config_path=tsa_cfg,
        skip_ffmpeg_meta=skip_ffmpeg,
        max_retries=max_retries,
        timeout=timeout,
        no_sign=no_sign or (not cert_path),
        dry_run=dry_run,
    )


@app.command("verify")
def verify_cmd(
    archive: Path = typer.Option(
        ..., "--archive", "-a", help="Path to the ZIP archive", exists=True, readable=True
    ),
    report: Path = typer.Option(
        ..., "--report", "-r", help="Path to the signed report PDF", exists=True, readable=True
    ),
    verify_tsa_certs: bool = typer.Option(
        False, "--verify-tsa-certs", help="Also verify TSA certificates against EUTL"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Write verification report to file"
    ),
    format: str = typer.Option(
        "text", "--format", help="Output format: text or json"
    ),
) -> None:
    raise typer.Exit(verify_command(archive, report, verify_tsa_certs, output, format))


app.add_typer(config_app, name="config")


def _parse_path_env(var: str) -> Optional[Path]:
    val = os.environ.get(var)
    if val:
        p = Path(val)
        if p.exists():
            return p
    return None


def _parse_bool_env(var: str) -> bool:
    val = os.environ.get(var, "").lower()
    return val in ("1", "true", "yes")


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
):
    if version:
        typer.echo("signed-archive v0.1.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()
