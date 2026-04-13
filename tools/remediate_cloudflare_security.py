#!/usr/bin/env python3
"""Apply selected Cloudflare security remediations for bluecollar-systems.com.

This script is intended to run in GitHub Actions using repository secrets:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID (optional for Turnstile)

Primary goals:
1) Harden DMARC from monitoring-only to a staged policy.
2) Ensure a Turnstile widget exists for the production domain (best effort).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://api.cloudflare.com/client/v4"


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _cf_request(
    token: str,
    method: str,
    path: str,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = API_BASE + path
    if query:
        query_items = {
            k: str(v) for k, v in query.items() if v is not None and str(v) != ""
        }
        if query_items:
            url += "?" + urllib.parse.urlencode(query_items)

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, method=method.upper())
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            text = resp.read().decode("utf-8")
            parsed = json.loads(text)
            parsed["_http_status"] = resp.getcode()
            return parsed
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {"success": False, "errors": [{"message": payload}]}
        parsed["_http_status"] = exc.code
        return parsed
    except Exception as exc:  # pragma: no cover
        return {
            "success": False,
            "errors": [{"message": f"{type(exc).__name__}: {exc}"}],
            "_http_status": 0,
        }


def _extract_rua(content: str | None) -> str | None:
    if not content:
        return None
    clean = content.strip().strip('"')
    for part in clean.split(";"):
        p = part.strip()
        if p.lower().startswith("rua="):
            return p[4:].strip()
    return None


def _errors_to_text(resp: dict[str, Any]) -> str:
    errs = resp.get("errors") or []
    if not errs:
        return "Unknown error"
    return "; ".join(str(e.get("message") or e) for e in errs)


def _build_dmarc_content(
    policy: str,
    pct: int,
    rua: str,
    strict_alignment: bool,
) -> str:
    parts = [
        "v=DMARC1",
        f"p={policy}",
        f"pct={pct}",
        f"rua={rua}",
    ]
    if strict_alignment:
        parts.extend(["adkim=s", "aspf=s"])
    parts.append("fo=1")
    return '"' + "; ".join(parts) + '"'


def main() -> int:
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: CLOUDFLARE_API_TOKEN is required.")
        return 1

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    domain = os.getenv("TARGET_DOMAIN", "bluecollar-systems.com").strip()
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "").strip()

    policy = os.getenv("DMARC_POLICY", "quarantine").strip().lower()
    if policy not in {"none", "quarantine", "reject"}:
        print(f"ERROR: Unsupported DMARC_POLICY={policy}")
        return 1
    pct = int(os.getenv("DMARC_PCT", "25").strip())
    pct = max(0, min(100, pct))

    strict_alignment = _bool_env("DMARC_STRICT", default=True)
    enable_turnstile = _bool_env("ENABLE_TURNSTILE", default=True)
    fallback_rua = os.getenv(
        "DMARC_RUA",
        "mailto:2fdc58aa85a44ab59fdd0874b1548894@dmarc-reports.cloudflare.net",
    ).strip()

    summary: dict[str, Any] = {
        "domain": domain,
        "zone_id": None,
        "dmarc": {"status": "not_run"},
        "turnstile": {"status": "not_run"},
    }

    # Resolve zone id if not provided
    if not zone_id:
        zone_res = _cf_request(
            token, "GET", "/zones", query={"name": domain, "status": "active", "per_page": 1}
        )
        if not zone_res.get("success"):
            summary["dmarc"] = {
                "status": "error",
                "message": f"Zone lookup failed: {_errors_to_text(zone_res)}",
            }
            print(json.dumps(summary, indent=2))
            return 1
        zone_results = zone_res.get("result") or []
        if not zone_results:
            summary["dmarc"] = {
                "status": "error",
                "message": f"No active zone found for {domain}",
            }
            print(json.dumps(summary, indent=2))
            return 1
        zone_id = zone_results[0]["id"]
    summary["zone_id"] = zone_id

    # DMARC read existing
    dmarc_name = f"_dmarc.{domain}"
    rec_res = _cf_request(
        token,
        "GET",
        f"/zones/{zone_id}/dns_records",
        query={"type": "TXT", "name": dmarc_name, "per_page": 50},
    )
    if not rec_res.get("success"):
        summary["dmarc"] = {
            "status": "error",
            "message": f"DMARC record lookup failed: {_errors_to_text(rec_res)}",
        }
        print(json.dumps(summary, indent=2))
        return 1

    records = rec_res.get("result") or []
    existing = records[0] if records else None
    existing_content = existing.get("content") if existing else None
    rua = _extract_rua(existing_content) or fallback_rua
    target_content = _build_dmarc_content(
        policy=policy,
        pct=pct,
        rua=rua,
        strict_alignment=strict_alignment,
    )

    dmarc_body = {
        "type": "TXT",
        "name": dmarc_name,
        "content": target_content,
        "ttl": 1,
    }

    if existing:
        write_res = _cf_request(
            token,
            "PUT",
            f"/zones/{zone_id}/dns_records/{existing['id']}",
            body=dmarc_body,
        )
        action = "updated"
    else:
        write_res = _cf_request(
            token, "POST", f"/zones/{zone_id}/dns_records", body=dmarc_body
        )
        action = "created"

    if not write_res.get("success"):
        summary["dmarc"] = {
            "status": "error",
            "message": f"DMARC {action} failed: {_errors_to_text(write_res)}",
            "proposed_content": target_content,
            "existing_content": existing_content,
        }
        print(json.dumps(summary, indent=2))
        return 1

    verify_res = _cf_request(
        token,
        "GET",
        f"/zones/{zone_id}/dns_records",
        query={"type": "TXT", "name": dmarc_name, "per_page": 1},
    )
    verified_content = None
    if verify_res.get("success") and verify_res.get("result"):
        verified_content = verify_res["result"][0].get("content")

    summary["dmarc"] = {
        "status": "ok",
        "action": action,
        "record_name": dmarc_name,
        "content": verified_content or target_content,
    }

    # Turnstile best-effort
    if not enable_turnstile:
        summary["turnstile"] = {"status": "skipped", "reason": "disabled"}
    elif not account_id:
        summary["turnstile"] = {
            "status": "skipped",
            "reason": "CLOUDFLARE_ACCOUNT_ID not provided",
        }
    else:
        list_res = _cf_request(
            token, "GET", f"/accounts/{account_id}/challenges/widgets"
        )
        if not list_res.get("success"):
            summary["turnstile"] = {
                "status": "error",
                "message": f"Widget list failed: {_errors_to_text(list_res)}",
            }
        else:
            widgets = list_res.get("result") or []
            domain_set = {domain, f"www.{domain}"}

            def _widget_domains(w: dict[str, Any]) -> set[str]:
                return {str(d).strip().lower() for d in (w.get("domains") or [])}

            existing_widget = None
            for w in widgets:
                if _widget_domains(w) & {d.lower() for d in domain_set}:
                    existing_widget = w
                    break

            if existing_widget:
                summary["turnstile"] = {
                    "status": "ok",
                    "action": "already_present",
                    "sitekey": existing_widget.get("sitekey"),
                    "name": existing_widget.get("name"),
                }
            else:
                create_body = {
                    "name": "bluecollar-systems-main",
                    "domains": [domain, f"www.{domain}"],
                    "mode": "managed",
                }
                create_res = _cf_request(
                    token,
                    "POST",
                    f"/accounts/{account_id}/challenges/widgets",
                    body=create_body,
                )
                if create_res.get("success"):
                    result = create_res.get("result") or {}
                    summary["turnstile"] = {
                        "status": "ok",
                        "action": "created",
                        "sitekey": result.get("sitekey"),
                        "name": result.get("name"),
                    }
                else:
                    summary["turnstile"] = {
                        "status": "error",
                        "message": f"Widget create failed: {_errors_to_text(create_res)}",
                    }

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
