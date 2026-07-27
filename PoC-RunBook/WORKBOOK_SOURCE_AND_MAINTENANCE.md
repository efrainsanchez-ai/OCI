# OCI PoC RunBook Source and Maintenance

Whenever this workbook is edited, update the visible `Last updated <Month Day, Year>` label in `index.html` to the current publication date.

## Purpose

This file documents the Markdown knowledge source, generated workbook pages, maintenance workflow, and quality checks for the OCI PoC RunBook.

## Source of Record

The editable source of knowledge is the Markdown set in `md/`. Each numbered Markdown file maps to one independent HTML module through its `generated_html` metadata. Keep implementation facts, command examples, tables, checklists, and readiness records in the Markdown source first, then regenerate the HTML.

If a generated HTML file is edited directly during review, treat that HTML edit as temporary. After a successful rebuild, copy accepted direct HTML edits back into the matching Markdown source. Generated HTML alone is not the source of record.

## Generated Page Map

| Source file | HTML module | Module title |
|---|---|---|
| `00_Project_Overview.md` | `00-oci-poc-runbook/index.html` | OCI PoC RunBook |
| `01_Scope_and_Principles.md` | `01-scope-and-design-principles/index.html` | Scope and Design Principles |
| `02_Target_Architecture.md` | `02-target-oci-network-architecture/index.html` | Target OCI Network Architecture |
| `03_Addressing_and_DNS.md` | `03-addressing-naming-and-dns/index.html` | Addressing, Naming, and DNS |
| `04_Bastion_and_Admin_Access.md` | `04-bastion-and-administrator-access/index.html` | Bastion and Administrator Access |
| `05_Network.md` | `05-Network/index.html` | Network |
| `06_Exadata_Environment_Initialization.md` | `06-exadata-environment-initialization/index.html` | Exadata Environment Initialization |
| `07_Bastion_VM_Creation.md` | `07-bastion-vm-creation/index.html` | Bastion VM Creation |
| `08_Create_Exadata_Cluster.md` | `08-create-exadata-cluster/index.html` | Create Exadata Cluster |
| `09_Upscale_Cluster_To_Two_Nodes.md` | `09-upscale-the-cluster-to-two-nodes/index.html` | Upscale the Cluster to Two Nodes |
| `10_Create_Container_Database.md` | `10-create-container-database/index.html` | Create Container Database |
| `11_Bastion_And_Cluster_SSH_Connection.md` | `11-bastion-and-cluster-ssh-connection/index.html` | Bastion and Cluster SSH Connection |
| `12_Enable_Automatic_Backups.md` | `12-enable-automatic-backups/index.html` | Enable Automatic Backups |
| `13_Create_Database_Credential_Secrets.md` | `13-create-database-credential-secrets/index.html` | Create Database Credential Secrets |
| `14_OCI_Database_Management.md` | `14-oci-database-management/index.html` | OCI Database Management |
| `15_OCI_File_Storage_Mounts.md` | `15-oci-file-storage/index.html` | OCI File Storage |
| `16_Stop_And_Start_Services.md` | `16-stop-and-start-services/index.html` | Stop and Start Services |
| `17_Recover_Variables.md` | `17-recover-variables/index.html` | Recover Variables |
| `18_Create_New_PDB.md` | `18-create-new-pdb/index.html` | Create New PDB |

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
- OCI CLI examples must use `~/workbook/cli.env` for reusable OCIDs and related variables, source `~/workbook/lib/helpers.sh` before helper usage, and use the workbook `capture_oci_id` helper when create commands return a new OCID under `data.id`.
- Code cards, copy behavior, table wrappers, date labels, favicon guard, and Oracle-style visual tokens must remain valid.

## Editorial Rules

- Keep one operational topic per numbered module.
- Use tables for matrices, inventories, checklists, route rules, and readiness records.
- Keep shell, JSON, policy, diagram, and expected-output examples in fenced code blocks so the build script renders them as copyable code cards.
- Store reusable OCI CLI OCIDs and related variables in `~/workbook/cli.env`; keep `set -a` at the top and `set +a` at the end of that file.
- Store workbook helper functions in `~/workbook/lib/helpers.sh`; examples should source that file with `. ~/workbook/lib/helpers.sh` and load variables with `load_cli_env`.
- Store helper-generated JSON files, temporary OCI CLI output, and route/security-rule artifacts under `~/workbook`.
- Use the workbook `capture_oci_id` helper for OCI create commands that should parse JSON output and write the returned OCID back to `cli.env`; make clear that `capture_oci_id` is not part of OCI CLI.
- Avoid public HTML links to maintenance files or local filesystem paths.
- Keep the educational-use and validation-required notice in the root hero and in every module footer.
- Re-check Oracle documentation before production implementation because regional availability, service labels, CLI syntax, and default behaviors can change.
