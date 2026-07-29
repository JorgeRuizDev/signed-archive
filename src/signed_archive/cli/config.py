from pathlib import Path
from typing import Optional

import typer
import yaml

from signed_archive.config.defaults import DEFAULT_CONFIG
from signed_archive.config.loader import load_config, save_config, validate_config
from signed_archive.models.config import TSAServer


config_app = typer.Typer(help="Manage TSA configuration")


def _get_config_dir(input_dir: Path) -> Path:
    return (input_dir / ".signed_archive").resolve()


def _get_config_path(config_dir: Path) -> Path:
    return config_dir / "config.yml"


@config_app.command("init")
def config_init(
    input_dir: Path = typer.Option(
        Path.cwd(), "--input", "-i", help="Directory containing .signed_archive/ folder"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config without confirmation"),
):
    config_dir = _get_config_dir(input_dir)
    config_path = _get_config_path(config_dir)

    if config_path.exists() and not force:
        typer.echo(f"Config already exists at {config_path}. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    save_config(DEFAULT_CONFIG, config_path)
    typer.echo(f"Default config created: {config_path}")


@config_app.command("show")
def config_show(
    input_dir: Path = typer.Option(
        Path.cwd(), "--input", "-i", help="Directory containing .signed_archive/ folder"
    ),
):
    config_path = _get_config_path(_get_config_dir(input_dir))

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        typer.echo(f"Config not found. Run 'config init' first.", err=True)
        raise typer.Exit(2)

    typer.echo(f"Config file: {config_path}")
    typer.echo(f"Min servers required: {config.min_servers_required}")
    typer.echo(f"Request timeout: {config.request_timeout_seconds}s")
    typer.echo(f"Max retries: {config.max_retries}")
    typer.echo(f"Retry backoff base: {config.retry_backoff_base_seconds}s")
    typer.echo(f"Clock skew threshold: {config.clock_skew_warning_threshold_seconds}s")
    typer.echo("\nServers:")
    for i, server in enumerate(config.servers, 1):
        status = "enabled" if server.enabled else "disabled"
        typer.echo(f"  {i}. [{status}] {server.label}")
        typer.echo(f"     URL: {server.url}")
        if server.certificate_url:
            typer.echo(f"     Cert: {server.certificate_url}")


@config_app.command("add")
def config_add(
    url: str = typer.Argument(..., help="TSA server URL"),
    label: str = typer.Argument(..., help="Human-readable label"),
    input_dir: Path = typer.Option(
        Path.cwd(), "--input", "-i", help="Directory containing .signed_archive/ folder"
    ),
    certificate_url: Optional[str] = typer.Option(
        None, "--certificate-url", help="URL to download the TSA certificate"
    ),
):
    config_path = _get_config_path(_get_config_dir(input_dir))

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        typer.echo(f"Config not found. Run 'config init' first.", err=True)
        raise typer.Exit(2)

    if not url.startswith("http://") and not url.startswith("https://"):
        typer.echo(f"Error: Invalid URL '{url}'. Must start with http:// or https://", err=True)
        raise typer.Exit(2)

    new_server = TSAServer(url=url, label=label, certificate_url=certificate_url, enabled=True)
    config.servers.append(new_server)

    errors = validate_config(config)
    if errors:
        typer.echo("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors), err=True)
        raise typer.Exit(2)

    save_config(config, config_path)
    typer.echo(f"Added TSA server: {label} ({url})")


@config_app.command("remove")
def config_remove(
    identifier: str = typer.Argument(..., help="TSA server URL or label to remove"),
    input_dir: Path = typer.Option(
        Path.cwd(), "--input", "-i", help="Directory containing .signed_archive/ folder"
    ),
):
    config_path = _get_config_path(_get_config_dir(input_dir))

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        typer.echo(f"Config not found. Run 'config init' first.", err=True)
        raise typer.Exit(2)

    found = None
    for i, server in enumerate(config.servers):
        if server.url == identifier or server.label == identifier:
            found = i
            break

    if found is None:
        typer.echo(f"Server not found: {identifier}", err=True)
        raise typer.Exit(1)

    removed = config.servers.pop(found)
    save_config(config, config_path)
    typer.echo(f"Removed TSA server: {removed.label} ({removed.url})")
