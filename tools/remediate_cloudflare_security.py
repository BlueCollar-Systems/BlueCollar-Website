#!/usr/bin/env python3
"""Apply selected Cloudflare security remediations for bluecollar-systems.com.

This script is intended to run in GitHub Actions using repository secrets:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID (optional for Turnstile)

Primary goals:
1) Ensure Cloudflare-managed security.txt is enabled for the production domain.
2) Harden DMARC from monitoring-only to a staged policy.
3) Ensure a Turnstile widget exists for the production domain (best effort).
4) Enable HSTS, Always Use HTTPS, and minimum TLS 1.2 zone settings.
5) Ensure www CNAME points at the Pages hostname (proxied).
6) Register www as a Pages custom domain (fixes 522 when DNS points at Pages).
7) Optionally disable zone HSTS so Pages _headers HSTS applies on custom domains.
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


def _augment_permission_hint(message: str, area: str) -> str:
    msg_lower = message.lower()
    if "authentication error" not in msg_lower and "unauthorized" not in msg_lower:
        return message
    if area == "dmarc":
        return (
            f"{message}. Likely missing token scope for DNS write "
            "(Zone DNS:Edit)."
        )
    if area == "turnstile":
        return (
            f"{message}. Likely missing token scope for Turnstile widget management "
            "(Account-level challenges/Turnstile edit)."
        )
    if area == "securitytxt":
        return (
            f"{message}. Likely missing token scope for Security Center settings "
            "(Zone Settings/Security Center edit)."
        )
    if area in {"hsts", "min_tls", "always_https"}:
        return (
            f"{message}. Likely missing token scope for zone SSL/TLS settings "
            "(Zone Settings:Edit)."
        )
    if area == "www_dns":
        return (
            f"{message}. Likely missing token scope for DNS write "
            "(Zone DNS:Edit)."
        )
    if area == "pages_domain":
        return (
            f"{message}. Likely missing token scope for Pages project edit "
            "(Account Cloudflare Pages:Edit)."
        )
    return message




def _patch_zone_setting(
    token: str, zone_id: str, setting_id: str, value: Any
) -> dict[str, Any]:
    return _cf_request(
        token,
        "PATCH",
        f"/zones/{zone_id}/settings/{setting_id}",
        body={"value": value},
    )


def _get_zone_setting(token: str, zone_id: str, setting_id: str) -> dict[str, Any]:
    return _cf_request(token, "GET", f"/zones/{zone_id}/settings/{setting_id}")


def _setting_value(result: dict[str, Any] | None) -> Any:
    if not result:
        return None
    return result.get("value")


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
    enable_security_txt = _bool_env("ENABLE_SECURITY_TXT", default=True)
    require_security_txt_update = _bool_env("REQUIRE_SECURITY_TXT_UPDATE", default=False)
    enable_hsts = _bool_env("ENABLE_HSTS", default=True)
    enable_min_tls = _bool_env("ENABLE_MIN_TLS", default=True)
    enable_always_use_https = _bool_env("ENABLE_ALWAYS_USE_HTTPS", default=True)
    enable_www_cname = _bool_env("ENABLE_WWW_CNAME", default=True)
    enable_pages_www_domain = _bool_env("ENABLE_PAGES_WWW_DOMAIN", default=True)
    pages_project = os.getenv("PAGES_PROJECT", "bluecollar-website").strip()
    hsts_via_pages_headers = _bool_env("HSTS_VIA_PAGES_HEADERS", default=True)
    www_cname_target = os.getenv(
        "WWW_CNAME_TARGET", "bluecollar-website.pages.dev"
    ).strip()
    fallback_rua = os.getenv(
        "DMARC_RUA",
        "mailto:2fdc58aa85a44ab59fdd0874b1548894@dmarc-reports.cloudflare.net",
    ).strip()
    security_contact = os.getenv(
        "SECURITY_TXT_CONTACT", "mailto:support@bluecollar-systems.com"
    ).strip()
    security_policy = os.getenv(
        "SECURITY_TXT_POLICY", f"https://{domain}/feedback"
    ).strip()
    security_expires = os.getenv(
        "SECURITY_TXT_EXPIRES", "2027-05-25T23:59:59Z"
    ).strip()

    summary: dict[str, Any] = {
        "domain": domain,
        "zone_id": None,
        "securitytxt": {"status": "not_run"},
        "dmarc": {"status": "not_run"},
        "turnstile": {"status": "not_run"},
        "hsts": {"status": "not_run"},
        "min_tls": {"status": "not_run"},
        "always_use_https": {"status": "not_run"},
        "www_cname": {"status": "not_run"},
        "pages_www_domain": {"status": "not_run"},
    }
    had_errors = False

    # Resolve zone id if not provided
    if not zone_id:
        zone_res = _cf_request(
            token, "GET", "/zones", query={"name": domain, "status": "active", "per_page": 1}
        )
        if not zone_res.get("success"):
            summary["dmarc"] = {
                "status": "error",
                "message": _augment_permission_hint(
                    f"Zone lookup failed: {_errors_to_text(zone_res)}", "dmarc"
                ),
            }
            had_errors = True
        zone_results = zone_res.get("result") or []
        if not had_errors and not zone_results:
            summary["dmarc"] = {
                "status": "error",
                "message": f"No active zone found for {domain}",
            }
            had_errors = True
        if not had_errors:
            zone_id = zone_results[0]["id"]
    summary["zone_id"] = zone_id

    # Cloudflare-managed security.txt. The static site also serves the same
    # file at /.well-known/security.txt, but the dashboard insight checks this
    # Security Center setting directly.
    if not enable_security_txt:
        summary["securitytxt"] = {"status": "skipped", "reason": "disabled"}
    elif not zone_id:
        summary["securitytxt"] = {
            "status": "skipped",
            "reason": "Zone id unavailable",
        }
    else:
        security_body = {
            "enabled": True,
            "contact": [security_contact],
            "canonical": [f"https://{domain}/.well-known/security.txt"],
            "expires": security_expires,
            "preferred_languages": "en",
            "policy": [security_policy],
        }
        security_res = _cf_request(
            token,
            "PUT",
            f"/zones/{zone_id}/security-center/securitytxt",
            body=security_body,
        )
        if not security_res.get("success"):
            summary["securitytxt"] = {
                "status": "manual_action_required",
                "message": _augment_permission_hint(
                    f"security.txt update failed: {_errors_to_text(security_res)}",
                    "securitytxt",
                ),
                "proposed_content": security_body,
            }
            if require_security_txt_update:
                had_errors = True
        else:
            verify_res = _cf_request(
                token,
                "GET",
                f"/zones/{zone_id}/security-center/securitytxt",
            )
            summary["securitytxt"] = {
                "status": "ok",
                "action": "enabled",
                "config": (
                    verify_res.get("result")
                    if verify_res.get("success")
                    else security_body
                ),
            }

    # DMARC read/update
    dmarc_name = f"_dmarc.{domain}"
    if not zone_id:
        summary["dmarc"] = {
            "status": "skipped",
            "reason": "Zone id unavailable",
        }
    else:
        rec_res = _cf_request(
            token,
            "GET",
            f"/zones/{zone_id}/dns_records",
            query={"type": "TXT", "name": dmarc_name, "per_page": 50},
        )
        if not rec_res.get("success"):
            summary["dmarc"] = {
                "status": "error",
                "message": _augment_permission_hint(
                    f"DMARC record lookup failed: {_errors_to_text(rec_res)}", "dmarc"
                ),
            }
            had_errors = True
        else:
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
                    "message": _augment_permission_hint(
                        f"DMARC {action} failed: {_errors_to_text(write_res)}", "dmarc"
                    ),
                    "proposed_content": target_content,
                    "existing_content": existing_content,
                }
                had_errors = True
            else:
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
                "message": _augment_permission_hint(
                    f"Widget list failed: {_errors_to_text(list_res)}", "turnstile"
                ),
            }
            had_errors = True
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
                        "message": _augment_permission_hint(
                            f"Widget create failed: {_errors_to_text(create_res)}",
                            "turnstile",
                        ),
                    }
                    had_errors = True


    # Zone SSL/TLS and HSTS settings.
    # Pages _headers already sets HSTS on pages.dev; zone HSTS overrides custom
    # domains with a shorter default (180d, no preload). Prefer _headers when
    # HSTS_VIA_PAGES_HEADERS is true by disabling zone HSTS.
    hsts_target = {
        "enabled": True,
        "max_age": 31536000,
        "include_subdomains": True,
        "preload": True,
        "nosniff": True,
    }
    hsts_disabled_for_pages = {
        "enabled": False,
        "max_age": 0,
        "include_subdomains": False,
        "preload": False,
        "nosniff": False,
    }

    if not zone_id:
        for key in ("hsts", "min_tls", "always_use_https", "www_cname"):
            summary[key] = {"status": "skipped", "reason": "Zone id unavailable"}
    else:
        if not enable_hsts:
            summary["hsts"] = {"status": "skipped", "reason": "disabled"}
        elif hsts_via_pages_headers:
            current = _get_zone_setting(token, zone_id, "security_header")
            if not current.get("success"):
                summary["hsts"] = {
                    "status": "error",
                    "message": _augment_permission_hint(
                        f"HSTS read failed: {_errors_to_text(current)}", "hsts"
                    ),
                }
                had_errors = True
            else:
                existing_val = _setting_value(current.get("result")) or {}
                zone_hsts_on = existing_val.get("enabled") is True
                if not zone_hsts_on:
                    summary["hsts"] = {
                        "status": "ok",
                        "action": "already_disabled_for_pages_headers",
                        "note": "Pages _headers supplies HSTS on custom domains",
                    }
                else:
                    patch_res = _patch_zone_setting(
                        token, zone_id, "security_header", hsts_disabled_for_pages
                    )
                    if not patch_res.get("success"):
                        summary["hsts"] = {
                            "status": "error",
                            "message": _augment_permission_hint(
                                f"Zone HSTS disable failed: {_errors_to_text(patch_res)}",
                                "hsts",
                            ),
                        }
                        had_errors = True
                    else:
                        summary["hsts"] = {
                            "status": "ok",
                            "action": "disabled_for_pages_headers",
                            "note": "Pages _headers supplies HSTS on custom domains",
                        }
        else:
            current = _get_zone_setting(token, zone_id, "security_header")
            if not current.get("success"):
                summary["hsts"] = {
                    "status": "error",
                    "message": _augment_permission_hint(
                        f"HSTS read failed: {_errors_to_text(current)}", "hsts"
                    ),
                }
                had_errors = True
            else:
                existing_val = _setting_value(current.get("result")) or {}
                needs_update = not (
                    existing_val.get("enabled") is True
                    and existing_val.get("max_age") == 31536000
                    and existing_val.get("include_subdomains") is True
                    and existing_val.get("preload") is True
                    and existing_val.get("nosniff") is True
                )
                if not needs_update:
                    summary["hsts"] = {"status": "ok", "action": "already_set"}
                else:
                    patch_res = _patch_zone_setting(
                        token, zone_id, "security_header", hsts_target
                    )
                    if not patch_res.get("success"):
                        summary["hsts"] = {
                            "status": "error",
                            "message": _augment_permission_hint(
                                f"HSTS update failed: {_errors_to_text(patch_res)}",
                                "hsts",
                            ),
                        }
                        had_errors = True
                    else:
                        summary["hsts"] = {
                            "status": "ok",
                            "action": "updated",
                            "value": hsts_target,
                        }

        if not enable_min_tls:
            summary["min_tls"] = {"status": "skipped", "reason": "disabled"}
        else:
            current = _get_zone_setting(token, zone_id, "min_tls_version")
            if not current.get("success"):
                summary["min_tls"] = {
                    "status": "error",
                    "message": _augment_permission_hint(
                        f"min_tls read failed: {_errors_to_text(current)}", "min_tls"
                    ),
                }
                had_errors = True
            elif _setting_value(current.get("result")) == "1.2":
                summary["min_tls"] = {"status": "ok", "action": "already_set"}
            else:
                patch_res = _patch_zone_setting(token, zone_id, "min_tls_version", "1.2")
                if not patch_res.get("success"):
                    summary["min_tls"] = {
                        "status": "error",
                        "message": _augment_permission_hint(
                            f"min_tls update failed: {_errors_to_text(patch_res)}",
                            "min_tls",
                        ),
                    }
                    had_errors = True
                else:
                    summary["min_tls"] = {
                        "status": "ok",
                        "action": "updated",
                        "value": "1.2",
                    }

        if not enable_always_use_https:
            summary["always_use_https"] = {
                "status": "skipped",
                "reason": "disabled",
            }
        else:
            current = _get_zone_setting(token, zone_id, "always_use_https")
            if not current.get("success"):
                summary["always_use_https"] = {
                    "status": "error",
                    "message": _augment_permission_hint(
                        f"always_use_https read failed: {_errors_to_text(current)}",
                        "always_https",
                    ),
                }
                had_errors = True
            elif _setting_value(current.get("result")) == "on":
                summary["always_use_https"] = {
                    "status": "ok",
                    "action": "already_set",
                }
            else:
                patch_res = _patch_zone_setting(
                    token, zone_id, "always_use_https", "on"
                )
                if not patch_res.get("success"):
                    summary["always_use_https"] = {
                        "status": "error",
                        "message": _augment_permission_hint(
                            f"always_use_https update failed: {_errors_to_text(patch_res)}",
                            "always_https",
                        ),
                    }
                    had_errors = True
                else:
                    summary["always_use_https"] = {
                        "status": "ok",
                        "action": "updated",
                        "value": "on",
                    }

        if not enable_www_cname:
            summary["www_cname"] = {"status": "skipped", "reason": "disabled"}
        else:
            www_name = f"www.{domain}"
            rec_res = _cf_request(
                token,
                "GET",
                f"/zones/{zone_id}/dns_records",
                query={"type": "CNAME", "name": www_name, "per_page": 50},
            )
            if not rec_res.get("success"):
                summary["www_cname"] = {
                    "status": "error",
                    "message": _augment_permission_hint(
                        f"www CNAME lookup failed: {_errors_to_text(rec_res)}",
                        "www_dns",
                    ),
                }
                had_errors = True
            else:
                records = rec_res.get("result") or []
                existing = records[0] if records else None
                cname_body = {
                    "type": "CNAME",
                    "name": www_name,
                    "content": www_cname_target,
                    "proxied": True,
                    "ttl": 1,
                }
                if existing:
                    same = (
                        str(existing.get("content", "")).rstrip(".") == www_cname_target.rstrip(".")
                        and existing.get("proxied") is True
                    )
                    if same:
                        summary["www_cname"] = {
                            "status": "ok",
                            "action": "already_set",
                            "name": www_name,
                            "content": existing.get("content"),
                        }
                    else:
                        write_res = _cf_request(
                            token,
                            "PUT",
                            f"/zones/{zone_id}/dns_records/{existing['id']}",
                            body=cname_body,
                        )
                        action = "updated"
                        if not write_res.get("success"):
                            summary["www_cname"] = {
                                "status": "error",
                                "message": _augment_permission_hint(
                                    f"www CNAME {action} failed: {_errors_to_text(write_res)}",
                                    "www_dns",
                                ),
                            }
                            had_errors = True
                        else:
                            summary["www_cname"] = {
                                "status": "ok",
                                "action": action,
                                "name": www_name,
                                "content": www_cname_target,
                            }
                else:
                    write_res = _cf_request(
                        token,
                        "POST",
                        f"/zones/{zone_id}/dns_records",
                        body=cname_body,
                    )
                    action = "created"
                    if not write_res.get("success"):
                        summary["www_cname"] = {
                            "status": "error",
                            "message": _augment_permission_hint(
                                f"www CNAME {action} failed: {_errors_to_text(write_res)}",
                                "www_dns",
                            ),
                        }
                        had_errors = True
                    else:
                        summary["www_cname"] = {
                            "status": "ok",
                            "action": action,
                            "name": www_name,
                            "content": www_cname_target,
                        }

    # Pages custom domain for www (required when www CNAME targets *.pages.dev)
    if not enable_pages_www_domain:
        summary["pages_www_domain"] = {"status": "skipped", "reason": "disabled"}
    elif not account_id:
        summary["pages_www_domain"] = {
            "status": "skipped",
            "reason": "CLOUDFLARE_ACCOUNT_ID not provided",
        }
    else:
        www_host = f"www.{domain}"
        list_res = _cf_request(
            token,
            "GET",
            f"/accounts/{account_id}/pages/projects/{pages_project}/domains",
        )
        if not list_res.get("success"):
            summary["pages_www_domain"] = {
                "status": "error",
                "message": _augment_permission_hint(
                    f"Pages domain list failed: {_errors_to_text(list_res)}",
                    "pages_domain",
                ),
            }
            had_errors = True
        else:
            domains = list_res.get("result") or []
            existing_names = {
                str(d.get("name", "")).lower().rstrip(".") for d in domains
            }
            if www_host.lower() in existing_names:
                summary["pages_www_domain"] = {
                    "status": "ok",
                    "action": "already_present",
                    "name": www_host,
                }
            else:
                create_res = _cf_request(
                    token,
                    "POST",
                    f"/accounts/{account_id}/pages/projects/{pages_project}/domains",
                    body={"name": www_host},
                )
                if create_res.get("success"):
                    result = create_res.get("result") or {}
                    summary["pages_www_domain"] = {
                        "status": "ok",
                        "action": "created",
                        "name": result.get("name") or www_host,
                        "status_detail": result.get("status"),
                    }
                else:
                    summary["pages_www_domain"] = {
                        "status": "error",
                        "message": _augment_permission_hint(
                            f"Pages domain create failed: {_errors_to_text(create_res)}",
                            "pages_domain",
                        ),
                    }
                    had_errors = True

    print(json.dumps(summary, indent=2))
    return 1 if had_errors else 0


if __name__ == "__main__":
    sys.exit(main())
