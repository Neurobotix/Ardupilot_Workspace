# Scripts

Workspace scripts live here. Use `scripts/ops/` for operator entrypoints,
`scripts/maintenance/` for validators and maintenance checks, and `scripts/dev/`
for development helpers.

`scripts/dev/report_generation/` holds the Markdown-to-PDF report renderer
(`pdf.py`, `theme.md`, `report_template.md`). It is a development helper, not
the governed evidence workflow.

`scripts/dev/decision_page/` builds a self-contained HTML page from a JSON
list of decisions (one card per decision, a recommended option each, and an
export of the answers). See its README for the spec.

## Naming

- Shell scripts use `lower_snake_case.sh`.
- Python scripts use `lower_snake_case.py`.
- Directory names use `lower_snake_case`.
- Date prefixes are not required for stable scripts.
- Keep external tool names only when a tool requires a specific file name.

Document new operator-facing scripts in the nearest README and update
`governance/standards/change_control.md` or `.ai/index.md` only when the script
becomes a canonical workflow entrypoint.
