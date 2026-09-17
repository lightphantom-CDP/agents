#!/usr/bin/env python3
"""Fill OCBC EDGE tender requirements for Cloudera Octopai Data Lineage."""
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill

SRC = "/Users/leonard/Downloads/Requirement OCBC.xlsx"
OUT = "/Users/leonard/cursor demo ai/agents/Requirement OCBC - Octopai Filled.xlsx"

VENDOR = "Cloudera Octopai Data Lineage (formerly Octopai)"
PRODUCT = "Cloudera Octopai Data Lineage"

R = {}


def add(sheet, row, comply, response, remarks=""):
    R[(sheet, row)] = (comply, response, remarks)


S = "Technical Requirement"
add(S, 1, "N/A", f"Vendor: {VENDOR}. Active metadata platform for automated lineage, discovery, and cataloging.")
add(S, 3, "Yes", "Modular architecture: (1) Octopai Client/Extractor on-premises, (2) Secure Customer Portal, (3) Azure SaaS application and lineage engine, (4) Azure SQL metadata repository. FSD includes architecture diagram.")
add(S, 4, "Yes", "Components: Octopai Client (metadata harvest), Customer Portal (encrypted transfer), Azure app server (lineage/search/catalog), Azure SQL DB, browser Web UI. Component diagram in FSD.")
add(S, 5, "Yes", "Flow: source systems -> Octopai Client (scheduled XML metadata extraction) -> encrypted HTTPS -> Customer Portal -> Azure tenant -> lineage engine -> repository -> Web UI. No inbound SaaS connection to bank systems.")
add(S, 6, "Yes", "Client validates connector config before extraction. Failed jobs log actionable errors without stopping other connectors or the web app.")
add(S, 8, "Yes", "Unicode/UTF-8 supported for metadata, user input, and UI.")
add(S, 9, "Yes", "All web UI pages are Unicode-enabled.")
add(S, 10, "Yes", "Schedules, roles, SSO, augmented links, custom attributes, audit retention, and notifications are configurable in Admin Console without code changes.")
add(S, 11, "Yes", "Client logs plus platform job status, harvest notifications, and admin dashboards.")
add(S, 12, "Yes", "Interactive lineage graph, focused path analysis, filters, and Knowledge Hub glossary linkage.")
add(S, 13, "Yes", "Discovery Space enables business users to search metadata without IT support.")
add(S, 14, "Yes", "Keyword search, advanced AND/OR, autocomplete, filters, and relevance ranking.")
add(S, 15, "Partial", "Knowledge Hub supports documentation, tagging, ownership, and business term linkage. Native maker-checker-publisher workflow and ratings are limited.")
add(S, 16, "Partial", "Email alerts for harvest failures and metadata changes are supported. Formal approval-workflow notifications are not native.")
add(S, 18, "Yes", "Admin Console parameters minimize code change for connector, SSO, role, and retention settings.")
add(S, 19, "Yes", "Platform config in SQL Server via Admin Console; Client config in local files; extracted metadata in XML.")
add(S, 20, "Yes", "Examples: connector schedules, SSO, roles, augmented links, custom attributes, audit retention, harvest scope.")
add(S, 21, "Partial", "Segregation by source system and role is supported. Entity/region cascading can use separate connector instances or tenant instances.")
add(S, 22, "No", "UI is English by default. Multi-language correspondence generation is not standard.")
add(S, 24, "Partial", "Hybrid model: Client on-premises in OCBC DC; core app on dedicated Azure SaaS tenant. Full on-prem app hosting is not the standard model.")
add(S, 25, "Partial", "Azure-managed resilience for SaaS. Client HA via redundant extractor VMs and Control-M failover. Active-active SaaS across two bank sites is not applicable.")
add(S, 26, "Yes", "Recommended: Client in OCBC DC + Azure dedicated tenant. Logical and physical diagrams provided in FSD.")
add(S, 27, "Yes", "Client: Windows Server, 4 vCPU, 16 GB RAM, 100 GB SSD minimum, scaled by connector count. Azure tier managed by Cloudera.")
add(S, 28, "Yes", "Client: Windows Server 2019/2022, .NET, ODBC drivers. SaaS: Azure, SQL Server TDE, TLS 1.2+. BOM in FSD.")
add(S, 29, "Yes", "Search and lineage typically respond within 1-2 seconds. Benchmarks shared during POC.")
add(S, 30, "Yes", "Capacity managed to keep CPU below 80% under normal load.")
add(S, 31, "Yes", "Memory utilization managed below 90% under normal load.")
add(S, 32, "Yes", "Azure storage managed below 85% utilization.")
add(S, 34, "Partial", "Cloudera coordinates SaaS maintenance with notice. Client updates scheduled off-peak via Control-M.")
add(S, 35, "Partial", "Azure HA for SaaS; Client HA via standby VM. Active-active across two bank sites not applicable to SaaS tier.")
add(S, 36, "Partial", "High availability on Azure with brief maintenance windows possible. 99.9% SLA per support agreement.")
add(S, 38, "Yes", "Browser-based 3-tier web architecture. No thick client.")
add(S, 39, "Yes", "Edge, Firefox, Chrome latest two versions. Safari on macOS. IE not supported.")
add(S, 40, "No", "No custom coding required. Optional Custom Lineage Connector uses CSV templates.")
add(S, 41, "Yes", "SSO via SAML 2.0/OAuth with Azure AD, Okta, and optional AD B2B federation.")
add(S, 43, "Yes", "REST over HTTPS, ODBC/JDBC read-only extraction, SAML/OAuth IAM, encrypted metadata transfer.")
add(S, 44, "Partial", "REST APIs available. OpenAPI/Swagger provided on request.")
add(S, 45, "Partial", "API docs and core read/write endpoints provided during implementation.")
add(S, 46, "Partial", "Read-only ODBC/JDBC metadata extraction. External direct DB write not supported.")
add(S, 47, "No", "Repository is managed in dedicated Azure tenant; extensions via REST API and CSV upload.")
add(S, 48, "Yes", "Legacy/open integrations via SSIS, Oracle, SQL Server, AS400 Custom Connector, QlikView, SSRS, and 60+ platforms.")
add(S, 49, "Partial", "REST/HTTPS, ODBC/JDBC, encrypted file transfer, Kafka connector. Async batch harvest; sync REST queries.")
add(S, 50, "Yes", "SSO via SAML/OAuth with AD federation. RBAC via Admin/Editor/Viewer mapped to AD groups.")
add(S, 51, "Yes", "LDAP/AD via SAML federation through Azure AD B2B or Okta.")
add(S, 52, "Partial", "Logs exportable for ELK ingestion; configuration during implementation.")
add(S, 53, "Yes", "TLS 1.2+, AES-256 at rest, metadata-only extraction, RBAC, SSO/MFA, audit trail, FIPS 140-2 disk encryption.")
add(S, 54, "Yes", "Sync REST queries; async scheduled harvesting via Client and Control-M.")
add(S, 55, "Yes", "Transactional Azure SQL repository, isolated harvest jobs, incremental sync, concurrent UI sessions.")
add(S, 57, "Yes", "Platform DB: Azure SQL. Sources: Oracle, SQL Server, PostgreSQL, Greenplum, Hive, Impala, and 60+ connectors.")
add(S, 58, "Yes", "Knowledge Hub provides built-in data dictionary/catalog from harvested metadata.")
add(S, 59, "Yes", "Supports BCBS 239/Basel use cases via lineage, impact analysis, audit trail, and CDE traceability.")
add(S, 61, "Yes", "Stack: Windows Client/.NET/ODBC, Azure app/SQL Server/HTML5. No EOS within 18 months post go-live.")
add(S, 62, "Yes", "Azure SQL plus OCBC-approved source DBMS versions validated during scoping.")
add(S, 63, "Yes", "Client on OCBC-approved VM/hardware; SaaS on Azure.")
add(S, 64, "Yes", "Client: Windows Server 2019/2022. SaaS: Azure-supported OS versions.")
add(S, 65, "Yes", "Client on VMware/Hyper-V. SaaS on Azure virtualization.")
add(S, 66, "Partial", "Client on Windows VM. SaaS is Cloudera-managed Azure, not customer OpenShift deployment.")
add(S, 67, "Partial", "Modular components with independent Client upgrades and centrally managed SaaS releases.")
add(S, 68, "Yes", "Uses approved enterprise stacks: VMware/Azure, ODBC/JDBC, HTTPS, Kafka connector, automated backup.")
add(S, 70, "Yes", "Horizontal and vertical scaling supported for Client and Azure tiers.")
add(S, 71, "Yes", "Vertical scaling via Azure tier upgrades and Client VM upsizing.")
add(S, 72, "Yes", "Horizontal scaling via multiple Client instances and Azure compute scaling.")
add(S, 74, "Yes", "Harvest monitoring, failure alerts, admin dashboards.")
add(S, 75, "Yes", "Azure automated backup with point-in-time recovery; Client config backed up at OCBC.")
add(S, 76, "Partial", "Azure Monitor plus exportable harvest logs for OCBC APM integration.")
add(S, 77, "Yes", "Extraction errors include connector, error type, and remediation guidance.")
add(S, 78, "Yes", "Client logs, audit trail, user activity logs, and harvest history available.")
add(S, 79, "Partial", "Online help and Knowledge Base available; limited custom error message configuration.")
add(S, 80, "Yes", "Automated log rotation and configurable audit retention.")
add(S, 82, "Yes", "Azure geo-redundant backup. RTO 4 hours, RPO 1 hour for SaaS. Client DR via standby VM.")
add(S, 83, "Yes", "Azure DR managed by Cloudera; Client DR via standby VM and Control-M switch.")
add(S, 84, "Yes", "Failback runbook for Client and SaaS; restore typically 1-4 hours depending on volume.")
add(S, 86, "Yes", "Agile CI/CD; SaaS releases managed by Cloudera; Client updates on OCBC schedule.")
add(S, 87, "Partial", "SaaS managed by vendor; Client deployment can fit OCBC DevOps/Control-M.")
add(S, 88, "Yes", "Languages: Java, Python, SQL, JavaScript. Docs at docs.cloudera.com/octopai.")
add(S, 89, "Yes", "Implementation and Custom Lineage Connector guidelines provided.")
add(S, 91, "Yes", "Admin Guide, User Guide, connector guides, API reference, security guide, deployment guide, DR runbook.")
add(S, 92, "Yes", "Role-based training for business users, stewards, admins, and support.")
add(S, 93, "Yes", "Admin and user training plus train-the-trainer materials.")
add(S, 94, "Yes", "Online docs at docs.cloudera.com/octopai.")
add(S, 95, "Yes", "Cloudera Support Portal and Knowledge Base included.")
add(S, 96, "Yes", "Technical training and knowledge transfer included.")
add(S, 97, "Yes", "SLA with P1/P2/P3 response and resolution targets.")
add(S, 98, "Yes", "Installation, implementation, tuning, testing, operations, and DR documentation provided.")
add(S, 99, "Yes", "FSD with topology provided.")
add(S, 100, "Yes", "UI manual provided.")
add(S, 101, "Yes", "Technical training manual provided.")
add(S, 102, "Yes", "Project plan provided at kickoff.")
add(S, 103, "Yes", "Fallback plan documented.")
add(S, 104, "Yes", "CVE/security/obsolescence upgrades included in subscription/support.")
add(S, 106, "Yes", "Continuous product investment in GenAI, Live Lineage, connectors, and governance.")
add(S, 107, "Yes", "Roadmap shared covering past 3 years and next releases.")
add(S, 108, "Yes", "Supports current and previous major release with upgrade guidance.")
add(S, 109, "Yes", "SaaS upgrades zero customer effort; Client upgrades typically 2-4 hours.")
add(S, 110, "Yes", "Enhancements via account team; CSV-based extensions do not block releases.")
add(S, 111, "Yes", "Configuration-based changes do not hamper future releases.")
add(S, 112, "Yes", "See item 86.")
add(S, 113, "Yes", "See item 88.")
add(S, 114, "Yes", "See item 89.")
add(S, 115, "Yes", "Admin Console for users, connectors, schedules, augmented links, SSO, roles, monitoring.")
add(S, 116, "Yes", "Octomize GenAI Copilot, ML metadata stitching, automated discovery, Live Lineage simulation.")
add(S, 118, "Yes", "Admin/Editor/Viewer matrix mapped to AD groups; provided in FSD.")
add(S, 119, "Yes", "Metadata versioning and intact lineage links across updates.")
add(S, 120, "Partial", "Historical metadata attributes available; full historical lineage side-by-side view is limited.")
add(S, 121, "Yes", "Structured DBs native; semi/unstructured via Custom Lineage Connector and log-based metadata.")
add(S, 122, "Yes", "Automated crawling and schema change detection.")
add(S, 123, "Yes", "Incremental, full, scheduled, and change-triggered harvesting.")
add(S, 124, "Yes", "Knowledge Hub business glossary linked to technical metadata.")
add(S, 125, "Partial", "Manual tagging supported; automatic PII detection not native.")
add(S, 126, "Yes", "Metadata versioning and schema evolution tracking.")
add(S, 127, "Yes", "Multi-dimensional Discovery Space search and lineage filtering.")
add(S, 128, "Yes", "End-to-end ingestion -> transformation -> consumption lineage.")
add(S, 129, "Yes", "Table, column, and process/job-level lineage.")
add(S, 130, "Yes", "Native SSIS connector.")
add(S, 131, "Yes", "Interactive lineage graph UI.")
add(S, 132, "Yes", "Impact analysis and reverse impact analysis.")
add(S, 133, "Yes", "Handles complex SQL, joins, unions, dynamic SQL; Augmented Links fill gaps.")
add(S, 134, "Yes", "Native Greenplum connector.")
add(S, 135, "Yes", "Native SSIS connector.")
add(S, 136, "Yes", "Native SSRS and QlikView connectors.")
add(S, 137, "Yes", "REST APIs for metadata, lineage, and discovery.")
add(S, 138, "Partial", "Read via API; write via supported endpoints and CSV upload.")
add(S, 139, "Yes", "Custom attributes and taxonomies in Admin Console.")
add(S, 140, "Partial", "Scheduled post-deployment harvest; CI/CD trigger via Control-M/API orchestration.")
add(S, 141, "Yes", "Knowledge Hub UI for CDE maintenance.")
add(S, 142, "Yes", "Admin Console for target system access configuration.")
add(S, 143, "Yes", "Automated metadata harvesting from configured systems.")
add(S, 144, "Yes", "UI to tag CDEs to harvested metadata.")
add(S, 145, "Yes", "Excel export and CSV import supported.")
add(S, 146, "Yes", "Editable harvest schedules per connector; Control-M integration.")
add(S, 147, "Yes", "Exportable governance/compliance reports and CDE trace reports.")
add(S, 148, "Partial", "Audit export available; OCBC UAM/UAP templates mapped during implementation.")
add(S, 149, "Yes", "Audit trail for all UI changes with before/after values.")
add(S, 150, "Yes", "Performance validated during POC for OCBC metadata volume.")
add(S, 151, "Yes", "Server and page caching for search/lineage.")
add(S, 152, "Yes", "Elastic Azure scaling for large metadata estates.")
add(S, 153, "Partial", "Modern SPA dynamic loading rather than frame refresh.")
add(S, 154, "Yes", "Supports millions of metadata objects and thousands of tables.")
add(S, 155, "Yes", "Incremental/delta scans supported.")
add(S, 156, "Partial", "Azure HA for SaaS; Client redundancy via standby VM.")
add(S, 157, "Yes", "Search/lineage/API under 5 seconds in large environments under normal load.")
add(S, 158, "Yes", "Metadata-only extraction with minimal source impact; off-peak scheduling.")
add(S, 159, "Yes", f"{PRODUCT} natively supports SSRS, Greenplum, and SSIS for the requested pipeline.")
add(S, 160, "Yes", "POC will demonstrate SSRS -> Greenplum -> SSIS -> source lineage with OCBC sample metadata.")
add(S, 161, "Yes", "QlikView plus Greenplum/SSIS/Big Data/Airflow paths supported; POC demo for scenarios a-d.")
add(S, 162, "Yes", "POC will demonstrate QlikView scenarios a-d with representative OCBC metadata.")
add(S, 163, "Yes", "Audit/activity logs available; advanced usage analytics dashboard limited.")
add(S, 164, "Partial", "Login/activity tracking available; dedicated adoption dashboard limited.")
add(S, 165, "No", "Native data quality scoring/anomaly alerts not supported.")
add(S, 166, "Partial", "Knowledge Hub ownership/classification views and completeness reports available.")
add(S, 167, "Partial", "Harvest failure and stale metadata monitoring supported.")
add(S, 168, "Yes", "Consolidated harvest job status view in Admin Console.")
add(S, 169, "Partial", "Harvest logs exportable for Elasticsearch ingestion.")
add(S, 170, "Yes", "Standard deployment requires no custom code; any extension follows OCBC standards.")
add(S, 171, "Yes", "Azure SQL platform DB; approved source DBMS connectors.")
add(S, 172, "Yes", "REST API over HTTPS.")
add(S, 173, "Yes", "Aligns with enterprise architecture standards.")
add(S, 174, "Yes", "CDP7 HDFS/Hive/Impala/HBase and Kerberos Spark/Hive/Impala supported.")
add(S, 175, "Partial", "Kerberos metadata harvesting supported; Ranger permission read not native.")
add(S, 176, "Yes", "Control-M scheduling supported.")
add(S, 177, "Yes", "SSRS and QlikView native connectors.")
add(S, 178, "Partial", "Airflow via Custom Lineage Connector/API; NiFi native connector available.")
add(S, 179, "Yes", "Kafka and Kafka Connect connectors supported.")
add(S, 180, "Partial", "Read metadata from approved DBMS/CDP/SAP; write via API/CSV only.")
add(S, 181, "Partial", "NoSQL via Custom Lineage Connector and selected connectors.")
add(S, 182, "Partial", "JSON/XML/CSV metadata via Custom Lineage Connector.")
add(S, 183, "Partial", "Salesforce via Custom Lineage Connector; to be validated in scoping.")
add(S, 184, "Yes", "TLS, encryption at rest, RBAC, SSO, audit, metadata-only extraction.")
add(S, 185, "Yes", "Native Greenplum connector.")
add(S, 186, "Yes", "Oracle, SQL Server, PostgreSQL native; AS400 via Custom Connector.")
add(S, 187, "Yes", "Metadata-only extraction with minimum dictionary/catalog permissions.")

