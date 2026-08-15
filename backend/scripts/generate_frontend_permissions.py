"""Generates frontend/src/constants/permissions.ts from the backend catalog.

The backend catalog in `src/shared/infrastructure/security/permission_codes.py` is the
single source of truth. Run after changing it:

    python -m scripts.generate_frontend_permissions       # writes the file
    python -m scripts.generate_frontend_permissions --check  # CI: fails if stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.shared.infrastructure.security.permission_codes import (
    SERVICE_BY_RESOURCE,
    PermissionAction,
    PermissionCode,
)

TARGET = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "permissions.ts"

HEADER = """\
/**
 * GENERATED FILE — do not edit.
 *
 * Source of truth: backend/src/shared/infrastructure/security/permission_codes.py
 * Regenerate with: cd backend && python -m scripts.generate_frontend_permissions
 *
 * Codes are namespaced as `service.resource.action`. Each entry also carries the
 * legacy `resource.action` alias, which still authorizes during the migration.
 */
"""


def _action_block() -> str:
    lines = ["export const PermissionAction = {"]
    for key in sorted(vars(PermissionAction)):
        value = getattr(PermissionAction, key)
        if key.isupper() and isinstance(value, str):
            lines.append(f"  {key}: '{value}',")
    lines.append("} as const")
    lines.append("")
    lines.append(
        "export type PermissionActionValue =\n"
        "  (typeof PermissionAction)[keyof typeof PermissionAction]"
    )
    return "\n".join(lines)


def _constant_pairs() -> list[tuple[str, str, str]]:
    """(constant name, canonical code, legacy code) in declaration order."""
    pairs: list[tuple[str, str, str]] = []
    for key, value in vars(PermissionCode).items():
        if not key.isupper() or not isinstance(value, str):
            continue
        pairs.append((key, PermissionCode.canonical(value), value))
    return pairs


def _codes_block(pairs: list[tuple[str, str, str]]) -> str:
    lines = ["export const PermissionCode = {"]
    lines += [f"  {key}: '{code}'," for key, code, _ in pairs]
    lines.append("} as const")
    lines.append("")
    lines.append("/** Pre-namespace aliases, accepted by the backend until they are dropped. */")
    lines.append("export const PermissionLegacyCode = {")
    lines += [f"  {key}: '{legacy}'," for key, _, legacy in pairs]
    lines.append("} as const")
    lines.append("")
    lines.append(
        "export type PermissionCodeValue = (typeof PermissionCode)[keyof typeof PermissionCode]"
    )
    return "\n".join(lines)


def _services_block() -> str:
    services = sorted(set(SERVICE_BY_RESOURCE.values()))
    lines = ["export const PermissionService = {"]
    lines += [f"  {service.upper()}: '{service}'," for service in services]
    lines.append("} as const")
    lines.append("")
    lines.append(
        "export type PermissionServiceValue =\n"
        "  (typeof PermissionService)[keyof typeof PermissionService]"
    )
    return "\n".join(lines)


def _catalog_block() -> str:
    lines = [
        "export interface PermissionCatalogEntry {",
        "  code: string",
        "  legacyCode: string",
        "  service: string",
        "  resource: string",
        "  action: string",
        "  name: string",
        "  description: string",
        "}",
        "",
        "export const PERMISSION_CATALOG: readonly PermissionCatalogEntry[] = [",
    ]
    for item in PermissionCode.catalog():
        lines.append(
            "  {"
            f" code: '{item.code}',"
            f" legacyCode: '{item.legacy_code}',"
            f" service: '{item.service}',"
            f" resource: '{item.resource}',"
            f" action: '{item.action}',"
            f" name: {_ts_string(item.name)},"
            f" description: {_ts_string(item.description)}"
            " },"
        )
    lines.append("] as const")
    return "\n".join(lines)


def _bundles_block() -> str:
    lines = [
        "export interface PermissionBundleEntry {",
        "  slug: string",
        "  service: string",
        "  name: string",
        "  description: string",
        "  codes: readonly string[]",
        "}",
        "",
        "export const PERMISSION_BUNDLES: readonly PermissionBundleEntry[] = [",
    ]
    for bundle in PermissionCode.bundles():
        codes = ", ".join(f"'{code}'" for code in bundle.codes)
        lines.append(
            "  {"
            f" slug: '{bundle.slug}',"
            f" service: '{bundle.service}',"
            f" name: {_ts_string(bundle.name)},"
            f" description: {_ts_string(bundle.description)},"
            f" codes: [{codes}]"
            " },"
        )
    lines.append("] as const")
    return "\n".join(lines)


HELPERS = """\
const ALIASES: Record<string, readonly string[]> = PERMISSION_CATALOG.reduce(
  (acc, entry) => {
    const pair = [entry.code, entry.legacyCode] as const
    acc[entry.code] = pair
    acc[entry.legacyCode] = pair
    return acc
  },
  {} as Record<string, readonly string[]>,
)

/** Both accepted forms of a code (canonical + legacy), or the code itself. */
export function permissionAliases(code: string): readonly string[] {
  return ALIASES[code] ?? [code]
}

/** True when the granted set contains any accepted form of the code. */
export function hasPermissionCode(granted: ReadonlySet<string>, code: string): boolean {
  return permissionAliases(code).some((alias) => granted.has(alias))
}

export function permissionService(code: string): string {
  const parts = code.split('.')
  if (parts.length >= 3) return parts[0]
  return PERMISSION_CATALOG.find((entry) => entry.legacyCode === code)?.service ?? ''
}

export function permissionResource(code: string): string {
  const parts = code.split('.')
  if (parts.length >= 3) return parts[1]
  return parts.length === 2 ? parts[0] : code
}

export function permissionAction(code: string): string {
  const parts = code.split('.')
  if (parts.length >= 3) return parts.slice(2).join('.')
  return parts.length === 2 ? parts[1] : ''
}
"""


def _ts_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def render() -> str:
    pairs = _constant_pairs()
    blocks = (
        HEADER,
        _action_block(),
        _services_block(),
        _codes_block(pairs),
        _catalog_block(),
        _bundles_block(),
        HELPERS,
    )
    return "\n\n".join(block.rstrip() for block in blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the generated file is out of date",
    )
    args = parser.parse_args()

    content = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != content:
            print(f"{TARGET} is out of date — run python -m scripts.generate_frontend_permissions")
            return 1
        print(f"{TARGET} is up to date")
        return 0

    TARGET.write_text(content, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
