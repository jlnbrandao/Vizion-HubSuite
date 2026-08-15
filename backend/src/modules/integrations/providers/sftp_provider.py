"""SFTP / CSV provider — pull files server-side only (paramiko)."""

from __future__ import annotations

import asyncio
import base64
import csv
import fnmatch
import hashlib
import hmac
import io
import time
from datetime import UTC, datetime
from typing import Any

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)


class SFTPProvider:
    """ETAPA 6: SFTP connect + list/download CSV with encoding and schedule metadata."""

    type = "sftp"

    def __init__(self, *, connect_timeout: float = 20.0, max_files: int = 50) -> None:
        self._connect_timeout = connect_timeout
        self._max_files = max_files

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        host = _cfg(configuration, "host")
        username = _cfg(configuration, "username")
        if not host or not username:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Host ou usuário SFTP não configurados.",
            )
        missing = _missing_auth_secret(configuration, secrets)
        if missing:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=missing,
            )

        port = _port(configuration)
        remote_path = _cfg(configuration, "remote_path", "remotePath") or "/"
        auth_label = _auth_label(configuration)
        started = time.perf_counter()
        try:
            listing = await asyncio.to_thread(
                _connect_and_listdir,
                host=host,
                port=port,
                username=username,
                configuration=configuration,
                secrets=secrets,
                remote_path=remote_path,
                timeout=self._connect_timeout,
            )
        except _SFTPError as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=f"{host}:{port}",
                authentication=auth_label,
                error_detail=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 — surface safe message
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=f"{host}:{port}",
                authentication=auth_label,
                error_detail=_safe_error(exc),
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        schedule = _cfg(configuration, "schedule_cron", "scheduleCron") or "manual"
        return IntegrationTestResult(
            success=True,
            message="Conexão SFTP realizada com sucesso",
            server=f"{host}:{port}",
            duration_ms=duration_ms,
            authentication=auth_label,
            permission=f"{remote_path} ({len(listing)} entradas); schedule={schedule}",
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        started_at = datetime.now(UTC).isoformat()
        host = _cfg(configuration, "host")
        username = _cfg(configuration, "username")
        if not host or not username:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Host ou usuário SFTP não configurados.",
                started_at=started_at,
                finished_at=finished,
            )
        missing = _missing_auth_secret(configuration, secrets)
        if missing:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=missing,
                started_at=started_at,
                finished_at=finished,
            )

        port = _port(configuration)
        remote_path = _cfg(configuration, "remote_path", "remotePath") or "/"
        pattern = (
            _cfg(configuration, "filename_pattern", "filenamePattern") or "*.csv"
        )
        encoding = _cfg(configuration, "encoding") or "utf-8"
        delimiter = _cfg(configuration, "delimiter") or ","
        schedule = _cfg(configuration, "schedule_cron", "scheduleCron") or "manual"

        try:
            result = await asyncio.to_thread(
                _pull_and_parse_csv,
                host=host,
                port=port,
                username=username,
                configuration=configuration,
                secrets=secrets,
                remote_path=remote_path,
                pattern=pattern,
                encoding=encoding,
                delimiter=delimiter,
                timeout=self._connect_timeout,
                max_files=self._max_files,
            )
        except _SFTPError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=str(exc),
                started_at=started_at,
                finished_at=finished,
            )
        except Exception as exc:  # noqa: BLE001
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=_safe_error(exc),
                started_at=started_at,
                finished_at=finished,
            )

        finished = datetime.now(UTC).isoformat()
        files = result["files"]
        records = int(result["records"])
        return IntegrationSyncResult(
            success=True,
            mode="full",
            records_processed=records,
            message=(
                f"SFTP pull: {len(files)} arquivo(s) coincidente(s) com '{pattern}' "
                f"em {remote_path}; {records} linha(s) CSV ({encoding}). "
                f"Schedule: {schedule}."
            ),
            started_at=started_at,
            finished_at=finished,
        )


class _SFTPError(Exception):
    """Safe, user-facing SFTP failure (no secrets)."""