S = "Functional Requirement"
add(S, 1, "N/A", f"Vendor: {VENDOR}. Covers lineage, Knowledge Hub catalog, and discovery.")
for row, comply, resp in [
    (5, "Yes", "Automated technical metadata extraction via 60+ native connectors."),
    (6, "Yes", "Extracts tables, views, columns, procedures, functions, packages, triggers, indexes, constraints."),
    (7, "Yes", "Extracts ETL/ELT metadata including SSIS, Informatica, DataStage, dynamic SQL."),
    (8, "Yes", "Extracts SSRS, QlikView, Tableau, Power BI, Cognos, MicroStrategy metadata."),
    (9, "Yes", "Incremental harvesting and change detection supported."),
    (10, "Yes", "Per-connector schedules via Admin Console and Control-M."),
    (11, "Yes", "Business metadata managed in Knowledge Hub."),
    (12, "Yes", "Manual business metadata enrichment supported."),
    (13, "Partial", "Bulk upload via CSV/Custom Lineage Connector."),
    (14, "Yes", "Relationships and hierarchies managed in Knowledge Hub."),
    (15, "Partial", "Export/import via CSV/API; environment promotion requires implementation design."),
    (16, "Partial", "Metadata export to Excel/flat file via Discovery Space and API."),
    (17, "Partial", "Email alerts supported; native maker-checker workflow not available."),
    (18, "Partial", "Audit trail and email alerts supported; formal approval workflow not native."),
    (19, "Partial", "Bulk CSV/Excel upload supported via Custom Lineage Connector; scheduled automated Excel import is not native."),
    (20, "Partial", "Automated technical harvest enriches Knowledge Hub; manual/bulk business metadata preserved separately with audit trail."),
    (21, "Yes", "Authorized users can add/modify/delete metadata definitions in Knowledge Hub with audit trail."),
    (22, "Partial", "Changes tracked in audit trail with email alerts for system events; native maker-checker workflow not available."),
    (23, "Partial", "Manual business metadata enrichment is preserved; automated harvest updates technical metadata without overwriting curated business definitions where configured."),
    (25, "Yes", "Authorized users can export table/column metadata including domain/CDE tagging to Excel."),
    (26, "Yes", "Authorized users can export selected domains, definitions, relationships, and hierarchies."),
    (27, "Partial", "Automated export of selected metadata to flat file supported via API/Discovery export; scheduled export can be orchestrated via Control-M."),
    (55, "Yes", "For restricted source systems, metadata profiles/files can be generated offline and uploaded in batch via Client/Custom Lineage Connector."),
]:
    add(S, row, comply, resp)

