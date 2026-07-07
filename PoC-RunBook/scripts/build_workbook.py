#!/usr/bin/env python3
"""Build the static OCI PoC RunBook from the Markdown source files."""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "md"
ASSETS_DIR = ROOT / "assets"
TODAY_LABEL = "July 6, 2026"
SERIES_TITLE = "OCI PoC RunBook"
SERIES_SUBTITLE = "Workbook"
NOTICE_TITLE = "Educational use and validation required"
NOTICE_BODY = (
    "This content is for educational and planning purposes only. Apply every command and "
    "configuration first in a non-production test environment that mirrors your target "
    "platform, product version, network, security, workload, integration, and failover "
    "requirements. The recommended values shown here may not work in your specific "
    "environment, may require change-control approval, and can affect availability, "
    "performance, security, routing, transaction behavior, resource use, or operational "
    "placement. Validate with application owners, administrators, network teams, security "
    "teams, and vendor support guidance before using any setting in production."
)


DOC_LINKS = [
    (
        "Exadata Exascale Readiness",
        [
            (
                "Preparing for Oracle Exadata Database Service on Exascale Infrastructure",
                "https://docs.oracle.com/en-us/iaas/exadb-xs/doc/preparing-for-exadb-xs-deployment.html",
                "VCN, client subnet, backup subnet, private subnet, Service Gateway, and DNS planning.",
            )
        ],
    ),
    (
        "OCI Networking Security",
        [
            (
                "Securing Networking: VCN, Load Balancers, and DNS",
                "https://docs.oracle.com/en-us/iaas/Content/Security/Reference/networking_security.htm",
                "Security posture for VCNs, public and private subnets, route rules, and DNS.",
            ),
            (
                "Network Security Groups",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/networksecuritygroups.htm",
                "NSG concepts and component-level security rule design.",
            ),
            (
                "Security Rules",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securityrules.htm",
                "Stateful and stateless rule behavior for NSGs and security lists.",
            ),
            (
                "Security Lists",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm",
                "Security-list guardrails and default security-list review.",
            ),
        ],
    ),
    (
        "Routing and Private Service Access",
        [
            (
                "VCN Route Tables",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingroutetables.htm",
                "Route table design and custom route table management.",
            ),
            (
                "Working with VCN Route Tables and Route Rules",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingroutetables_topic-working.htm",
                "Route targets including DRG, Internet Gateway, NAT Gateway, and Service Gateway.",
            ),
            (
                "Service Gateway",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/servicegateway.htm",
                "Private access from a VCN to supported Oracle Services Network services.",
            ),
        ],
    ),
    (
        "Operations, Bastion, and Governance",
        [
            (
                "VCN Flow Logs",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/vcn-flow-logs.htm",
                "Flow log enablement for network troubleshooting and security investigation.",
            ),
            (
                "Use OCI Bastion Service",
                "https://docs.oracle.com/en/solutions/use-bastion-service/index.html",
                "Managed, audited private administrator access pattern.",
            ),
            (
                "Bastion Overview",
                "https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm",
                "OCI Bastion service behavior and session model.",
            ),
            (
                "CIS OCI Benchmark Landing Zone",
                "https://docs.oracle.com/en/solutions/cis-oci-benchmark/index.html",
                "Compartment, security, Cloud Guard, and landing-zone posture.",
            ),
            (
                "OCI Zero Trust Packet Routing Overview",
                "https://docs.oracle.com/en-us/iaas/Content/zero-trust-packet-routing/overview.htm",
                "Optional ZPR overlay and security-attribute caution.",
            ),
        ],
    ),
    (
        "Secrets and Key Management",
        [
            (
                "OCI Vault and Key Management Overview",
                "https://docs.oracle.com/en-us/iaas/Content/KeyManagement/Concepts/keyoverview.htm",
                "Vault and key management context for private service access.",
            ),
            (
                "Managing Secrets",
                "https://docs.oracle.com/en-us/iaas/Content/KeyManagement/Tasks/managingsecrets.htm",
                "Secret management context for target database and application deployments.",
            ),
        ],
    ),
]


GLOSSARY_GROUPS = [
    (
        "Network Baseline",
        [
            (
                "VCN",
                "A Virtual Cloud Network that provides the private network boundary for OCI resources.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingVCNs.htm",
            ),
            (
                "CIDR",
                "The IP address range assigned to the VCN, subnet, or routed network segment.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingVCNs.htm",
            ),
            (
                "Subnet",
                "A subdivision of the VCN used to isolate resource roles, routing, and public or private posture.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingVCNs.htm",
            ),
            (
                "DNS label",
                "The VCN or subnet label used to form internal OCI hostnames under oraclevcn.com.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/dns.htm",
            ),
        ],
    ),
    (
        "Routing and Gateways",
        [
            (
                "Service Gateway",
                "An OCI gateway that lets private resources reach supported Oracle services without public internet traversal.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/servicegateway.htm",
            ),
            (
                "Internet Gateway",
                "The route target used by public subnets that require internet ingress or egress.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingIGs.htm",
            ),
            (
                "NAT Gateway",
                "An outbound-only gateway for private resources that must reach public endpoints not available through Service Gateway.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/NATgateway.htm",
            ),
            (
                "DRG",
                "A Dynamic Routing Gateway that connects the VCN to on-premises, hub, VPN, FastConnect, or peered networks.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingDRGs.htm",
            ),
            (
                "Oracle Services Network",
                "The Oracle service address space used by Service Gateway route rules for private service access.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/servicegateway.htm",
            ),
        ],
    ),
    (
        "Security and Operations",
        [
            (
                "NSG",
                "A Network Security Group that applies security rules to selected VNICs instead of every resource in a subnet.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/networksecuritygroups.htm",
            ),
            (
                "Security list",
                "A subnet-level security rule set used here as a guardrail while NSGs remain the primary control.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm",
            ),
            (
                "OCI Bastion",
                "A managed service for time-bound, audited private access to resources without persistent public jump hosts.",
                "https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm",
            ),
            (
                "VCN Flow Logs",
                "OCI logs that record accepted and rejected network flows for selected VNICs or subnets.",
                "https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/vcn-flow-logs.htm",
            ),
            (
                "Cloud Guard",
                "OCI security posture service used to monitor risky changes such as public exposure or overly broad ingress.",
                "https://docs.oracle.com/en-us/iaas/cloud-guard/home.htm",
            ),
            (
                "Zero Trust Packet Routing",
                "An optional OCI network policy overlay based on security attributes and ZPR policies.",
                "https://docs.oracle.com/en-us/iaas/Content/zero-trust-packet-routing/overview.htm",
            ),
        ],
    ),
    (
        "Exadata Readiness",
        [
            (
                "ExaDB-XS",
                "Oracle Exadata Database Service on Exascale Infrastructure, the target that will consume this network baseline.",
                "https://docs.oracle.com/en-us/iaas/exadb-xs/doc/preparing-for-exadb-xs-deployment.html",
            ),
            (
                "SCAN",
                "Single Client Access Name, a database client connection abstraction that depends on correct network and DNS planning.",
                "https://docs.oracle.com/en/database/oracle/oracle-database/26/rilin/about-scan.html",
            ),
            (
                "TCPS",
                "Encrypted Oracle Net connectivity commonly associated with production listener hardening on port 2484.",
                "https://docs.oracle.com/en/database/oracle/oracle-database/26/netag/configuring-secure-sockets-layer-authentication.html",
            ),
        ],
    ),
]


@dataclass
class Chapter:
    source: Path
    number: str
    title: str
    short_title: str
    slug: str
    summary: str
    sections: list[tuple[str, list[str]]]


@dataclass
class RunbookCard:
    key: str
    title: str
    objective: str
    language: str
    code: str


RUNBOOK_CARD_CACHE: dict[str, RunbookCard] | None = None


def strip_front_matter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[idx + 1 :])
    return text


