#!/usr/bin/env python3
"""Static checks for the generated OCI Networking workbook HTML."""

from __future__ import annotations

import re
import sys
import html as html_lib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "md"
CURRENT_DATE = "Last updated July 6, 2026"
ALLOWED_TYPES = {"SQL", "PL/SQL", "Bash", "JSON", "Text", "Output"}
HTML_CHANGE_RULE = "After a successful rebuild, copy accepted edits made directly in the generated HTML page back into this Markdown source."
RETIRED_NAMING_TERMS = ("found" + "ation",)
RETIRED_RESOURCE_NAMES = (
    "subnet-" + "bastion-admin",
    "exa" + "-xs",
    "exa" + "xs",
    "exadata" + "vcn",
    "exa" + "client",
    "exa" + "backup",
    "network-" + "production",
    "security-" + "production",
    "database-" + "production",
    "application-" + "production",
    "logging-" + "production",
    "igw-exadata",
    "sgw-exadata",
    "nat-exadata",
    "drg-exadata",
    "drg-attachment-exadata",
)
RETIRED_NAMING_PATTERNS = (
    re.compile(r"\b" + "c" + "mp-[a-z0-9-]+"),
    re.compile(r"\b[a-z0-9-]+-" + "pr" + r"od\b"),
    re.compile(r"\b" + "non" + "pr" + r"od\b"),
    re.compile(r"\b" + "pr" + r"od\b"),
)
FORBIDDEN_PUBLIC_TERMS = (
    re.compile(r"\b" + "fu" + "ture" + r"\b", flags=re.I),
    re.compile(r"\b" + "re" + "search" + r"\b", flags=re.I),
    re.compile(r"\bbest[- ]practice\b", flags=re.I),
    re.compile(r"(?<!OCI )\bconsole\b", flags=re.I),
)
FORBIDDEN_EXPORT_ASSIGNMENT = re.compile(r"^\s*export\s+[A-Z0-9_]+=", flags=re.M)
FORBIDDEN_LOCAL_CLI_ENV = re.compile(r"(\. \./cli\.env|CLI_ENV=\"\$\{CLI_ENV:-\./cli\.env\}\"|cat > cli\.env|chmod 600 cli\.env)")
FORBIDDEN_CLI_ENV_WRAPPER = re.compile(r"set -a\s*\n\s*\. ~/workbook/cli\.env\s*\n\s*set \+a")
FORBIDDEN_DIRECT_CLI_ENV_SOURCE = re.compile(r"^\s*\. ~/workbook/cli\.env\b", flags=re.M)
FORBIDDEN_EXTERNAL_WORKBOOK_ARTIFACT = re.compile(r"(mktemp \"\$\{TMPDIR:-/tmp\}/oci-|cat > (rt-|nsg-)|file://(?:rt-|nsg-))")
FORBIDDEN_COMPARTMENT_OCID_ALIAS = re.compile(r"(?<![A-Z0-9_])COMPARTMENT_OCID(?![A-Z0-9_])")
FORBIDDEN_PUBLIC_PYTHON_RUNTIME = re.compile(r"(\bpython3?\b|<<'PY')")
MARKDOWN_CODE_BLOCK = re.compile(r"```[^\n]*\n(.*?)\n```", flags=re.S)
MARKDOWN_FENCED_BLOCK = re.compile(r"```([^\n]*)\n(.*?)\n```", flags=re.S)
PUBLIC_INTERNAL_PHRASES = {
    "Markdown source",
    "Markdown Sources",
    "Maintenance Workflow",
    "Editable Markdown sources",
    "Static HTML",
    "Version: 1.0",
    "Generated: 2026-06-19",
    "Source material",
    "supplied with the request",
    "Downstream dependency",
    "OCI_Networking.md",
    "Source Workbook Sections Used",
    "downstream",
    "Workbook Manifest",
    "Handoff Contract for the Exadata Exascale Workbook",
    "Those topics remain in the " + "fu" + "ture Exadata Exascale workbook",
    "fu" + "ture Exadata Exascale workbook",
    "fu" + "ture Exadata workbook",
    "later Exadata Exascale workbook",
    "fu" + "ture workbook",
    "Prefer TCPS on 2484",
    "1521 can be enabled",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def front_matter(path: Path) -> dict[str, str]:
    lines = read(path).splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line.startswith(" "):
            continue
        key, raw = line.split(":", 1)
        values[key.strip()] = raw.strip().strip('"')
    return values


def code_cards(html: str) -> list[str]:
    return re.findall(r'<div class="code-card">(.*?)</div>\s*</div>', html, flags=re.S)


def retired_naming_errors(label: Path | str, text: str) -> list[str]:
    errors: list[str] = []
    lower_text = text.lower()
    for term in RETIRED_NAMING_TERMS:
        if term in lower_text:
            errors.append(f"{label}: retired naming term remains")
    for term in RETIRED_RESOURCE_NAMES:
        if term in lower_text:
            errors.append(f"{label}: retired resource naming remains")
    for pattern in RETIRED_NAMING_PATTERNS:
        if pattern.search(lower_text):
            errors.append(f"{label}: retired naming token remains")
    for pattern in FORBIDDEN_PUBLIC_TERMS:
        if pattern.search(text):
            errors.append(f"{label}: retired workbook process term remains")
    if FORBIDDEN_EXPORT_ASSIGNMENT.search(text):
        errors.append(f"{label}: use cli.env instead of direct shell export assignments")
    errors.extend(direct_oci_create_errors(label, text))
    if FORBIDDEN_LOCAL_CLI_ENV.search(text):
        errors.append(f"{label}: use ~/workbook/cli.env instead of a local cli.env path")
    if FORBIDDEN_CLI_ENV_WRAPPER.search(text):
        errors.append(f"{label}: load self-exporting cli.env with a single source command")
    if FORBIDDEN_DIRECT_CLI_ENV_SOURCE.search(text):
        errors.append(f"{label}: source ~/workbook/helpers.sh and call load_cli_env instead of sourcing cli.env directly")
    if FORBIDDEN_EXTERNAL_WORKBOOK_ARTIFACT.search(text):
        errors.append(f"{label}: store workbook-generated artifacts under ~/workbook")
    if FORBIDDEN_COMPARTMENT_OCID_ALIAS.search(text):
        errors.append(f"{label}: use explicit compartment variables such as NETWORK_COMPARTMENT_OCID")
    return errors


def multiline_oci_command_errors(label: Path | str, code: str, start_line: int = 1) -> list[str]:
    errors: list[str] = []
    for offset, line in enumerate(code.splitlines()):
        stripped = line.strip()
        if stripped == "oci --version":
            continue
        has_oci_command = re.search(r"(^|[;&|]\s*)oci\s+", stripped)
        has_wrapped_capture = "capture_oci_id" in stripped and " oci " in stripped
        if (has_oci_command or has_wrapped_capture) and "--" in stripped:
            errors.append(f"{label}:{start_line + offset}: display OCI commands over multiple indented lines")
    return errors


def direct_oci_create_errors(label: Path | str, text: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^\s*oci\s+.+\bcreate\b", line):
            continue
        previous = ""
        for prior in reversed(lines[:index]):
            if prior.strip():
                previous = prior.strip()
                break
        if "capture_oci_id" in previous and previous.endswith("\\"):
            continue
        window = "\n".join(lines[max(0, index - 1) : min(len(lines), index + 80)])
        uses_assignment_capture = re.search(r'[A-Z0-9_]+="\$\(\s*$', previous) is not None
        has_data_id_query = "--query 'data.id'" in window or '--query "data.id"' in window
        has_raw_output = "--raw-output" in window
        has_upsert = "upsert_cli_env" in window
        if not has_data_id_query:
            continue
        if uses_assignment_capture and has_data_id_query and has_raw_output and has_upsert:
            continue
        errors.append(f"{label}: save OCI create data.id with capture_oci_id or assignment plus upsert_cli_env")
    return errors


def validate_html(path: Path) -> list[str]:
    errors: list[str] = []
    text = read(path)
    rel = path.relative_to(ROOT)

    if '<link rel="icon" href="data:,">' not in text:
        errors.append(f"{rel}: missing favicon guard")
    if CURRENT_DATE not in text:
        errors.append(f"{rel}: missing current visible Last updated label")
    if "Blog last updated" in text:
        errors.append(f"{rel}: stale Blog last updated wording")
    hero_meta_match = re.search(r'<div class="hero-meta">(.*?)</div>', text, flags=re.S)
    if not hero_meta_match:
        errors.append(f"{rel}: missing hero metadata row")
    else:
        pills = re.findall(r"<span>(.*?)</span>", hero_meta_match.group(1), flags=re.S)
        if pills != [CURRENT_DATE]:
            errors.append(f"{rel}: hero metadata must contain only {CURRENT_DATE!r}; found {pills!r}")
    if "135deg" not in text and "workbook.css" not in text:
        errors.append(f"{rel}: missing Oracle 135deg hero/header gradient")
    if "rgba(199, 70, 52" not in text and "workbook.css" not in text:
        errors.append(f"{rel}: missing Oracle red gradient token")
    for phrase in PUBLIC_INTERNAL_PHRASES:
        if phrase in text:
            errors.append(f"{rel}: public HTML contains internal phrase {phrase!r}")
    errors.extend(retired_naming_errors(rel, text))

    pre_count = len(re.findall(r"<pre\b", text))
    card_count = len(re.findall(r'class="code-card"', text))
    if pre_count != card_count:
        errors.append(f"{rel}: every pre must be inside exactly one code-card ({pre_count} pre, {card_count} cards)")

    for match in re.finditer(r'<div class="code-card">(.*?)</div>\s*</div>', text, flags=re.S):
        card = match.group(0)
        line = text[: match.start()].count("\n") + 1
        if len(re.findall(r'class="code-toolbar"', card)) != 1:
            errors.append(f"{rel}:{line}: code-card must contain exactly one code-toolbar")
        if len(re.findall(r'class="copy-btn"', card)) != 1:
            errors.append(f"{rel}:{line}: code-card must contain exactly one copy-btn")
        if len(re.findall(r'class="code-description code-objective"', card)) != 1:
            errors.append(f"{rel}:{line}: code-card must contain exactly one objective row")
        if len(re.findall(r'<pre class="code-scroll"><code>', card)) != 1:
            errors.append(f"{rel}:{line}: code-card must contain one pre.code-scroll code block")

        type_match = re.search(r'<span class="code-type">([^<]+)</span>', card)
        if not type_match or type_match.group(1) not in ALLOWED_TYPES:
            errors.append(f"{rel}:{line}: code toolbar label must be type-only")

        objective_match = re.search(r'<span class="objective-label">Objective:</span>\s*([^<\n][^<]*)', card)
        if not objective_match:
            errors.append(f"{rel}:{line}: objective text missing after label")
        else:
            objective_text = objective_match.group(1).strip()
            first = re.search(r"[A-Za-z]", objective_text)
            if first and first.group(0).islower():
                errors.append(f"{rel}:{line}: objective text starts lowercase")

        code_match = re.search(r"<pre class=\"code-scroll\"><code>(.*?)</code></pre>", card, flags=re.S)
        if code_match:
            code = html_lib.unescape(re.sub(r"<[^>]+>", "", code_match.group(1))).lstrip()
            errors.extend(multiline_oci_command_errors(rel, code, line))
            if re.match(r"(?i)(#|--|//)\s*check\b", code):
                errors.append(f"{rel}:{line}: code snippet starts with redundant purpose comment")
            setup_lines = [
                "SET LINESIZE 220",
                "SET PAGESIZE 100",
                "SET TRIMSPOOL ON",
                "SET TAB OFF",
            ]
            if type_match and type_match.group(1) in {"SQL", "PL/SQL"}:
                for setup in setup_lines:
                    if code.count(setup) > 1:
                        errors.append(f"{rel}:{line}: duplicate SQL*Plus setup line {setup}")

    if re.search(r"<p>[^<]*Objective:", text):
        errors.append(f"{rel}: body paragraph contains Objective text outside a code-card")
    if "line-number" in text or "hljs-ln" in text:
        errors.append(f"{rel}: generated line-number runtime or classes are not allowed")
    if "copy-btn" in text:
        copy_js = read(ROOT / "assets" / "workbook.js")
        if 'querySelector("pre code")' not in copy_js or ".textContent" not in copy_js:
            errors.append(f"{rel}: copy handler must copy only pre code.textContent")
    if "table-wrap" not in text and "<table" in text:
        errors.append(f"{rel}: tables must be wrapped in table-wrap")
    if "Deployment Readiness Record" in text:
        if 'class="article-section saveable-section"' not in text:
            errors.append(f"{rel}: deployment readiness record must be a saveable section")
        if 'class="save-section-btn"' not in text:
            errors.append(f"{rel}: deployment readiness record missing save button")
        if 'data-save-file="exascale-deployment-readiness-record.txt"' not in text:
            errors.append(f"{rel}: deployment readiness record must use short save filename")
    if "chapter-card-nav" not in text and rel != Path("index.html"):
        errors.append(f"{rel}: chapter page missing Main/Previous/Next card navigation")
    if rel != Path("index.html"):
        nav_count = len(re.findall(r'class="chapter-nav chapter-card-nav"', text))
        if nav_count != 2:
            errors.append(f"{rel}: chapter page must contain top and bottom card navigation ({nav_count} found)")
        if "Related modules" in text:
            errors.append(f"{rel}: stale Related modules section must be replaced by card navigation")
        if 'aria-label="Related workbook modules"' in text:
            errors.append(f"{rel}: stale related-module registry placeholder remains")
        if "Module navigation" in text or "module-navigation" in text or re.search(r">Module \d{2}<", text):
            errors.append(f"{rel}: stale Module label remains in chapter chrome")
    for match in re.finditer(r'<a class="related-link"[^>]*>(.*?)</a>', text, flags=re.S):
        if "<span" in match.group(1):
            line = text[: match.start()].count("\n") + 1
            errors.append(f"{rel}:{line}: module navigation card must contain names only")
    for match in re.finditer(r'<a class="content-card link-card"[^>]*>(.*?)</a>', text, flags=re.S):
        if "<span" in match.group(1):
            line = text[: match.start()].count("\n") + 1
            errors.append(f"{rel}:{line}: series link card must contain names only")
    for match in re.finditer(r'<(?:a|span) class="chapter-link nav-card[^"]*"[^>]*>(.*?)</(?:a|span)>', text, flags=re.S):
        card = match.group(1)
        if re.search(r'<span(?! class="nav-card-label")', card):
            line = text[: match.start()].count("\n") + 1
            errors.append(f"{rel}:{line}: chapter navigation card must contain names only")
    return errors


def validate_css() -> list[str]:
    css_path = ROOT / "assets" / "workbook.css"
    errors: list[str] = []
    if not css_path.exists():
        return ["assets/workbook.css: missing stylesheet"]
    css = read(css_path)
    required = [
        "linear-gradient(135deg, rgba(199, 70, 52",
        ".code-card",
        ".code-toolbar",
        ".code-type",
        ".copy-btn",
        ".code-description",
        ".objective-label",
        ".code-scroll::-webkit-scrollbar",
        ".chapter-card-nav",
        ".nav-card-label",
        ".save-section-btn",
        "overflow-x: auto",
        "grid-template-columns: 280px minmax(0, 1fr)",
    ]
    for token in required:
        if token not in css:
            errors.append(f"assets/workbook.css: missing required token {token!r}")
    if "letter-spacing: -" in css:
        errors.append("assets/workbook.css: negative letter spacing is not allowed")
    js = read(ROOT / "assets" / "workbook.js") if (ROOT / "assets" / "workbook.js").exists() else ""
    for token in [
        '".save-section-btn"',
        "new Blob",
        "text/plain;charset=utf-8",
        ".saveable-section",
        "fixedWidthTable",
        "padEnd",
        "toUpperCase",
    ]:
        if token not in js:
            errors.append(f"assets/workbook.js: missing save-section token {token!r}")
    shared_js = read(ROOT / "shared-guide-set.js") if (ROOT / "shared-guide-set.js").exists() else ""
    for token in ['"description"', "descriptionClassName"]:
        if token in shared_js:
            errors.append(f"shared-guide-set.js: navigation cards must not include {token!r}")
    return errors


def validate_sources() -> list[str]:
    errors: list[str] = []
    source_files = sorted(SOURCE_DIR.glob("[0-9][0-9]_*.md"))
    expected_numbers = {f"{number:02d}" for number in range(16)}
    actual_numbers = {path.name[:2] for path in source_files}
    if actual_numbers != expected_numbers:
        errors.append(
            "md/: expected PoC numbered Markdown sources "
            f"{sorted(expected_numbers)}, found {sorted(actual_numbers)}"
        )
    runbook_text = read(SOURCE_DIR / "05_Network.md")
    runbook_cards = {
        f"{match.group(1).upper()} {int(match.group(2)):02d}"
        for match in re.finditer(r"^((?:BASH|OUTPUT))\s+(\d{1,2})\s+-\s+.+?:\s*Objective:", runbook_text, flags=re.M)
    }
    for path in source_files:
        rel = path.relative_to(ROOT)
        source_text = read(path)
        errors.extend(retired_naming_errors(rel, source_text))
        for marker in re.finditer(r"::runbook-card\s+(BASH|OUTPUT)\s+(\d{1,2})", source_text, flags=re.I):
            card_key = f"{marker.group(1).upper()} {int(marker.group(2)):02d}"
            if card_key not in runbook_cards:
                errors.append(f"{rel}: runbook card marker references missing {card_key}")
        for block in MARKDOWN_FENCED_BLOCK.finditer(source_text):
            language = block.group(1).strip().lower()
            code_start = source_text[: block.start(2)].count("\n") + 1
            code = block.group(2)
            source_number = path.name[:2]
            if (
                language in {"bash", "sh", "shell", "zsh"}
                and source_number in {"01", "02", "03", "04"}
            ):
                errors.append(f"{rel}:{code_start}: use ::runbook-card markers instead of local Bash command cards")
            errors.extend(multiline_oci_command_errors(rel, code, code_start))
            if FORBIDDEN_PUBLIC_PYTHON_RUNTIME.search(code):
                errors.append(f"{rel}:{code_start}: use Bash and OCI CLI query output instead of Python runtime snippets")
        metadata = front_matter(path)
        if metadata.get("source_of_record") != "true":
            errors.append(f"{rel}: missing source_of_record metadata")
        generated_html = metadata.get("generated_html", "")
        if not generated_html:
            errors.append(f"{rel}: missing generated_html metadata")
        elif not (ROOT / generated_html).is_file():
            errors.append(f"{rel}: generated_html target does not exist: {generated_html}")
        if metadata.get("html_change_rule") != HTML_CHANGE_RULE:
            errors.append(f"{rel}: missing or incorrect HTML-to-Markdown change rule")

    overview = read(SOURCE_DIR / "00_Project_Overview.md")
    addressing = read(SOURCE_DIR / "03_Addressing_and_DNS.md")
    readme = read(SOURCE_DIR / "README.md")
    maintenance = read(ROOT / "WORKBOOK_SOURCE_AND_MAINTENANCE.md") if (ROOT / "WORKBOOK_SOURCE_AND_MAINTENANCE.md").exists() else ""
    for label, text in [
        ("md/00_Project_Overview.md", overview),
        ("md/README.md", readme),
        ("WORKBOOK_SOURCE_AND_MAINTENANCE.md", maintenance),
    ]:
        lower = text.lower()
        errors.extend(retired_naming_errors(label, text))
        if "source of knowledge" not in lower and "source of record" not in lower and "source_of_record" not in lower:
            errors.append(f"{label}: missing source-of-record/source-of-knowledge guidance")
    if "After a successful rebuild, copy accepted direct HTML edits back into the matching Markdown source" not in maintenance:
        errors.append("WORKBOOK_SOURCE_AND_MAINTENANCE.md: missing post-rebuild HTML-to-Markdown maintenance rule")
    if "After a successful rebuild, copy accepted edits made directly in generated HTML back into the matching Markdown source" not in readme:
        errors.append("md/README.md: missing post-rebuild HTML-to-Markdown maintenance rule")
    if "cli.env" not in overview:
        errors.append("md/00_Project_Overview.md: missing cli.env shell variable standard")
    if "mkdir -p ~/workbook" not in overview or "cat > ~/workbook/cli.env" not in overview:
        errors.append("md/00_Project_Overview.md: missing ~/workbook/cli.env creation standard")
    if "cat > ~/workbook/cli.env <<'EOF'\nset -a" not in overview or "\nset +a\nEOF" not in overview:
        errors.append("md/00_Project_Overview.md: cli.env template must self-export variables")
    if 'CLI_ENV="${CLI_ENV:-$WORKBOOK_DIR/cli.env}"' not in overview:
        errors.append("md/00_Project_Overview.md: missing ~/workbook/cli.env helper default")
    if "cat > ~/workbook/helpers.sh" not in overview or "WORKBOOK_DIR=\"${WORKBOOK_DIR:-$HOME/workbook}\"" not in overview:
        errors.append("md/00_Project_Overview.md: missing ~/workbook/helpers.sh helper standard")
    if "capture_oci_id` is a workbook helper function" not in overview or "not part of OCI CLI" not in overview:
        errors.append("md/00_Project_Overview.md: missing capture_oci_id helper explanation")
    for required_variable in ["TENANCY_ID", "REGION"]:
        if required_variable not in overview:
            errors.append(f"md/00_Project_Overview.md: missing {required_variable} prerequisite guidance")
    if "NETWORK_COMPARTMENT_OCID" not in runbook_text:
        errors.append("md/05_Network.md: missing NETWORK_COMPARTMENT_OCID implementation alias guidance")
    if "cli.env" not in readme:
        errors.append("md/README.md: missing cli.env maintenance guidance")
    if "~/workbook/cli.env" not in readme:
        errors.append("md/README.md: missing ~/workbook/cli.env maintenance guidance")
    if "~/workbook/helpers.sh" not in readme:
        errors.append("md/README.md: missing ~/workbook/helpers.sh maintenance guidance")
    if "set -a" not in readme or "set +a" not in readme:
        errors.append("md/README.md: missing self-exporting cli.env guidance")
    if "cli.env" not in maintenance:
        errors.append("WORKBOOK_SOURCE_AND_MAINTENANCE.md: missing cli.env maintenance guidance")
    if "~/workbook/cli.env" not in maintenance:
        errors.append("WORKBOOK_SOURCE_AND_MAINTENANCE.md: missing ~/workbook/cli.env maintenance guidance")
    if "~/workbook/helpers.sh" not in maintenance:
        errors.append("WORKBOOK_SOURCE_AND_MAINTENANCE.md: missing ~/workbook/helpers.sh maintenance guidance")
    if "capture_oci_id" not in overview or "mktemp" not in overview or 'upsert_cli_env "$KEY" "$VALUE"' not in overview:
        errors.append("md/00_Project_Overview.md: missing automatic OCI output capture helper")
    if "poc.oraclevcn.com" not in overview or "poc.oraclevcn.com" not in addressing:
        errors.append("Markdown source: missing poc.oraclevcn.com VCN DNS domain standard")
    for domain in [
        "admin.poc.oraclevcn.com",
        "client.poc.oraclevcn.com",
        "backup.poc.oraclevcn.com",
    ]:
        if domain not in addressing:
            errors.append(f"md/03_Addressing_and_DNS.md: missing {domain} DNS domain standard")
    if "capture_oci_id" not in readme:
        errors.append("md/README.md: missing capture_oci_id maintenance guidance")
    if "capture_oci_id" not in maintenance:
        errors.append("WORKBOOK_SOURCE_AND_MAINTENANCE.md: missing capture_oci_id maintenance guidance")
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: static_html_validator.py <html> [<html> ...]", file=sys.stderr)
        return 2
    errors = validate_css()
    errors.extend(validate_sources())
    for arg in argv:
        path = Path(arg)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.is_file() and path.suffix == ".html":
            errors.extend(validate_html(path))
        else:
            errors.append(f"{arg}: not an HTML file")
    if errors:
        print("Checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Static checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