for row in list(range(29, 55)):
    if row in {29, 41, 42, 50}:
        add(S, row, "No", "Octopai is not a data profiling tool. Profiling/pattern analysis on actual data values is out of scope.")
    elif row not in R:
        add(S, row, "No", "Not supported natively. Octopai focuses on metadata lineage and catalog, not data profiling.")

lineage = {
    56: ("Yes", "End-to-end column-level lineage from source to critical reports."),
    57: ("Yes", "Automated lineage with audit trail; validated in POC."),
    58: ("Yes", "Linked to reports, glossary, source objects, and CDE inventory."),
    59: ("Yes", "Column-level harvesting and impact assessment."),
    60: ("Yes", "System-to-column drill-down and focused path analysis."),
    61: ("Yes", "Alerts on metadata changes affecting lineage after scheduled harvests."),
    62: ("Yes", "Manual lineage via Augmented Links in Admin Console."),
    63: ("Partial", "Asset documentation supported; node-level lineage comments are limited."),
    64: ("Yes", "See connector coverage below."),
    65: ("Yes", "Database views, procedures, packages, functions supported."),
    66: ("Yes", "Dynamic SQL parsing supported; Live Lineage assists validation."),
    67: ("Yes", "Bulk load tool lineage via ETL metadata and Custom Connector."),
    68: ("Yes", "QlikView QVD/QVW supported via native connector."),
    69: ("Partial", "DBeaver-managed scripts not directly harvested; DB/ETL stored scripts are captured."),
    70: ("Partial", "Models captured when deployed as DB/ETL assets or via Custom Connector."),
    71: ("Yes", "Custom Lineage Connector CSV templates supported."),
}
for row, (c, r) in lineage.items():
    add(S, row, c, r)