def front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def slugify(value: str) -> str:
    text = value.lower()
    text = re.sub(r"chapter\s+\d+\s*-\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "section"


def html_attr(value: str) -> str:
    return html.escape(value, quote=True)


def nav_card(label: str, title: str, href: str | None = None) -> str:
    content = (
        f'<span class="nav-card-label">{html.escape(label)}</span>'
        f"<strong>{html.escape(title)}</strong>"
    )
    if href:
        return f'<a class="chapter-link nav-card" href="{html_attr(href)}">{content}</a>'
    return f'<span class="chapter-link nav-card is-disabled" aria-disabled="true">{content}</span>'


def render_chapter_card_nav(chapter: Chapter, chapters: list[Chapter]) -> str:
    idx = chapters.index(chapter)
    cards = [
        nav_card(
            "Main",
            "Workbook home",
            "../index.html",
        )
    ]
    if idx > 0:
        prev = chapters[idx - 1]
        cards.append(nav_card("Previous", f"{prev.number}. {prev.short_title}", f"../{prev.slug}/index.html"))
    else:
        cards.append(nav_card("Previous", "Start of workbook"))
    if idx + 1 < len(chapters):
        nxt = chapters[idx + 1]
        cards.append(nav_card("Next", f"{nxt.number}. {nxt.short_title}", f"../{nxt.slug}/index.html"))
    else:
        cards.append(nav_card("Next", "End of workbook"))
    return f"""<nav class="chapter-nav chapter-card-nav" aria-label="Chapter navigation">
        {''.join(cards)}
      </nav>"""


def is_saveable_section(title: str) -> bool:
    normalized = title.lower()
    return "readiness record" in normalized or "readiness values" in normalized or "handoff" in normalized


def save_file_name_for(title: str) -> str:
    if slugify(title) == "deployment-readiness-record":
        return "exascale-deployment-readiness-record.txt"
    return f"{slugify(title)}.txt"


def inline_markup(value: str) -> str:
    placeholders: list[str] = []

    def preserve(fragment: str) -> str:
        placeholders.append(fragment)
        return f"@@HTML{len(placeholders) - 1}@@"

    def code_repl(match: re.Match[str]) -> str:
        return preserve(f"<code>{html.escape(match.group(1), quote=False)}</code>")

    text = re.sub(r"`([^`]+)`", code_repl, value)

    def link_repl(match: re.Match[str]) -> str:
        label = inline_markup(match.group(1))
        href = html_attr(match.group(2))
        attrs = ' target="_blank" rel="noopener"' if re.match(r"^https?://", match.group(2)) else ""
        return preserve(f'<a href="{href}"{attrs}>{label}</a>')

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    for idx, replacement in enumerate(placeholders):
        text = text.replace(f"@@HTML{idx}@@", replacement)
    return text


def parse_markdown_table(lines: list[str]) -> str:
    def split_row(row: str) -> list[str]:
        cells = row.strip().strip("|").split("|")
        return [cell.strip() for cell in cells]

    def alignment_for(cell: str) -> str | None:
        marker = cell.strip()
        if not re.fullmatch(r":?-{3,}:?", marker):
            return None
        if marker.startswith(":") and marker.endswith(":"):
            return "center"
        if marker.endswith(":"):
            return "right"
        if marker.startswith(":"):
            return "left"
        return None

    def attrs_for(idx: int, base_class: str | None = None) -> str:
        classes = []
        if base_class:
            classes.append(base_class)
        if idx in alignments:
            classes.append(f"align-{alignments[idx]}")
        if not classes:
            return ""
        return f' class="{" ".join(classes)}"'

    rows = [split_row(line) for line in lines if line.strip()]
    if len(rows) < 2:
        return ""
    header = rows[0]
    separator = split_row(lines[1]) if len(lines) > 1 else []
    alignments = {
        idx: alignment
        for idx, cell in enumerate(separator)
        if (alignment := alignment_for(cell)) is not None
    }
    status_columns = {idx for idx, cell in enumerate(header) if cell.strip().lower() == "status"}
    body = rows[2:] if re.fullmatch(r"[:\-\s|]+", lines[1].strip()) else rows[1:]
    out = ['<div class="table-wrap">', '<table class="data-table">', "<thead><tr>"]
    for idx, cell in enumerate(header):
        class_attr = attrs_for(idx, "status-col" if idx in status_columns else None)
        out.append(f'<th scope="col"{class_attr}>{inline_markup(cell)}</th>')
    out.append("</tr></thead>")
    out.append("<tbody>")
    for row in body:
        out.append("<tr>")
        for idx, cell in enumerate(row):
            class_attr = attrs_for(idx, "status-cell" if idx in status_columns else None)
            rendered_cell = inline_markup(cell)
            if idx in status_columns:
                rendered_cell = rendered_cell.replace("[  ]", "[&nbsp;&nbsp;]")
            out.append(f"<td{class_attr}>{rendered_cell}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def code_type_for(language: str, objective_context: str) -> str:
    lang = language.lower()
    if lang == "output":
        return "Output"
    if "expected" in objective_context.lower():
        return "Output"
    if lang in {"bash", "sh", "shell", "zsh"}:
        return "Bash"
    if lang in {"json"}:
        return "JSON"
    if lang in {"sql", "plsql", "pl/sql"}:
        return "SQL" if lang == "sql" else "PL/SQL"
    return "Text"


def objective_for_code(language: str, heading: str, previous_text: str, pending: str | None) -> str:
    if pending:
        objective = pending.strip()
    elif previous_text.lower().startswith("expected result"):
        objective = f"Review the expected output for {heading}."
    elif language.lower() in {"bash", "sh", "shell", "zsh"}:
        objective = f"Run or adapt this CLI pattern for {heading}."
    elif language.lower() == "json":
        objective = f"Use this JSON example for {heading}."
    elif language.lower() == "mermaid":
        objective = "Review the logical architecture flow for the workbook."
    else:
        objective = f"Review this text pattern for {heading}."
    objective = objective.strip()
    return objective[:1].upper() + objective[1:]


def render_code_card(language: str, code: str, objective: str, collapsed: bool = False, copyable: bool = True) -> str:
    code_type = code_type_for(language, objective)
    if code_type == "Output":
        collapsed = False
        copyable = False
    escaped = html.escape(code.rstrip("\n"), quote=False)
    collapse_attrs = ' data-collapsible="true" data-collapsed="true"' if collapsed else ""
    objective_toggle = (
        '\n    <button class="code-toggle-btn" type="button" aria-expanded="false">Expand</button>'
        if collapsed
        else ""
    )
    copy_button = "" if not copyable else '\n    <button class="copy-btn" type="button">Copy</button>'
    return f"""<div class="code-card"{collapse_attrs}>
  <div class="code-toolbar">
    <span class="code-type">{code_type}</span>{copy_button}
  </div>
  <div class="code-description code-objective">
    <span class="code-objective-text"><span class="objective-label">Objective:</span> {inline_markup(objective)}</span>{objective_toggle}
  </div>
  <pre class="code-scroll"><code>{escaped}</code></pre>
</div>"""


def load_runbook_cards() -> dict[str, RunbookCard]:
    global RUNBOOK_CARD_CACHE
    if RUNBOOK_CARD_CACHE is not None:
        return RUNBOOK_CARD_CACHE

    source = SOURCE_DIR / "05_Network.md"
    lines = strip_front_matter(source.read_text(encoding="utf-8")).splitlines()
    cards: dict[str, RunbookCard] = {}
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        match = re.match(r"^((?:BASH|OUTPUT)\s+(\d{1,2}))\s+-\s+(.+?):\s*Objective:\s*(.+)$", stripped)
        if not match:
            i += 1
            continue
        key = f"{match.group(1).split()[0]} {int(match.group(2)):02d}"
        title = match.group(3).strip()
        objective = match.group(4).strip()
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines) or not lines[j].strip().startswith("```"):
            i += 1
            continue
        language = lines[j].strip().strip("`").strip() or "text"
        j += 1
        code_lines: list[str] = []
        while j < len(lines) and not lines[j].strip().startswith("```"):
            code_lines.append(lines[j])
            j += 1
        cards[key] = RunbookCard(
            key=key,
            title=title,
            objective=objective,
            language=language,
            code="\n".join(code_lines),
        )
        i = j + 1
    RUNBOOK_CARD_CACHE = cards
    return cards


def render_runbook_card(kind: str, number: str, collapsed: bool = False) -> str:
    key = f"{kind.upper()} {int(number):02d}"
    card = load_runbook_cards().get(key)
    if card is None:
        raise ValueError(f"Runbook card {key} was requested but was not found in md/05_Network.md")
    heading = f"{card.key} - {card.title}"
    language = "output" if kind.upper() == "OUTPUT" else card.language
    return f"<h3>{inline_markup(heading)}</h3>\n{render_code_card(language, card.code, card.objective, collapsed=collapsed)}"


def render_logical_architecture_infographic() -> str:
    return """<div class="architecture-infographic" aria-label="Logical OCI network architecture infographic">
  <div class="architecture-stage architecture-stage-external">
    <p class="visual-caption">Entry points</p>
    <div class="architecture-node node-admin">
      <span class="node-icon" aria-hidden="true">ADM</span>
      <strong>Administrator workstation</strong>
      <span>SSH or Bastion session</span>
    </div>
    <div class="architecture-node node-internet">
      <span class="node-icon" aria-hidden="true">WWW</span>
      <strong>Internet users</strong>
      <span>HTTPS 443</span>
    </div>
    <div class="architecture-node node-hybrid">
      <span class="node-icon" aria-hidden="true">HYB</span>
      <strong>On-premises or hub network</strong>
      <span>FastConnect or Site-to-Site VPN</span>
    </div>
  </div>

  <div class="architecture-stage architecture-stage-vcn">
    <div class="stage-header">
      <p class="visual-caption">Private VCN zones</p>
      <span>Database paths stay private; public ingress terminates at the load balancer.</span>
    </div>
    <div class="architecture-grid">
      <div class="architecture-node node-bastion">
        <span class="node-icon" aria-hidden="true">BST</span>
        <strong>OCI Bastion or approved jump host</strong>
        <span>Private TCP 22 path</span>
      </div>
      <div class="architecture-node node-lb">
        <span class="node-icon" aria-hidden="true">LB</span>
        <strong>Public load balancer subnet</strong>
        <span>HTTPS to application tier</span>
      </div>
      <div class="architecture-node node-drg">
        <span class="node-icon" aria-hidden="true">DRG</span>
        <strong>DRG optional</strong>
        <span>Hybrid routing to private subnets</span>
      </div>
      <div class="architecture-node node-apps">
        <span class="node-icon" aria-hidden="true">APP</span>
        <strong>Applications subnet</strong>
        <span>ORDS, APEX, middleware, AI agents</span>
      </div>
      <div class="architecture-node node-dbtools">
        <span class="node-icon" aria-hidden="true">SQL</span>
        <strong>Database Tools private endpoint subnet</strong>
        <span>SQL*Net TCP 1521</span>
      </div>
      <div class="architecture-node node-client">
        <span class="node-icon" aria-hidden="true">EXA</span>
        <strong>Target Exadata client subnet</strong>
        <span>SCAN, VIP, listener, application SQL*Net</span>
      </div>
      <div class="architecture-node node-backup">
        <span class="node-icon" aria-hidden="true">BKP</span>
        <strong>Target Exadata backup subnet</strong>
        <span>Backup and recovery network</span>
      </div>
    </div>
  </div>

  <div class="architecture-stage architecture-stage-services">
    <p class="visual-caption">Controlled egress</p>
    <div class="architecture-node node-sgw">
      <span class="node-icon" aria-hidden="true">SGW</span>
      <strong>Service Gateway</strong>
      <span>TCP 443 to Oracle Services Network</span>
    </div>
    <div class="architecture-node node-nat">
      <span class="node-icon" aria-hidden="true">NAT</span>
      <strong>NAT Gateway optional</strong>
      <span>Outbound-only public endpoints</span>
    </div>
  </div>

  <div class="flow-label flow-admin">SSH / Bastion</div>
  <div class="flow-label flow-web">HTTPS 443</div>
  <div class="flow-label flow-sql">SQL*Net TCP 1521</div>
  <div class="flow-label flow-services">TCP 443 services</div>
  <div class="flow-label flow-hybrid">Hybrid private routes</div>
</div>"""


def render_bastion_access_flow_infographic() -> str:
    return """<div class="bastion-flow-infographic" aria-label="Bastion access flow infographic">
  <div class="bastion-flow-main">
    <div class="bastion-step step-admin">
      <span class="bastion-step-number">1</span>
      <span class="bastion-step-icon" aria-hidden="true">ADM</span>
      <strong>Administrator workstation</strong>
      <span>Named user starts from an approved source network.</span>
    </div>
    <div class="bastion-connector" aria-hidden="true">SSH request</div>
    <div class="bastion-step step-session">
      <span class="bastion-step-number">2</span>
      <span class="bastion-step-icon" aria-hidden="true">BST</span>
      <strong>OCI Bastion managed session</strong>
      <span>Identity-controlled, time-bound access path.</span>
    </div>
    <div class="bastion-connector" aria-hidden="true">Private path</div>
    <div class="bastion-step step-target">
      <span class="bastion-step-number">3</span>
      <span class="bastion-step-icon" aria-hidden="true">VCN</span>
      <strong>Private target subnet</strong>
      <span><code>subnet-admin</code> or target Exadata client subnet.</span>
    </div>
    <div class="bastion-connector" aria-hidden="true">TCP 22</div>
    <div class="bastion-step step-host">
      <span class="bastion-step-number">4</span>
      <span class="bastion-step-icon" aria-hidden="true">SSH</span>
      <strong>Approved private host</strong>
      <span>Private host or target Exadata VM node only.</span>
    </div>
  </div>

  <div class="bastion-control-panel" aria-label="Bastion access controls">
    <div class="bastion-control">
      <strong>Identity gate</strong>
      <span>IAM policy, MFA, and privileged access workflow.</span>
    </div>
    <div class="bastion-control">
      <strong>Network gate</strong>
      <span>Approved CIDR allowlist; no <code>0.0.0.0/0</code> SSH.</span>
    </div>
    <div class="bastion-control">
      <strong>Session guardrail</strong>
      <span>Short TTL with session creation and deletion audit events.</span>
    </div>
    <div class="bastion-control">
      <strong>Private-only target</strong>
      <span>No public IP or public listener path on Exadata nodes.</span>
    </div>
  </div>
</div>"""


def render_blocks(lines: list[str], chapter_title: str, chapter_number: str, section_title: str) -> str:
    out: list[str] = []
    i = 0
    current_heading = section_title
    previous_text = ""
    pending_objective: str | None = None
    chapter_title_key = chapter_title.lower()
    collapse_code_cards = (
        "end-to-end implementation runbook" in chapter_title_key
        or "oci poc runbook" in chapter_title_key
    )
    collapse_bash_cards = int(chapter_number) >= 6
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped == "---":
            i += 1
            continue
        if stripped == "::logical-architecture-infographic":
            out.append(render_logical_architecture_infographic())
            previous_text = ""
            i += 1
            continue
        if stripped == "::bastion-access-flow-infographic":
            out.append(render_bastion_access_flow_infographic())
            previous_text = ""
            i += 1
            continue
        runbook_card = re.fullmatch(r"::runbook-card\s+(BASH|OUTPUT)\s+(\d{1,2})", stripped, flags=re.I)
        if runbook_card:
            card_kind = runbook_card.group(1).upper()
            card_number = runbook_card.group(2)
            collapse_runbook_card = (
                collapse_code_cards
                or (collapse_bash_cards and card_kind == "BASH")
                or (
                "validation and readiness record" in chapter_title_key
                and card_kind == "BASH"
                and card_number == "20"
                )
            )
            out.append(render_runbook_card(card_kind, card_number, collapsed=collapse_runbook_card))
            previous_text = ""
            i += 1
            continue
        if stripped.startswith("### "):
            current_heading = stripped[4:].strip()
            out.append(f"<h3>{inline_markup(current_heading)}</h3>")
            previous_text = current_heading
            i += 1
            continue
        if stripped.startswith("#### "):
            current_heading = stripped[5:].strip()
            out.append(f"<h4>{inline_markup(current_heading)}</h4>")
            previous_text = current_heading
            i += 1
            continue
        if stripped.startswith("```"):
            language = stripped.strip("`").strip() or "text"
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            objective = objective_for_code(language, current_heading, previous_text, pending_objective)
            if current_heading.upper().startswith("OUTPUT "):
                language = "output"
            manual_line_by_line = current_heading in {
                "BASH 11 - Open SQL*Plus as SYSDBA on CDB01",
                "BASH 12 - Return to the Cloud Shell session",
            } and previous_text.startswith(f"{current_heading}: Objective:")
            collapse_card = collapse_code_cards or (
                collapse_bash_cards and code_type_for(language, objective) == "Bash"
            )
            if manual_line_by_line:
                collapse_card = False
            if current_heading == "Reusable connection commands":
                collapse_card = False
            if current_heading in {
                "BASH 13 - Allow Cloud Shell SSH to the bastion NSG",
                "BASH 13 - Allow SSH to the bastion NSG",
            }:
                collapse_card = False
            out.append(
                render_code_card(
                    language,
                    "\n".join(code_lines),
                    objective,
                    collapsed=collapse_card,
                    copyable=not manual_line_by_line,
                )
            )
            pending_objective = None
            previous_text = ""
            continue
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(parse_markdown_table(table_lines))
            previous_text = ""
            continue
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            first_number = int(re.match(r"^(\d+)\.\s+", stripped).group(1))
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            start_attr = f' start="{first_number}"' if first_number != 1 else ""
            out.append(f'<ol class="article-list ordered"{start_attr}>')
            out.extend(f"<li>{inline_markup(item)}</li>" for item in items)
            out.append("</ol>")
            previous_text = ""
            continue
        if stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:].strip())
                i += 1
            out.append('<ul class="article-list">')
            out.extend(f"<li>{inline_markup(item)}</li>" for item in items)
            out.append("</ul>")
            previous_text = ""
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if (
                not next_line
                or next_line == "---"
                or next_line.startswith("### ")
                or next_line.startswith("#### ")
                or next_line.startswith("```")
                or next_line.startswith("|")
                or next_line.startswith("- ")
                or re.match(r"^\d+\.\s+", next_line)
            ):
                break
            paragraph_lines.append(next_line)
            i += 1
        paragraph = " ".join(paragraph_lines)
        match = re.match(r"^(.+?):\s*Objective:\s*(.+)$", paragraph, re.I)
        if match:
            current_heading = match.group(1).strip()
            out.append(f"<h3>{inline_markup(current_heading)}</h3>")
            pending_objective = match.group(2).strip()
            previous_text = current_heading
            continue
        if section_title.lower().endswith("purpose") or "chapter purpose" in section_title.lower():
            out.append(f'<div class="note-box">{inline_markup(paragraph)}</div>')
        else:
            out.append(f"<p>{inline_markup(paragraph)}</p>")
        previous_text = paragraph
    return "\n".join(out)


