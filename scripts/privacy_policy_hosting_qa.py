#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCE_POLICY = ROOT / "store/privacy_policy.html"
REPORT_JSON = ROOT / "build/reports/privacy_policy_hosting.json"
REPORT_MD = ROOT / "build/reports/privacy_policy_hosting.md"
HOSTING_DIR = ROOT / "build/privacy_policy_handoff"
HOSTING_POLICY = HOSTING_DIR / "privacy_policy.html"
HOSTING_MANIFEST = HOSTING_DIR / "manifest.json"
HOSTING_README = HOSTING_DIR / "README.md"
PRIVACY_URL_ENV = "SHAWARMA58_PRIVACY_POLICY_URL"
LOCAL_PLACEHOLDER_HOSTS = {"example.com", "localhost", "127.0.0.1", "::1"}
FORBIDDEN_TAGS = {"script", "iframe", "form", "input", "object", "embed", "link"}
REMOTE_ATTRS = {"href", "src", "action", "poster"}
FORBIDDEN_TEXT_MARKERS = [
    "google-analytics",
    "googletagmanager",
    "firebase",
    "facebook pixel",
    "metrika",
    "yandex",
    "mailto:",
    "tel:",
]
REQUIRED_TERMS = [
    "Шаурма 58",
    "командой проекта «Шаурма 58»",
    "не собирает",
    "не передаёт",
    "не продаёт",
    "не требует аккаунта",
    "не содержит рекламы",
    "не объявлено разрешение INTERNET",
    "сбросит прогресс в настройках приложения",
    "удалит приложение",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


class PolicyHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.attrs: list[tuple[str, dict[str, str]]] = []
        self.current_tag: str | None = None
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        normalized_attrs = {key.lower(): value or "" for key, value in attrs}
        self.tags.append(normalized_tag)
        self.attrs.append((normalized_tag, normalized_attrs))
        self.current_tag = normalized_tag

    def handle_endtag(self, tag: str) -> None:
        if self.current_tag == tag.lower():
            self.current_tag = None

    def handle_data(self, data: str) -> None:
        if self.current_tag == "title":
            self.title_parts.append(data)
        elif self.current_tag == "h1":
            self.h1_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self.title_parts if part.strip())

    @property
    def h1(self) -> str:
        return " ".join(part.strip() for part in self.h1_parts if part.strip())


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def status_for_absent(strict: bool) -> str:
    return "FAIL" if strict else "EXTERNAL_BLOCKER"


def parse_policy_html(text: str) -> PolicyHtmlParser:
    parser = PolicyHtmlParser()
    parser.feed(text)
    return parser


def check_source_file() -> Check:
    if not SOURCE_POLICY.exists():
        return Check("Source privacy policy file", "FAIL", f"missing {rel(SOURCE_POLICY)}")
    if SOURCE_POLICY.suffix.lower() != ".html":
        return Check("Source privacy policy file", "FAIL", "privacy policy source must be an HTML page")
    size = SOURCE_POLICY.stat().st_size
    if size < 1_500:
        return Check("Source privacy policy file", "FAIL", f"policy file is too small for a complete public policy: {size} bytes")
    if size > 128_000:
        return Check("Source privacy policy file", "FAIL", f"policy file is unexpectedly large: {size} bytes")
    return Check("Source privacy policy file", "PASS", f"{rel(SOURCE_POLICY)} exists, {size} bytes")


def check_html_structure(text: str, parser: PolicyHtmlParser) -> Check:
    missing: list[str] = []
    lowered = text.lower()
    if not lowered.lstrip().startswith("<!doctype html>"):
        missing.append("<!doctype html>")
    html_attrs = [attrs for tag, attrs in parser.attrs if tag == "html"]
    if not html_attrs or html_attrs[0].get("lang") != "ru":
        missing.append('<html lang="ru">')
    if "meta" not in parser.tags or not any(
        tag == "meta" and attrs.get("charset", "").lower() == "utf-8"
        for tag, attrs in parser.attrs
    ):
        missing.append("utf-8 meta")
    if not any(
        tag == "meta" and attrs.get("name", "").lower() == "viewport"
        for tag, attrs in parser.attrs
    ):
        missing.append("viewport meta")
    if "Шаурма 58" not in parser.title:
        missing.append("title with app name")
    if "Политика конфиденциальности" not in parser.h1 or "Шаурма 58" not in parser.h1:
        missing.append("h1 with policy/app name")
    if "main" not in parser.tags:
        missing.append("<main>")
    if missing:
        return Check("HTML document structure", "FAIL", f"missing: {', '.join(missing)}")
    return Check("HTML document structure", "PASS", "doctype, lang, metadata, title, h1 and main are present")