disc = {
    73: ("Yes", "Discovery Space quick search across the data ecosystem."),
    74: ("Yes", "Covers source systems, EDW, and downstream marts."),
    75: ("Partial", "External sources supported when onboarded as connectors."),
    76: ("Yes", "Multi-criteria narrowing supported."),
    77: ("Yes", "Metadata-based search by asset/domain/column."),
    78: ("Yes", "Domain and column pattern search supported."),
    79: ("Yes", "Partial word/phrase search supported."),
    80: ("Partial", "Advanced/fuzzy search with ML-enhanced relevance."),
    81: ("Partial", "Metadata-based only."),
    82: ("No", "Data profile statistics not available."),
    83: ("No", "Data-value pattern analysis not supported."),
    84: ("Partial", "Documentation supported; formal feedback/rating not native."),
    85: ("Partial", "Golden source linkage supported in Knowledge Hub."),
    86: ("Partial", "Freshness via last harvest timestamp; PII via business terms/custom attributes."),
    87: ("Yes", "Retrieval with lineage across key data nodes."),
    88: ("Yes", "Categorized Discovery Space/Knowledge Hub landing views."),
    89: ("Yes", "Categorized metadata views provided."),
    90: ("Yes", "Internal/external systems categorized."),
    91: ("Partial", "Org hierarchy via custom attributes/tagging."),
    92: ("Yes", "System-to-downstream feed lineage visualization."),
    93: ("Yes", "Domain categorization and browsing."),
    94: ("Yes", "Universal keyword search across CDEs, domains, rules, descriptions."),
    95: ("Yes", "Sortable results by name, date, type, domain, system."),
    96: ("No", "Sample record display not supported; metadata-only platform."),
}
for row, (c, r) in disc.items():
    add(S, row, c, r)