def parse_chapter(path: Path) -> Chapter:
    raw_text = path.read_text(encoding="utf-8")
    metadata = front_matter(raw_text)
    text = strip_front_matter(raw_text)
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), path.stem)
    short_title = re.sub(r"^Chapter\s+\d+\s*-\s*", "", title)
    number_match = re.match(r"(\d{2})_", path.name)
    number = number_match.group(1) if number_match else "00"
    generated_html = metadata.get("generated_html", "")
    if generated_html.endswith("/index.html"):
        slug = generated_html.removesuffix("/index.html")
    else:
        slug = f"{number}-{slugify(short_title)}"
    body = lines[1:] if lines and lines[0].startswith("# ") else lines
    sections: list[tuple[str, list[str]]] = []
    current_title = "Overview"
    current_lines: list[str] = []
    for line in body:
        if line.startswith("## "):
            if any(line.strip() and line.strip() != "---" for line in current_lines):
                sections.append((current_title, current_lines))
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if any(line.strip() and line.strip() != "---" for line in current_lines):
        sections.append((current_title, current_lines))
    summary = ""
    for sec_title, sec_lines in sections:
        if "purpose" in sec_title.lower() or not summary:
            for candidate in sec_lines:
                clean = candidate.strip()
                if clean and not clean.startswith("---"):
                    summary = clean
                    break
        if summary and "purpose" in sec_title.lower():
            break
    return Chapter(path, number, title, short_title, slug, summary, sections)