def _connect_and_listdir(
    *,
    host: str,
    port: int,
    username: str,
    configuration: dict[str, Any],
    secrets: dict[str, Any],
    remote_path: str,
    timeout: float,
) -> list[str]:
    client = _open_client(
        host=host,
        port=port,
        username=username,
        configuration=configuration,
        secrets=secrets,
        timeout=timeout,
    )
    try:
        sftp = client.open_sftp()
        try:
            return sorted(sftp.listdir(remote_path))
        finally:
            sftp.close()
    except OSError as exc:
        raise _SFTPError(f"Não foi possível listar '{remote_path}': {_safe_error(exc)}") from exc
    finally:
        client.close()


def _pull_and_parse_csv(
    *,
    host: str,
    port: int,
    username: str,
    configuration: dict[str, Any],
    secrets: dict[str, Any],
    remote_path: str,
    pattern: str,
    encoding: str,
    delimiter: str,
    timeout: float,
    max_files: int,
) -> dict[str, Any]:
    client = _open_client(
        host=host,
        port=port,
        username=username,
        configuration=configuration,
        secrets=secrets,
        timeout=timeout,
    )
    matched: list[str] = []
    records = 0
    try:
        sftp = client.open_sftp()
        try:
            try:
                names = sftp.listdir(remote_path)
            except OSError as exc:
                raise _SFTPError(
                    f"Não foi possível listar '{remote_path}': {_safe_error(exc)}"
                ) from exc

            for name in sorted(names):
                if not fnmatch.fnmatch(name, pattern):
                    continue
                matched.append(name)
                if len(matched) > max_files:
                    raise _SFTPError(
                        f"Mais de {max_files} arquivos coincidem com '{pattern}'."
                    )
                remote_file = _join_remote(remote_path, name)
                try:
                    with sftp.open(remote_file, "rb") as handle:
                        raw = handle.read()
                except OSError as exc:
                    raise _SFTPError(
                        f"Falha ao ler '{remote_file}': {_safe_error(exc)}"
                    ) from exc
                records += _count_csv_rows(raw, encoding=encoding, delimiter=delimiter)
        finally:
            sftp.close()
    finally:
        client.close()

    return {"files": matched, "records": records}