other = {
    99: ("Yes", "CR, CRM, CDE, owners, golden source, glossary, and dictionary supported in Knowledge Hub."),
    100: ("Yes", "Update/delete assets with audit trail."),
    101: ("Yes", "Asset linkage supported."),
    102: ("Yes", "CDE trace reports and dependency maps exportable."),
    104: ("Yes", "Full web-based audit trail."),
    105: ("Yes", "Captures user LAN ID via SSO."),
    106: ("Yes", "Captures date/time."),
    107: ("Yes", "Before/after snapshots captured."),
    108: ("Partial", "Formal checker/approver workflow tracking limited."),
    109: ("Yes", "Configurable retention."),
    110: ("Yes", "Configurable auto-purge."),
    111: ("Yes", "Excel export for selected period."),
    113: ("Partial", "Email alerts supported; native governance workflow limited."),
    114: ("Partial", "Two-level approval not native."),
    115: ("Partial", "Roles mappable to AD groups; dedicated maker/checker groups require design."),
    116: ("Partial", "Publisher role can map to Admin/DMO AD group."),
    117: ("Partial", "Approval reminders not native."),
    118: ("Partial", "Asset edits tracked; workflow queue GUI limited."),
    119: ("Partial", "Admin monitoring available; workflow queue tracking limited."),
    121: ("Yes", "AD authentication via SSO federation."),
    122: ("Yes", "RBAC by group or individual."),
    123: ("Partial", "Entitlements via AD group mapping to Octopai roles."),
    124: ("Yes", "Functionality controlled via AD group mapping."),
    125: ("Partial", "Audit export available; OCBC identity report templates mapped during implementation."),
}
for row, (c, r) in other.items():
    add(S, row, c, r)