def page_shell(title: str, body_class: str, body: str, css_href: str, shared_href: str, js_href: str, guide_key: str, guide_scope: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | {SERIES_TITLE}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="{css_href}">
</head>
<body class="{body_class}" data-guide-key="{html_attr(guide_key)}" data-guide-scope="{html_attr(guide_scope)}">
  <a class="skip-link" href="#main">Skip to content</a>
{body}
  <button class="back-top" type="button" aria-label="Back to top">Back to top</button>
  <script src="{shared_href}"></script>
  <script src="{js_href}"></script>
</body>
</html>
"""


def topbar(prefix: str) -> str:
    home_href = f"{prefix}index.html"
    return f"""  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="{home_href}">
        <span class="brand-mark" aria-hidden="true">OCI</span>
        <span class="brand-text">
          <span class="brand-title" data-series-brand-title>{SERIES_TITLE}</span>
          <span class="brand-subtitle" data-series-brand-subtitle>{SERIES_SUBTITLE}</span>
        </span>
      </a>
      <div class="top-actions">
        <a class="top-link" href="{home_href}#documentation">Documentation</a>
        <a class="top-link" href="{home_href}#glossary">Glossary</a>
        <button class="theme-toggle" type="button" aria-pressed="false">Dark mode</button>
      </div>
    </div>
  </header>"""


def disclaimer(expanded: bool) -> str:
    if expanded:
        return f"""<aside class="disclaimer expanded">
          <h2>{NOTICE_TITLE}</h2>
          <p>{NOTICE_BODY}</p>
        </aside>"""
    return f"""<details class="disclaimer">
          <summary>{NOTICE_TITLE} <span class="disclaimer-action">click here</span></summary>
          <p>{NOTICE_BODY}</p>
        </details>"""


def root_card(chapter: Chapter) -> str:
    return f"""<a class="related-link" href="{chapter.slug}/index.html">
  <strong>{html.escape(chapter.number)}. {html.escape(chapter.short_title)}</strong>
</a>"""


def render_root(chapters: list[Chapter]) -> str:
    cards = "\n".join(root_card(chapter) for chapter in chapters)
    toc = "".join(
        f'<li><a href="#{anchor}">{label}</a></li>'
        for anchor, label in [
            ("navigate", "Navigate the workbook"),
            ("implementation-map", "Implementation map"),
            ("documentation", "Oracle Official Documentation"),
            ("glossary", "Glossary"),
        ]
    )
    doc_groups = []
    for title, links in DOC_LINKS:
        doc_groups.append(f'<div class="documentation-group"><h3>{html.escape(title)}</h3><ul class="reference-list">')
        for label, href, note in links:
            doc_groups.append(
                f'<li><a href="{html_attr(href)}" target="_blank" rel="noopener">{html.escape(label)}</a><span>{html.escape(note)}</span></li>'
            )
        doc_groups.append("</ul></div>")
    glossary_groups = []
    for title, terms in GLOSSARY_GROUPS:
        glossary_groups.append(f'<div class="glossary-block"><h3>{html.escape(title)}</h3><div class="glossary-grid">')
        for term, definition, href in terms:
            glossary_groups.append(
                f'<article class="glossary-term"><h4>{html.escape(term)}</h4><p>{html.escape(definition)}</p><a href="{html_attr(href)}" target="_blank" rel="noopener">Oracle reference</a></article>'
            )
        glossary_groups.append("</div></div>")
    phase_rows = [
        ("Plan", "00-04", "Purpose, scope, target architecture, addressing, naming, DNS, and administrator access choices."),
        ("Network implement", "05", "Run the consolidated OCI CLI flow in the default Partner/LAD-01 compartment, or the assigned Partner child compartment for the deployment."),
        ("Exadata implement", "06-13", "Reuse the prepared network baseline and single-compartment aliases to create the bastion VM, Exadata cluster, CDB, backups, credential secrets, and Database Management setup."),
    ]
    phase_table = parse_markdown_table(
        ["| Phase | Chapters | Focus |", "|---|---|---|"]
        + [f"| {phase} | `{chapters}` | {focus} |" for phase, chapters, focus in phase_rows]
    )
    body = f"""{topbar("")}
  <div id="top"></div>
  <section class="hero">
    <div class="hero-grid">
      <div class="hero-copy">
        <p class="eyebrow">Oracle Cloud Infrastructure workbook</p>
        <h1>OCI PoC RunBook</h1>
        <p class="subtitle">A complete PoC implementation runbook for the assigned Partner child compartment. It starts with the VCN, subnet, route, security, bastion-access, and service-access baseline, then continues through Exadata deployment, database creation, automatic backups, credential secrets, and OCI Database Management.</p>
        <div class="hero-meta">
          <span>Last updated {TODAY_LABEL}</span>
        </div>
        {disclaimer(True)}
      </div>
      <aside class="hero-visual" aria-label="Latest guide coverage">
        <p class="visual-caption">Latest guide coverage</p>
        <ul class="hero-highlights">
          <li class="highlight">Single assigned PoC compartment under Partner, with Partner/LAD-01 as the default example.</li>
          <li class="highlight">Network baseline chapters feed the Exadata implementation sequence.</li>
          <li class="highlight">Runbook chapters cover bastion VM, Exadata cluster, CDB, backups, secrets, and Database Management.</li>
          <li class="highlight">The same single-compartment aliases are reused end to end.</li>
        </ul>
      </aside>
    </div>
  </section>
  <div class="page-grid">
    <nav class="toc" aria-label="Table of contents">
      <p>Table of contents</p>
      <ol>{toc}</ol>
    </nav>
    <main id="main" class="article">
      <section id="navigate" class="article-section">
        <h2>Navigate the workbook</h2>
        <p>Open each chapter as a self-contained HTML page. The chapter sequence supports a full implementation, but every chapter can also be edited and reviewed independently.</p>
        <nav class="related-links root-links" data-guide-cards data-guide-variant="root" data-guide-scope="root" aria-label="Workbook chapters">
          {cards}
        </nav>
      </section>
      <section id="implementation-map" class="article-section">
        <h2>Implementation map</h2>
        <p>The workbook is organized around the operational path from design through deployment readiness.</p>
        {phase_table}
      </section>
      <section id="documentation" class="article-section">
        <h2>Oracle Official Documentation</h2>
        <p>These reader-facing Oracle references support the implementation choices and validation checks in the workbook.</p>
        <div class="documentation-grid">
          {''.join(doc_groups)}
        </div>
      </section>
      <section id="glossary" class="article-section">
        <h2>Glossary</h2>
        <p>Terms are limited to concepts, products, services, and controls used in this workbook.</p>
        {''.join(glossary_groups)}
      </section>
    </main>
  </div>
  <footer class="site-footer">
    <p><strong>{NOTICE_TITLE}.</strong> {NOTICE_BODY}</p>
  </footer>"""
    return page_shell("OCI PoC RunBook", "workbook-root", body, "assets/workbook.css", "shared-guide-set.js", "assets/workbook.js", "root", "root")


def render_chapter(chapter: Chapter, chapters: list[Chapter]) -> str:
    prefix = "../"
    section_nav = []
    section_html = []
    for section_title, section_lines in chapter.sections:
        clean_title = re.sub(r"^\d+\.\s*", "", section_title)
        anchor = slugify(clean_title)
        saveable = is_saveable_section(clean_title)
        section_class = "article-section saveable-section" if saveable else "article-section"
        save_attr = (
            f' data-save-title="{html_attr(clean_title)}" data-save-file="{html_attr(save_file_name_for(clean_title))}"'
            if saveable
            else ""
        )
        heading = (
            f"""<div class="section-heading-row">
          <h2>{inline_markup(clean_title)}</h2>
          <button class="save-section-btn" type="button">Save .txt</button>
        </div>"""
            if saveable
            else f"<h2>{inline_markup(clean_title)}</h2>"
        )
        section_nav.append((anchor, clean_title))
        section_html.append(
            f"""<section id="{anchor}" class="{section_class}"{save_attr}>
        {heading}
        {render_blocks(section_lines, chapter.title, chapter.number, clean_title)}
      </section>"""
        )
    chapter_nav = render_chapter_card_nav(chapter, chapters)
    toc = "".join(f'<li><a href="#{anchor}">{html.escape(label)}</a></li>' for anchor, label in section_nav)
    body = f"""{topbar(prefix)}
  <div id="top"></div>
  <section class="hero hero-compact">
    <div class="hero-grid">
      <div class="hero-copy">
        <p class="eyebrow">Chapter {chapter.number}</p>
        <h1>{html.escape(chapter.short_title)}</h1>
        <p class="subtitle">{inline_markup(chapter.summary)}</p>
        <div class="hero-meta">
          <span>Last updated {TODAY_LABEL}</span>
        </div>
        {disclaimer(False)}
      </div>
    </div>
  </section>
  <div class="page-grid">
    <nav class="toc" aria-label="Table of contents">
      <p>Table of contents</p>
      <ol>{toc}</ol>
    </nav>
    <main id="main" class="article">
      {chapter_nav}
      {''.join(section_html)}
      <section id="chapter-navigation" class="article-section">
        <h2>Chapter navigation</h2>
        {chapter_nav}
        <div class="two-up">
          <a class="content-card link-card" href="../index.html#documentation"><strong>Series documentation</strong></a>
          <a class="content-card link-card" href="../index.html#glossary"><strong>Series glossary</strong></a>
        </div>
      </section>
    </main>
  </div>
  <footer class="site-footer">
    {disclaimer(False)}
  </footer>"""
    return page_shell(chapter.short_title, "workbook-chapter", body, "../assets/workbook.css", "../shared-guide-set.js", "../assets/workbook.js", chapter.slug, "nested")


def write_css() -> None:
    css = r''':root {
  --bg: #faf8f7;
  --surface: #ffffff;
  --surface-soft: #f7f4f2;
  --surface-strong: #f5f5f4;
  --text: #1f1b1a;
  --muted: #57534e;
  --subtle: #78716c;
  --line: #e7e5e4;
  --accent: #c74634;
  --accent-strong: #5f2b24;
  --accent-soft: #fef2f2;
  --gold: #b07113;
  --green: #22775f;
  --blue: #2f5f96;
  --code-bg: #171412;
  --code-text: #f7f3ec;
  --shadow: 0 18px 50px rgba(31, 27, 26, 0.08);
  --radius: 8px;
  color-scheme: light;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body[data-theme="dark"] {
  --bg: #171412;
  --surface: #241f1d;
  --surface-soft: #1f1b1a;
  --surface-strong: #2f2a27;
  --text: #faf8f7;
  --muted: #d6d3d1;
  --subtle: #a8a29e;
  --line: #44403c;
  --accent-soft: rgba(199, 70, 52, 0.18);
  --shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
  color-scheme: dark;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-size: 16px;
  line-height: 1.7;
}

a {
  color: var(--accent-strong);
  text-decoration-color: rgba(199, 70, 52, 0.38);
  text-underline-offset: 3px;
}

body[data-theme="dark"] a {
  color: #f4b8ad;
}

.skip-link {
  position: absolute;
  left: 1rem;
  top: 0.5rem;
  z-index: 20;
  transform: translateY(-150%);
  border-radius: 6px;
  background: var(--text);
  color: var(--surface);
  padding: 0.5rem 0.75rem;
}

.skip-link:focus {
  transform: translateY(0);
}

.topbar {
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  position: sticky;
  top: 0;
  z-index: 10;
  backdrop-filter: blur(14px);
}

.topbar-inner {
  width: min(1280px, calc(100% - 2rem));
  min-height: 68px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.brand {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border-radius: 6px;
  background: var(--accent);
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 800;
}

.brand-text {
  min-width: 0;
  display: grid;
  gap: 0.1rem;
}

.brand-title,
.brand-subtitle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brand-title {
  font-weight: 750;
}

.brand-subtitle {
  color: var(--muted);
  font-size: 0.85rem;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.top-link,
.theme-toggle {
  min-height: 36px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.7rem;
  font: inherit;
  font-size: 0.9rem;
  line-height: 1;
  text-decoration: none;
  cursor: pointer;
}

.top-link:hover,
.theme-toggle:hover {
  border-color: rgba(199, 70, 52, 0.45);
}

.hero {
  border-bottom: 1px solid var(--line);
  background:
    linear-gradient(135deg, rgba(199, 70, 52, 0.13), transparent 44%),
    linear-gradient(180deg, #ffffff 0%, var(--surface-soft) 100%);
}

body[data-theme="dark"] .hero,
body[data-theme="dark"] .site-header {
  background:
    linear-gradient(135deg, rgba(199, 70, 52, 0.18), transparent 44%),
    linear-gradient(180deg, var(--surface) 0%, var(--surface-soft) 100%);
}

.hero-grid {
  width: min(1280px, calc(100% - 2rem));
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 2rem;
  align-items: end;
  padding: 4rem 0 3rem;
}

.hero-compact .hero-grid {
  grid-template-columns: minmax(0, 1fr);
  padding-bottom: 2.4rem;
}

.hero-copy {
  max-width: 58rem;
}

.eyebrow,
.visual-caption,
.toc p {
  margin: 0 0 0.75rem;
  color: var(--accent-strong);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

body[data-theme="dark"] .eyebrow,
body[data-theme="dark"] .visual-caption,
body[data-theme="dark"] .toc p {
  color: #f4b8ad;
}

h1,
h2,
h3,
h4 {
  margin: 0;
  letter-spacing: 0;
  line-height: 1.15;
}

h1 {
  max-width: 58rem;
  font-size: clamp(2.35rem, 7vw, 4.15rem);
}

h2 {
  font-size: 2rem;
}

h3 {
  margin-top: 2rem;
  font-size: 1.35rem;
}

h4 {
  margin-top: 1.5rem;
  font-size: 1.08rem;
}

.subtitle {
  max-width: 49rem;
  margin: 1rem 0 0;
  color: var(--muted);
  font-size: 1.1rem;
}

.hero-meta {
  display: flex;
  gap: 0.55rem;
  flex-wrap: wrap;
  margin: 1.25rem 0 0;
}

.hero-meta span {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 0.82rem;
  padding: 0.2rem 0.7rem;
}

.hero-visual,
.content-card,
.note-box,
.documentation-group,
.glossary-term {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.hero-visual {
  padding: 1.1rem;
}

.hero-highlights,
.article-list,
.reference-list {
  padding-left: 1.25rem;
}

.hero-highlights {
  margin: 0;
}

.highlight {
  margin: 0.45rem 0;
  color: var(--muted);
  overflow-wrap: normal;
  word-break: normal;
}

.disclaimer {
  margin-top: 1.25rem;
  border: 1px solid rgba(180, 83, 9, 0.42);
  border-radius: var(--radius);
  background: #fffbeb;
  color: #451a03;
}

.disclaimer.expanded {
  padding: 1rem;
}

.disclaimer h2 {
  font-size: 0.83rem;
  letter-spacing: 0.08em;
  line-height: 1.35;
  text-transform: uppercase;
}

.disclaimer p {
  margin: 0.55rem 0 0;
  font-size: 0.93rem;
  line-height: 1.65;
}

.disclaimer summary {
  cursor: pointer;
  list-style: none;
  padding: 0.85rem 1rem;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  line-height: 1.4;
  text-transform: uppercase;
}

.disclaimer summary::-webkit-details-marker {
  display: none;
}

.disclaimer:not(.expanded) p {
  border-top: 1px solid rgba(180, 83, 9, 0.25);
  margin: 0;
  padding: 0.9rem 1rem 1rem;
}

.disclaimer-action {
  color: #92400e;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1;
  text-decoration: underline;
  text-transform: none;
  white-space: nowrap;
}

body[data-theme="dark"] .disclaimer {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(120, 53, 15, 0.28);
  color: #fef3c7;
}

body[data-theme="dark"] .disclaimer:not(.expanded) p {
  border-top-color: rgba(245, 158, 11, 0.3);
}

body[data-theme="dark"] .disclaimer-action {
  color: #fde68a;
}

.page-grid {
  width: min(1280px, calc(100% - 2rem));
  margin: 0 auto;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 2rem;
  padding: 2rem 0 4rem;
}

.toc {
  position: sticky;
  top: 5.4rem;
  align-self: start;
  max-height: calc(100vh - 6.4rem);
  overflow: auto;
  border-right: 1px solid var(--line);
  padding-right: 1rem;
}

.toc ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}

.toc a {
  display: block;
  border-radius: 6px;
  color: var(--muted);
  padding: 0.35rem 0.5rem;
  text-decoration: none;
}

.toc a:hover,
.toc a:focus-visible {
  background: var(--surface-soft);
  color: var(--text);
}

.article {
  min-width: 0;
}

.article-section {
  border-top: 1px solid var(--line);
  padding: 2.5rem 0;
  scroll-margin-top: 6rem;
}

.article-section:first-child {
  border-top: 0;
  padding-top: 0;
}

.article-section p {
  max-width: 74ch;
}

.article-section code:not(.code-card code) {
  border-radius: 5px;
  background: var(--surface-strong);
  color: var(--accent-strong);
  padding: 0.08rem 0.25rem;
  overflow-wrap: break-word;
}

body[data-theme="dark"] .article-section code:not(.code-card code) {
  color: #f4b8ad;
}

.article-list li {
  margin: 0.45rem 0;
}

.ordered {
  padding-left: 1.45rem;
}

.note-box {
  margin: 1rem 0;
  padding: 1rem;
  color: var(--muted);
}

.architecture-infographic {
  position: relative;
  display: grid;
  grid-template-columns: minmax(155px, 0.75fr) minmax(0, 2.2fr) minmax(170px, 0.85fr);
  gap: 1rem;
  margin: 1.25rem 0;
  padding: 1rem;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background:
    linear-gradient(135deg, rgba(199, 70, 52, 0.08), transparent 32%),
    linear-gradient(180deg, var(--surface) 0%, var(--surface-soft) 100%);
  box-shadow: var(--shadow);
}

.architecture-infographic::before,
.architecture-infographic::after {
  content: "";
  position: absolute;
  pointer-events: none;
}

.architecture-infographic::before {
  inset: 52px 17% 76px 17%;
  border-top: 2px solid rgba(47, 95, 150, 0.34);
  border-bottom: 2px solid rgba(34, 119, 95, 0.3);
}

.architecture-infographic::after {
  inset: 44% 13%;
  border-top: 2px dashed rgba(199, 70, 52, 0.32);
}

.architecture-stage {
  position: relative;
  z-index: 1;
  display: grid;
  align-content: start;
  gap: 0.75rem;
}

.architecture-stage-vcn {
  border: 1px solid rgba(47, 95, 150, 0.28);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--surface) 86%, #dbeafe);
  padding: 1rem;
}

.stage-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.25rem;
}

.stage-header .visual-caption {
  margin-bottom: 0;
}

.stage-header span {
  max-width: 36rem;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.45;
  text-align: right;
}

.architecture-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.architecture-node {
  min-width: 0;
  min-height: 118px;
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 0.35rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  padding: 0.85rem;
}

.architecture-node strong,
.architecture-node span {
  overflow-wrap: break-word;
}

.architecture-node strong {
  color: var(--text);
  font-size: 0.96rem;
  line-height: 1.25;
}

.architecture-node > span:last-child {
  color: var(--muted);
  font-size: 0.83rem;
  line-height: 1.4;
}

.node-icon {
  display: inline-grid;
  place-items: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 7px;
  background: var(--surface-strong);
  color: var(--accent-strong);
  font-size: 0.69rem;
  font-weight: 850;
  letter-spacing: 0.04em;
  line-height: 1;
}

.node-admin .node-icon,
.node-bastion .node-icon {
  background: #fef3c7;
  color: #92400e;
}

.node-internet .node-icon,
.node-lb .node-icon {
  background: #fee2e2;
  color: #991b1b;
}

.node-hybrid .node-icon,
.node-drg .node-icon {
  background: #e0f2fe;
  color: #075985;
}

.node-apps .node-icon,
.node-dbtools .node-icon {
  background: #dcfce7;
  color: #166534;
}

.node-client .node-icon,
.node-backup .node-icon {
  background: #ede9fe;
  color: #5b21b6;
}

.node-sgw .node-icon,
.node-nat .node-icon {
  background: #f1f5f9;
  color: #334155;
}

.node-apps,
.node-client {
  min-height: 140px;
}

.node-client {
  border-color: rgba(91, 33, 182, 0.3);
}

.node-backup {
  grid-column: auto;
}

.flow-label {
  position: relative;
  z-index: 2;
  justify-self: start;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 800;
  line-height: 1;
  padding: 0.34rem 0.55rem;
  white-space: nowrap;
}

.flow-admin {
  grid-column: 1;
}

.flow-web {
  grid-column: 2;
}

.flow-sql {
  grid-column: 2;
}

.flow-services {
  grid-column: 3;
}

.flow-hybrid {
  grid-column: 3;
}

body[data-theme="dark"] .architecture-stage-vcn {
  background: color-mix(in srgb, var(--surface) 82%, #172554);
}

body[data-theme="dark"] .architecture-node {
  background: var(--surface);
}

body[data-theme="dark"] .node-icon {
  filter: saturate(0.82) brightness(0.9);
}

.bastion-flow-infographic {
  display: grid;
  gap: 1rem;
  margin: 1.25rem 0;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background:
    linear-gradient(135deg, rgba(34, 119, 95, 0.09), transparent 34%),
    linear-gradient(180deg, var(--surface) 0%, var(--surface-soft) 100%);
  box-shadow: var(--shadow);
}

.bastion-flow-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 0.65rem;
  align-items: stretch;
}

.bastion-step {
  position: relative;
  min-width: 0;
  min-height: 178px;
  display: grid;
  grid-template-rows: auto auto auto 1fr;
  gap: 0.4rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  padding: 0.9rem;
}

.bastion-step-number {
  position: absolute;
  top: 0.65rem;
  right: 0.65rem;
  display: inline-grid;
  place-items: center;
  width: 1.55rem;
  height: 1.55rem;
  border-radius: 999px;
  background: var(--surface-strong);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 850;
  line-height: 1;
}

.bastion-step-icon {
  display: inline-grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 7px;
  background: #fef3c7;
  color: #92400e;
  font-size: 0.68rem;
  font-weight: 850;
  letter-spacing: 0.04em;
  line-height: 1;
}

.bastion-step strong {
  color: var(--text);
  font-size: 0.98rem;
  line-height: 1.25;
}

.bastion-step span:last-child {
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.42;
}

.step-session .bastion-step-icon {
  background: #e0f2fe;
  color: #075985;
}

.step-target .bastion-step-icon {
  background: #dcfce7;
  color: #166534;
}

.step-host .bastion-step-icon {
  background: #ede9fe;
  color: #5b21b6;
}

.bastion-connector {
  align-self: center;
  min-width: 5.4rem;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 850;
  line-height: 1.15;
  text-align: center;
  text-transform: uppercase;
}

.bastion-connector::before {
  content: "";
  width: 100%;
  height: 2px;
  margin-bottom: 0.45rem;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(34, 119, 95, 0.22), rgba(34, 119, 95, 0.78));
}

.bastion-control-panel {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  border-top: 1px solid var(--line);
  padding-top: 1rem;
}

.bastion-control {
  min-width: 0;
  border-left: 3px solid rgba(199, 70, 52, 0.48);
  background: color-mix(in srgb, var(--surface) 86%, #fef2f2);
  border-radius: 0 8px 8px 0;
  padding: 0.75rem 0.85rem;
}

.bastion-control strong {
  display: block;
  color: var(--text);
  font-size: 0.9rem;
  line-height: 1.25;
}

.bastion-control span {
  display: block;
  margin-top: 0.3rem;
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.4;
}

body[data-theme="dark"] .bastion-step {
  background: var(--surface);
}

body[data-theme="dark"] .bastion-control {
  background: color-mix(in srgb, var(--surface) 86%, #450a0a);
}

.content-card,
.documentation-group,
.glossary-term {
  padding: 1rem;
}

.two-up,
.documentation-grid,
.glossary-grid,
.related-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.documentation-grid,
.related-links.root-links {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.glossary-block {
  margin-top: 1.5rem;
}

.glossary-term h4 {
  margin-top: 0;
}

.reference-list {
  margin: 0.8rem 0 0;
}

.reference-list li {
  margin: 0.7rem 0;
}

.reference-list span {
  display: block;
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.55;
}

.related-link,
.chapter-link,
.link-card {
  display: grid;
  gap: 0.35rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  color: inherit;
  padding: 1rem;
  text-decoration: none;
  transition: border-color 160ms ease, transform 160ms ease;
}

.related-link:hover,
.chapter-link:hover,
.link-card:hover {
  border-color: rgba(199, 70, 52, 0.5);
  transform: translateY(-1px);
}

.chapter-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.chapter-card-nav {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.nav-card {
  min-height: 92px;
}

.nav-card-label {
  color: var(--accent-strong);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

body[data-theme="dark"] .nav-card-label {
  color: #f4b8ad;
}

.nav-card.is-disabled {
  color: var(--subtle);
  cursor: default;
  opacity: 0.72;
}

.nav-card.is-disabled:hover {
  border-color: var(--line);
  transform: none;
}

.section-heading-row {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.save-section-btn {
  flex: 0 0 auto;
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font: inherit;
  font-size: 0.86rem;
  font-weight: 700;
  line-height: 1;
  padding: 0.45rem 0.75rem;
}

.save-section-btn:hover {
  border-color: rgba(199, 70, 52, 0.45);
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  margin: 1.25rem 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
}

.data-table {
  min-width: 720px;
  width: 100%;
  border-collapse: collapse;
  font-size: 0.94rem;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid var(--line);
  padding: 0.7rem 0.8rem;
  text-align: left;
  vertical-align: top;
}

.data-table th {
  background: var(--surface-strong);
  color: var(--text);
  font-weight: 750;
}

.data-table .status-col,
.data-table .status-cell {
  min-width: 9.5rem;
  white-space: nowrap;
}

.data-table .align-left {
  text-align: left;
}

.data-table .align-center {
  text-align: center;
}

.data-table .align-right {
  text-align: right;
}

.data-table tr:last-child td {
  border-bottom: 0;
}

.code-card {
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid rgba(120, 113, 108, 0.35);
  background: #171412;
  margin: 1.25rem 0;
}

.code-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.5rem 1rem;
}

.code-type {
  color: #e7e5e4;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1rem;
  text-transform: uppercase;
}

.copy-btn,
.code-toggle-btn {
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1rem;
  padding: 0.25rem 0.75rem;
  transition: background 160ms ease, border-color 160ms ease;
  cursor: pointer;
}

.code-toggle-btn {
  flex: 0 0 auto;
  margin-left: 1rem;
}

.copy-btn:hover,
.code-toggle-btn:hover {
  background: rgba(255, 255, 255, 0.18);
}

.copy-btn:focus-visible,
.code-toggle-btn:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.65);
  outline-offset: 2px;
}

.code-card[data-collapsed="true"] pre {
  display: none;
}

.code-description {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: #e7e5e4;
  font-size: 0.875rem;
  font-weight: 400;
  line-height: 1.5rem;
  padding: 0.75rem 1rem;
}

.code-objective {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.code-objective-text {
  flex: 1 1 auto;
  min-width: 0;
}

.objective-label {
  font-weight: 600;
}

.code-objective strong {
  background: rgba(199, 70, 52, 0.22);
  border-radius: 4px;
  color: #ffb4ab;
  font-weight: 800;
  padding: 0.05rem 0.25rem;
}

.code-card pre {
  color: #f5f5f4;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 13px;
  font-weight: 400;
  line-height: 24px;
  margin: 0;
  overflow-x: auto;
  padding: 1rem;
  white-space: pre;
  -webkit-font-smoothing: antialiased;
}

.code-card pre code {
  color: inherit;
  font: inherit;
  font-weight: 400;
}

.code-scroll::-webkit-scrollbar {
  height: 10px;
  width: 10px;
}

.code-scroll::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.08);
}

.code-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.28);
  border-radius: 999px;
}

.site-footer {
  border-top: 1px solid var(--line);
  background: var(--surface-soft);
  color: var(--muted);
  padding: 1.5rem max(1rem, calc((100% - 1280px) / 2));
}

.site-footer p {
  max-width: 80rem;
  margin: 0;
}

.site-footer .disclaimer {
  margin: 0;
  max-width: 80rem;
}

.back-top {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: 15;
  display: none;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  padding: 0.55rem 0.8rem;
  box-shadow: var(--shadow);
  cursor: pointer;
}

.back-top.is-visible {
  display: inline-flex;
}

:focus-visible {
  outline: 2px solid rgba(199, 70, 52, 0.7);
  outline-offset: 2px;
}

@media (max-width: 1040px) {
  .hero-grid,
  .page-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-visual {
    max-width: 100%;
  }

  .toc {
    position: static;
    max-height: none;
    overflow: visible;
    border-right: 0;
    border-bottom: 1px solid var(--line);
    padding: 0 0 1rem;
  }

  .toc ol {
    display: flex;
    gap: 0.4rem;
    overflow-x: auto;
    padding-bottom: 0.25rem;
  }

  .toc li {
    flex: 0 0 auto;
  }

  .documentation-grid,
  .related-links.root-links,
  .two-up,
  .related-links,
  .glossary-grid,
  .chapter-card-nav {
    grid-template-columns: minmax(0, 1fr);
  }

  .architecture-infographic {
    grid-template-columns: minmax(0, 1fr);
  }

  .architecture-infographic::before,
  .architecture-infographic::after {
    inset: 4.2rem 50% 4rem;
    border-top: 0;
    border-bottom: 0;
    border-left: 2px solid rgba(47, 95, 150, 0.28);
  }

  .architecture-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .node-backup {
    grid-column: auto;
  }

  .flow-label {
    position: static;
    grid-column: auto;
    justify-self: start;
  }

  .bastion-flow-main {
    grid-template-columns: minmax(0, 1fr);
  }

  .bastion-step {
    min-height: 0;
  }

  .bastion-connector {
    min-width: 0;
    min-height: 2.9rem;
    justify-items: start;
    padding-left: 1rem;
    text-align: left;
  }

  .bastion-connector::before {
    width: 2px;
    height: 2.2rem;
    margin: 0 0.7rem 0 0;
    background: linear-gradient(180deg, rgba(34, 119, 95, 0.22), rgba(34, 119, 95, 0.78));
  }

  .bastion-control-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .topbar-inner {
    align-items: stretch;
    flex-direction: column;
    padding: 0.8rem 0;
  }

  .top-actions {
    justify-content: flex-start;
  }

  .top-link,
  .theme-toggle {
    flex: 1 1 auto;
    justify-content: center;
  }

  .hero-grid {
    padding: 2.7rem 0 2rem;
  }

  .hero-meta span {
    width: 100%;
  }

  .data-table {
    min-width: 680px;
  }

  .section-heading-row {
    align-items: stretch;
    flex-direction: column;
  }

  .save-section-btn {
    width: 100%;
  }

  .architecture-infographic {
    padding: 0.8rem;
  }

  .stage-header {
    display: grid;
  }

  .stage-header span {
    text-align: left;
  }

  .architecture-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .architecture-node {
    min-height: 0;
  }

  .bastion-flow-infographic {
    padding: 0.8rem;
  }

  .bastion-control-panel {
    grid-template-columns: minmax(0, 1fr);
  }
}
'''
    ASSETS_DIR.mkdir(exist_ok=True)
    (ASSETS_DIR / "workbook.css").write_text(css, encoding="utf-8")


def write_js(chapters: list[Chapter]) -> None:
    registry = [
        {
            "key": chapter.slug,
            "rootPath": f"{chapter.slug}/index.html",
            "nestedPath": f"../{chapter.slug}/index.html",
            "label": f"{chapter.number}. {chapter.short_title}",
        }
        for chapter in chapters
    ]
    shared = f'''(function () {{
  const shared = {{
    supportedLanguages: ["en"],
    defaultLanguage: "en",
    seriesBrand: {{
      title: {json.dumps(SERIES_TITLE)},
      subtitle: {json.dumps(SERIES_SUBTITLE)}
    }},
    notices: {{
      en: {{
        title: {json.dumps(NOTICE_TITLE)},
        body: {json.dumps(NOTICE_BODY)}
      }}
    }},
    guideRegistry: {json.dumps(registry, indent=6)}
  }};

  function normalizeLanguage(value) {{
    return value === "en" ? "en" : shared.defaultLanguage;
  }}

  function languageFromLocation() {{
    return shared.defaultLanguage;
  }}

  function withLanguage(href) {{
    return href;
  }}

  function chooseHref(entry, scope) {{
    return scope === "root" ? entry.rootPath : entry.nestedPath;
  }}

  function relatedLinks(currentKey, scope) {{
    return shared.guideRegistry
      .filter((entry) => entry.key !== currentKey)
      .map((entry) => ({{
        key: entry.key,
        href: withLanguage(chooseHref(entry, scope)),
        label: entry.label
      }}));
  }}

  function renderGuideCard(link, template) {{
    const anchor = document.createElement("a");
    anchor.className = template?.className || "related-link";
    anchor.href = link.href;
    anchor.dataset.guideKey = link.key;

    const title = document.createElement("strong");
    title.className = template?.titleClassName || "";
    title.textContent = link.label;

    anchor.append(title);
    return anchor;
  }}

  function hydrateGuideCards(root = document, options = {{}}) {{
    const containers = root.querySelectorAll("[data-guide-cards]");
    containers.forEach((container) => {{
      const variant = container.dataset.guideVariant || options.variant || "root";
      const scope = container.dataset.guideScope || options.scope || "nested";
      const firstCard = container.querySelector("a");
      const template = firstCard
        ? {{
            className: firstCard.className,
            titleClassName: firstCard.querySelector("strong")?.className || ""
          }}
        : null;
      const links = relatedLinks(variant, scope);
      container.replaceChildren(...links.map((link) => renderGuideCard(link, template)));
    }});
  }}

  function applyStaticPage({{ variant, scope, document }}) {{
    document.querySelectorAll("[data-series-brand-title]").forEach((node) => {{
      node.textContent = shared.seriesBrand.title;
    }});
    document.querySelectorAll("[data-series-brand-subtitle]").forEach((node) => {{
      node.textContent = shared.seriesBrand.subtitle;
    }});
    hydrateGuideCards(document, {{ variant, scope }});
  }}

  window.GuideSet = {{
    shared,
    normalizeLanguage,
    languageFromLocation,
    withLanguage,
    chooseHref,
    relatedLinks,
    hydrateGuideCards,
    applyStaticPage
  }};

  document.addEventListener("DOMContentLoaded", () => {{
    const body = document.body;
    applyStaticPage({{
      variant: body.dataset.guideKey || "root",
      scope: body.dataset.guideScope || "nested",
      document
    }});
  }});
}})();
'''
    behavior = r'''(function () {
  const storageKey = "oci-networking-workbook-theme";
  const themeButton = document.querySelector(".theme-toggle");
  const backTop = document.querySelector(".back-top");

  function preferredTheme() {
    const saved = localStorage.getItem(storageKey);
    if (saved === "light" || saved === "dark") {
      return saved;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.body.dataset.theme = theme;
    if (themeButton) {
      const isDark = theme === "dark";
      themeButton.textContent = isDark ? "Light mode" : "Dark mode";
      themeButton.setAttribute("aria-pressed", String(isDark));
    }
  }

  applyTheme(preferredTheme());

  themeButton?.addEventListener("click", () => {
    const next = document.body.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem(storageKey, next);
    applyTheme(next);
  });

  document.querySelectorAll(".code-toggle-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".code-card");
      if (!card) {
        return;
      }
      const isCollapsed = card.dataset.collapsed !== "false";
      card.dataset.collapsed = isCollapsed ? "false" : "true";
      button.setAttribute("aria-expanded", String(isCollapsed));
      button.textContent = isCollapsed ? "Collapse" : "Expand";
    });
  });

  document.querySelectorAll(".copy-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest(".code-card");
      const code = card?.querySelector("pre code");
      if (!code) {
        return;
      }
      const text = code.textContent;
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = "Copied";
      } catch (error) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.top = "-1000px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
        button.textContent = "Copied";
      }
      window.setTimeout(() => {
        button.textContent = "Copy";
      }, 1800);
    });
  });

  function safeFileName(value) {
    return value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 96) || "exascale-deployment-readiness-record";
  }

  function normalizeCellText(cell) {
    return cell.innerText.replace(/\s+/g, " ").trim();
  }

  function fixedWidthTable(table) {
    const rows = Array.from(table.querySelectorAll("tr"))
      .map((row) => Array.from(row.children).map(normalizeCellText))
      .filter((row) => row.length > 0);
    if (!rows.length) {
      return "";
    }
    const columnCount = Math.max(...rows.map((row) => row.length));
    const normalizedRows = rows.map((row) => {
      const next = row.slice();
      while (next.length < columnCount) {
        next.push("");
      }
      return next;
    });
    const widths = Array.from({ length: columnCount }, (_, index) =>
      Math.max(...normalizedRows.map((row) => row[index].length), 3)
    );
    const formatRow = (row) =>
      row.map((cell, index) => cell.padEnd(widths[index], " ")).join("  ").trimEnd();
    const header = normalizedRows[0].map((cell) => cell.toUpperCase());
    const separator = widths.map((width) => "-".repeat(width)).join("  ");
    const body = normalizedRows.slice(1);
    return [formatRow(header), separator, ...body.map(formatRow)].join("\n");
  }

  function savedSectionText(section) {
    const title = section.querySelector("h2")?.textContent?.trim() || "Deployment Readiness Record";
    const tables = Array.from(section.querySelectorAll("table"));
    if (!tables.length) {
      return title.toUpperCase();
    }
    const tableText = tables.map(fixedWidthTable).filter(Boolean).join("\n\n");
    return `${title.toUpperCase()}\n\n${tableText}`.trim();
  }

  document.querySelectorAll(".save-section-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const section = button.closest(".saveable-section");
      if (!section) {
        return;
      }
      const title = section.dataset.saveTitle || section.querySelector("h2")?.textContent || "Deployment readiness record";
      const fileName = section.dataset.saveFile || `${safeFileName(title)}.txt`;
      const text = savedSectionText(section);
      const blob = new Blob([text + "\n"], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName.endsWith(".txt") ? fileName : `${fileName}.txt`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      button.textContent = "Saved";
      window.setTimeout(() => {
        button.textContent = "Save .txt";
      }, 1800);
    });
  });

  function updateBackTop() {
    if (!backTop) {
      return;
    }
    backTop.classList.toggle("is-visible", window.scrollY > 520);
  }

  backTop?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", updateBackTop, { passive: true });
  updateBackTop();
})();
'''
    (ROOT / "shared-guide-set.js").write_text(shared, encoding="utf-8")
    (ASSETS_DIR / "workbook.js").write_text(behavior, encoding="utf-8")


def write_maintenance(chapters: list[Chapter]) -> None:
    rows = "\n".join(
        f"| `{chapter.source.name}` | `{chapter.slug}/index.html` | {chapter.short_title} |"
        for chapter in chapters
    )
    text = f"""# OCI PoC RunBook Source and Maintenance

Whenever this workbook is edited, update the visible `Last updated <Month Day, Year>` label in `index.html` to the current publication date.

## Purpose

This file documents the Markdown knowledge source, generated workbook pages, maintenance workflow, and quality checks for the OCI PoC RunBook.

## Source of Record

The editable source of knowledge is the Markdown set in `md/`. Each numbered Markdown file maps to one independent HTML module through its `generated_html` metadata. Keep implementation facts, command examples, tables, checklists, and readiness records in the Markdown source first, then regenerate the HTML.

If a generated HTML file is edited directly during review, treat that HTML edit as temporary. After a successful rebuild, copy accepted direct HTML edits back into the matching Markdown source. Generated HTML alone is not the source of record.

## Generated Page Map

| Source file | HTML module | Module title |
|---|---|---|
{rows}

The root `index.html` provides the workbook entry point, official Oracle documentation groups, glossary, and navigation cards.

## Shared Files

| File | Role |
|---|---|
| `assets/workbook.css` | Shared Oracle-style article layout, code cards, tables, dark mode, responsive rules |
| `assets/workbook.js` | Theme persistence, copy buttons, and Back to top behavior |
| `shared-guide-set.js` | Shared series brand and registry-driven workbook navigation |
| `scripts/build_workbook.py` | Regenerates static HTML from Markdown |
| `scripts/static_html_validator.py` | Runs deterministic static checks on generated HTML |

## Editing Workflow

1. Edit the relevant numbered Markdown file under `md/`.
2. After a successful rebuild, if an HTML file was edited directly, port the accepted content change into the Markdown file named by that page's source mapping.
3. Keep command text and placeholder values exact unless the implementation standard changes.
4. Update source references in `md/15_Reference_Links.md` when a new Oracle documentation dependency is introduced.
5. Run `python3 scripts/build_workbook.py` from the workbook root.
6. Run `python3 scripts/static_html_validator.py index.html */index.html`.
7. Open `index.html` locally and spot-check the edited module.

## Quality Check

The static validator checks generated HTML quality and source hygiene:

- Every numbered Markdown file must declare `source_of_record: true`.
- Every numbered Markdown file must declare the matching `generated_html` module path.
- Every numbered Markdown file must include the rule for copying accepted direct HTML edits back into Markdown after a successful rebuild.
- Every mapped HTML module must exist after the build.
- Generated navigation cards must use names only.
- Deployment readiness records must keep the short `exascale-deployment-readiness-record.txt` save filename.
- OCI CLI examples must use `~/workbook/cli.env` for reusable OCIDs and related variables, source `~/workbook/helpers.sh` before helper usage, and use the workbook `capture_oci_id` helper when create commands return a new OCID under `data.id`.
- Code cards, copy behavior, table wrappers, date labels, favicon guard, and Oracle-style visual tokens must remain valid.

## Editorial Rules

- Keep one operational topic per numbered module.
- Use tables for matrices, inventories, checklists, route rules, and readiness records.
- Keep shell, JSON, policy, diagram, and expected-output examples in fenced code blocks so the build script renders them as copyable code cards.
- Store reusable OCI CLI OCIDs and related variables in `~/workbook/cli.env`; keep `set -a` at the top and `set +a` at the end of that file.
- Store workbook helper functions in `~/workbook/helpers.sh`; examples should source that file with `. ~/workbook/helpers.sh` and load variables with `load_cli_env`.
- Store helper-generated JSON files, temporary OCI CLI output, and route/security-rule artifacts under `~/workbook`.
- Use the workbook `capture_oci_id` helper for OCI create commands that should parse JSON output and write the returned OCID back to `cli.env`; make clear that `capture_oci_id` is not part of OCI CLI.
- Avoid public HTML links to maintenance files or local filesystem paths.
- Keep the educational-use and validation-required notice in the root hero and in every module footer.
- Re-check Oracle documentation before production implementation because regional availability, service labels, CLI syntax, and default behaviors can change.
"""
    (ROOT / "WORKBOOK_SOURCE_AND_MAINTENANCE.md").write_text(text, encoding="utf-8")


def clean_old_chapter_dirs(chapters: list[Chapter]) -> None:
    expected = {chapter.slug for chapter in chapters}
    for child in ROOT.iterdir():
        if child.is_dir() and re.match(r"^\d{2}-", child.name) and child.name not in expected:
            shutil.rmtree(child)


def build() -> None:
    chapters = [parse_chapter(path) for path in sorted(SOURCE_DIR.glob("[0-9][0-9]_*.md"))]
    clean_old_chapter_dirs(chapters)
    write_css()
    write_js(chapters)
    (ROOT / "index.html").write_text(render_root(chapters), encoding="utf-8")
    for chapter in chapters:
        chapter_dir = ROOT / chapter.slug
        chapter_dir.mkdir(exist_ok=True)
        (chapter_dir / "index.html").write_text(render_chapter(chapter, chapters), encoding="utf-8")
    write_maintenance(chapters)
    print(f"Built {len(chapters)} workbook modules in {ROOT}")


if __name__ == "__main__":
    build()