def remote_value(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https", "//"}


def check_publish_safe_surface(text: str, parser: PolicyHtmlParser) -> Check:
    lowered = text.lower()
    problems: list[str] = []
    forbidden_tags = sorted(set(parser.tags) & FORBIDDEN_TAGS)
    if forbidden_tags:
        problems.append(f"forbidden tags: {', '.join(forbidden_tags)}")
    for tag, attrs in parser.attrs:
        for key, value in attrs.items():
            if key.startswith("on"):
                problems.append(f"event handler attribute on <{tag}>")
            if key in REMOTE_ATTRS and remote_value(value):
                problems.append(f"remote {key} on <{tag}>: {value}")
    marker_hits = [marker for marker in FORBIDDEN_TEXT_MARKERS if marker in lowered]
    if marker_hits:
        problems.append(f"forbidden markers: {', '.join(marker_hits)}")
    if re.search(r"\bhttp://", lowered):
        problems.append("plain http URL")
    if problems:
        return Check("Publish-safe HTML surface", "FAIL", "; ".join(sorted(set(problems))))
    return Check("Publish-safe HTML surface", "PASS", "static self-contained HTML; no scripts, forms, iframes, remote assets or tracking markers")


def check_required_terms(text: str) -> Check:
    missing = [term for term in REQUIRED_TERMS if term not in text]
    if missing:
        return Check("Privacy policy terms", "FAIL", f"missing required terms: {missing}")
    return Check("Privacy policy terms", "PASS", "app identity and no-collection/no-sharing/local-reset terms are present")


def write_hosting_bundle() -> dict[str, object]:
    HOSTING_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_POLICY, HOSTING_POLICY)
    policy_sha = sha256(HOSTING_POLICY)
    manifest = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": rel(SOURCE_POLICY),
        "file": rel(HOSTING_POLICY),
        "bytes": HOSTING_POLICY.stat().st_size,
        "sha256": policy_sha,
        "requiredPublicUrlEnv": PRIVACY_URL_ENV,
    }
    HOSTING_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    HOSTING_README.write_text(
        "\n".join(
            [
                "# Privacy Policy Hosting Handoff",
                "",
                "Host `privacy_policy.html` as a public HTTPS web page. Do not convert it to PDF.",
                f"After hosting, export `{PRIVACY_URL_ENV}` with the public URL and run:",
                "",
                "```bash",
                "python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url",
                "python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url",
                "```",
                "",
                f"SHA-256: `{policy_sha}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def check_hosting_bundle(manifest: dict[str, object]) -> Check:
    if manifest.get("sha256") != sha256(SOURCE_POLICY):
        return Check("Hosting bundle copy", "FAIL", "host-ready copy checksum does not match source policy")
    return Check("Hosting bundle copy", "PASS", f"{rel(HOSTING_POLICY)} matches source SHA-256 {manifest['sha256']}")


def check_privacy_url(strict: bool, fetch: bool) -> list[Check]:
    raw = os.environ.get(PRIVACY_URL_ENV, "").strip()
    if not raw:
        return [Check("Hosted privacy policy URL", status_for_absent(strict), f"{PRIVACY_URL_ENV} is not set")]
    parsed = urlparse(raw)
    checks: list[Check] = []
    if parsed.scheme != "https":
        checks.append(Check("Hosted privacy policy URL", "FAIL", "privacy policy URL must use https"))
    host = parsed.hostname or ""
    if host.lower() in LOCAL_PLACEHOLDER_HOSTS:
        checks.append(Check("Hosted privacy policy URL", "FAIL", "privacy policy URL must not use placeholder/local host"))
    if parsed.path.lower().endswith(".pdf"):
        checks.append(Check("Hosted privacy policy URL", "FAIL", "privacy policy URL must be a web page, not a PDF"))
    if not checks:
        checks.append(Check("Hosted privacy policy URL", "PASS", "URL shape is HTTPS and non-PDF"))
    if fetch and not any(check.status == "FAIL" for check in checks):
        request = urllib.request.Request(raw, method="GET", headers={"User-Agent": "Shawarma58PrivacyQa/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(128_000).decode("utf-8", errors="ignore")
                content_type = response.headers.get("content-type", "")
                if response.status >= 400:
                    checks.append(Check("Hosted privacy policy fetch", "FAIL", f"HTTP status {response.status}"))
                elif "pdf" in content_type.lower():
                    checks.append(Check("Hosted privacy policy fetch", "FAIL", f"content-type must not be PDF: {content_type}"))
                elif "html" not in content_type.lower() and "text/plain" not in content_type.lower():
                    checks.append(Check("Hosted privacy policy fetch", "FAIL", f"unexpected content-type: {content_type}"))
                elif any(term not in body for term in ["Шаурма 58", "не собирает", "не объявлено разрешение INTERNET"]):
                    checks.append(Check("Hosted privacy policy fetch", "FAIL", "hosted page does not contain expected app/privacy terms"))
                else:
                    checks.append(Check("Hosted privacy policy fetch", "PASS", f"HTTP {response.status}; expected terms found"))
        except (urllib.error.URLError, TimeoutError) as exc:
            checks.append(Check("Hosted privacy policy fetch", "FAIL", f"could not fetch privacy policy URL: {exc}"))
    return checks


def write_reports(checks: list[Check], hosting_manifest: dict[str, object], strict: bool, fetch: bool) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    statuses = [check.status for check in checks]
    if "FAIL" in statuses:
        status = "FAIL"
    elif "EXTERNAL_BLOCKER" in statuses:
        status = "EXTERNAL_BLOCKER"
    else:
        status = "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "strict": strict,
        "fetchPrivacyUrl": fetch,
        "sourcePath": rel(SOURCE_POLICY),
        "hostingBundle": hosting_manifest,
        "hostedUrl": os.environ.get(PRIVACY_URL_ENV, "") or "<unset>",
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Privacy Policy Hosting QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Strict mode: `{strict}`",
        f"Fetch hosted URL: `{fetch}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Hosting Bundle",
            f"- Source: `{payload['sourcePath']}`",
            f"- Host-ready copy: `{hosting_manifest.get('file', '')}`",
            f"- SHA-256: `{hosting_manifest.get('sha256', '')}`",
            f"- Public URL env: `{PRIVACY_URL_ENV}` = `{payload['hostedUrl']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail when the public privacy policy URL is absent")
    parser.add_argument("--fetch-privacy-url", action="store_true", help="fetch and inspect SHAWARMA58_PRIVACY_POLICY_URL")
    args = parser.parse_args()

    checks = [check_source_file()]
    text = SOURCE_POLICY.read_text(encoding="utf-8") if SOURCE_POLICY.exists() else ""
    parser = parse_policy_html(text)
    hosting_manifest: dict[str, object] = {}
    if not any(check.status == "FAIL" for check in checks):
        checks.extend(
            [
                check_html_structure(text, parser),
                check_publish_safe_surface(text, parser),
                check_required_terms(text),
            ]
        )
        if not any(check.status == "FAIL" for check in checks):
            hosting_manifest = write_hosting_bundle()
            checks.append(check_hosting_bundle(hosting_manifest))
    checks.extend(check_privacy_url(strict=args.strict, fetch=args.fetch_privacy_url))
    write_reports(checks, hosting_manifest, strict=args.strict, fetch=args.fetch_privacy_url)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Privacy policy hosting QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)

    print("Privacy policy hosting QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {rel(REPORT_MD)}, {rel(REPORT_JSON)}")


if __name__ == "__main__":
    main()