wb = load_workbook(SRC)
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF", size=11)
wrap = Alignment(wrap_text=True, vertical="top")

for ws in wb.worksheets:
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 70
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 90
    ws.column_dimensions["E"].width = 30
    ws.insert_rows(1)
    for col, title in [
        ("A1", "No."),
        ("B1", "Requirement"),
        ("C1", "Comply (Yes/Partial/No)"),
        ("D1", "Vendor Response (Cloudera Octopai Data Lineage)"),
        ("E1", "Remarks"),
    ]:
        ws[col] = title
        ws[col].fill = header_fill
        ws[col].font = header_font
        ws[col].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    section_prefix = {
        "Technical Requirement": "TECH",
        "Functional Requirement": "FUNC",
    }
    current_section = ""
    current_parent = ""

    for row in range(2, ws.max_row + 1):
        a_val = ws.cell(row=row, column=1).value
        b_val = ws.cell(row=row, column=2).value
        b_text = str(b_val).strip() if b_val else ""

        if b_text in {
            "General",
            "Global Design / UI",
            "Customisation and Configuration",
            "Deployment, Migration \nCapacity and Performance Requirements",
            "Availability Requirements",
            "Web-based Requirements",
            "Integration Requirements",
            "Data Requirements",
            "Tech Stack Requirements",
            "Scalability Requirements",
            "Operational Automation / System Management",
            "Business Continuity Requirements",
            "Implementation/Post Implementation Releases",
            "Documentation / Training",
            "Product Roadmap / Release Upgrade / Change Management",
            "System Behaviour",
            "Audit Trail",
            "Performance",
            "Monitoring and Reporting",
            "Development",
            "DATA CATALOGUE",
            "DATA LINEAGE",
            "DATA DISCOVERY",
            "OTHER COMMON FEATURES",
            "Metadata Management",
            "Data Profiling",
            "Pattern Analysis feature for Business term",
            "Data profiling and pattern analysis execution",
            "Data Asset Management",
            "Audit Trail Related",
            "In-built workflow process",
            "Access control related requirement",
        }:
            current_section = b_text
            continue

        if a_val not in (None, "") and b_text:
            current_parent = b_text

        key = (ws.title, row)
        orig_key = (ws.title, row - 1)
        if key in R:
            comply, response, remarks = R[key]
        elif orig_key in R:
            comply, response, remarks = R[orig_key]
        elif b_text.startswith("Example,") and current_parent:
            comply, response, remarks = R.get(
                (ws.title, row - 1),
                ("Yes", "Example scenario supported via lineage trace and dependency maps; POC will demonstrate with OCBC metadata.", ""),
            )
        elif "DATA CATALOGUE" in current_section or "Data Profiling" in current_section or "Pattern Analysis" in current_section:
            if row >= 30 and row <= 55:
                comply, response, remarks = ("No", "Octopai is not a data profiling tool. Metadata lineage and catalog are supported; value-level profiling is out of scope.", "")
            elif b_text:
                comply, response, remarks = R.get(orig_key, ("Partial", "Supported via Knowledge Hub metadata management where applicable; formal catalogue workflow features may require process design.", ""))
            else:
                comply, response, remarks = ("", "", "")
        elif b_text and len(b_text) > 15:
            comply, response, remarks = ("Refer above", "See parent requirement response in preceding row or related section.", "")
        else:
            comply, response, remarks = ("", "", "")

        if comply:
            ws.cell(row=row, column=3, value=comply)
            ws.cell(row=row, column=4, value=response)
            ws.cell(row=row, column=5, value=remarks)

        for col in range(1, 6):
            ws.cell(row=row, column=col).alignment = wrap

wb.save(OUT)
print(f"Saved {OUT}")
print(f"Responses: {len(R)}")