def _open_client(
    *,
    host: str,
    port: int,
    username: str,
    configuration: dict[str, Any],
    secrets: dict[str, Any],
    timeout: float,
) -> Any:
    import paramiko

    auth_type = (
        _cfg(configuration, "auth_type", "authType") or "private_key"
    ).strip().lower()
    client = paramiko.SSHClient()
    _apply_host_key_policy(client, configuration)
    connect_kwargs: dict[str, Any] = {
        "hostname": host,
        "port": port,
        "username": username,
        "timeout": timeout,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if auth_type == "password":
        password = _secret(secrets, "password", "sftp_password")
        if not password:
            raise _SFTPError("Senha SFTP não configurada no backend.")
        connect_kwargs["password"] = password
    else:
        key_material = _secret(
            secrets,
            "private_key_pem",
            "private_key",
            "privateKey",
            "sftp_private_key",
        )
        if not key_material:
            raise _SFTPError("Chave privada SFTP não configurada no backend.")
        passphrase = _secret(secrets, "passphrase", "private_key_passphrase") or None
        try:
            connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key(
                io.StringIO(key_material), password=passphrase
            )
        except paramiko.SSHException:
            try:
                connect_kwargs["pkey"] = paramiko.Ed25519Key.from_private_key(
                    io.StringIO(key_material), password=passphrase
                )
            except paramiko.SSHException as exc:
                raise _SFTPError("Chave privada SFTP inválida ou passphrase incorreta.") from exc

    try:
        client.connect(**connect_kwargs)
    except paramiko.AuthenticationException as exc:
        raise _SFTPError("Autenticação SFTP rejeitada.") from exc
    except paramiko.BadHostKeyException as exc:
        raise _SFTPError(
            "Host key do servidor SFTP não corresponde à esperada — conexão abortada."
        ) from exc
    except (OSError, paramiko.SSHException) as exc:
        raise _SFTPError(f"Falha de conexão SFTP: {_safe_error(exc)}") from exc

    _assert_expected_fingerprint(client, configuration)
    return client


def _apply_host_key_policy(client: Any, configuration: dict[str, Any]) -> None:
    """Fail closed on unknown host keys.

    Trusting any key on first sight makes the transfer trivially interceptable, so
    the server must be known: either through the system `known_hosts`, or through
    an expected fingerprint in the integration configuration. Accepting an unknown
    key stays possible, but only as an explicit, per-integration decision.
    """
    import paramiko

    client.load_system_host_keys()
    trust_unknown = _flag(configuration, "trust_unknown_host_key", "trustUnknownHostKey")
    expected = _cfg(configuration, "host_key_fingerprint", "hostKeyFingerprint")
    if trust_unknown or expected:
        # With an expected fingerprint the key is verified right after the
        # handshake, which is what actually authenticates the server; without one
        # the operator asked for first-use trust explicitly.
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
        return
    client.set_missing_host_key_policy(paramiko.RejectPolicy())


def _assert_expected_fingerprint(client: Any, configuration: dict[str, Any]) -> None:
    expected = _cfg(configuration, "host_key_fingerprint", "hostKeyFingerprint")
    if not expected:
        return

    key = client.get_transport().get_remote_server_key() if client.get_transport() else None
    if key is None:
        client.close()
        raise _SFTPError("Não foi possível obter a host key do servidor SFTP.")

    digest = hashlib.sha256(key.asbytes()).digest()
    actual = base64.b64encode(digest).decode().rstrip("=")
    normalized = expected.removeprefix("SHA256:").strip().rstrip("=")
    if not hmac.compare_digest(actual, normalized):
        client.close()
        raise _SFTPError(
            "Host key do servidor SFTP não corresponde ao fingerprint configurado."
        )


def _flag(configuration: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = configuration.get(key)
        if isinstance(value, bool):
            return value
        if value is not None:
            return str(value).strip().lower() in {"1", "true", "yes", "on"}
    return False


def _count_csv_rows(raw: bytes, *, encoding: str, delimiter: str) -> int:
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError as exc:
        raise _SFTPError(f"Encoding '{encoding}' inválido para o arquivo CSV.") from exc
    if not text.strip():
        return 0
    reader = csv.reader(io.StringIO(text), delimiter=delimiter[:1] or ",")
    rows = list(reader)
    if not rows:
        return 0
    # Treat first row as header when present.
    return max(0, len(rows) - 1)


def _missing_auth_secret(configuration: dict[str, Any], secrets: dict[str, Any]) -> str | None:
    auth_type = (
        _cfg(configuration, "auth_type", "authType") or "private_key"
    ).strip().lower()
    if auth_type == "password":
        if not _secret(secrets, "password", "sftp_password"):
            return "Senha SFTP não configurada no backend."
        return None
    if not _secret(
        secrets, "private_key_pem", "private_key", "privateKey", "sftp_private_key"
    ):
        return "Chave privada SFTP não configurada no backend."
    return None


def _auth_label(configuration: dict[str, Any]) -> str:
    auth_type = (
        _cfg(configuration, "auth_type", "authType") or "private_key"
    ).strip().lower()
    return "SFTP password" if auth_type == "password" else "SFTP private key"


def _port(configuration: dict[str, Any]) -> int:
    raw = configuration.get("port")
    try:
        port = int(raw) if raw is not None else 22
    except (TypeError, ValueError):
        port = 22
    return port if 1 <= port <= 65535 else 22


def _cfg(configuration: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = configuration.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _secret(secrets: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = secrets.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _join_remote(path: str, name: str) -> str:
    if path.endswith("/"):
        return f"{path}{name}"
    return f"{path}/{name}"


def _safe_error(exc: BaseException) -> str:
    text = str(exc).strip() or type(exc).__name__
    # Never echo credential-like fragments if libraries embed them.
    lowered = text.lower()
    for needle in ("password", "private key", "passphrase", "secret"):
        if needle in lowered:
            return type(exc).__name__
    return text[:300]
