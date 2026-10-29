# CRISP sample catalog (made up)

Sample content that shows what the Knowledge Catalog looks like and how the Assessment Processor reads it.
**Illustrative only.** The NIST control IDs (SP 800-53 Rev 5) are real, but the requirement wording, decisions,
rules, risk method, thresholds, patterns, targets, owners, dates and approvals are made up. Cyber leadership
confirms the NIST publication and revision.

## Folder map (catalog task in brackets)

| Path | What it holds |
|---|---|
| `catalog.yaml` | Manifest: version, framework basis, list of files |
| `vocabulary.yaml` | Shared terms (2.1) |
| `framework/adoption.yaml` | Adopt, tailor or exclude decisions with reason and date (1.x) |
| `requirements/*.yaml` | 17 requirements with owner, source, NIST reference, evidence definition (2.x) |
| `rules/project-attributes.yaml` | Project details, allowed values, where each comes from (3.1, 3.2) |
| `rules/classification-rules.yaml` | Puts a project in tier 1, 2 or 3 |
| `rules/applicability-rules.yaml` | 9 rules: which requirements apply and why (3.3) |
| `rules/override-reasons.yaml` | Standard override reasons (3.4) |
| `patterns-targets/patterns.yaml`, `targets.yaml` | 2 patterns, targets per tier, how each is measured (4.x) |
| `threat-modeling/` | Methods, trigger and selection rules, threat library with requirement links, completeness checklist (5.x) |
| `risk/risk-methodology.yaml` | Factors, scales, thresholds, inherent and residual risk, overrides, worked examples (6.x) |
| `process/change-process.yaml`, `change-log.yaml` | Versioning, approvals, release steps, example change records (7.x) |
| `project/sample-project.yaml` | A made-up project to try the catalog on |
| `tools/crisp_catalog.py` | `validate`, `build` and `assess` (needs Python 3 and PyYAML) |
| `dist/catalog-1.0.0.json` | The built release bundle. This is what the assessor reads |
| `sample-output.txt` | Output of `assess` on the sample project |

## Try it

    python3 tools/crisp_catalog.py validate   # checks links, owners, evidence, thresholds
    python3 tools/crisp_catalog.py build      # writes dist/catalog-1.0.0.json
    python3 tools/crisp_catalog.py assess     # applies the pinned release to the sample project

## How the pieces connect

1. The project's attributes (data class, exposure, criticality, type...) are matched by the **classification rules** (category) and **applicability rules** (requirements, each with a reason and rule version).
2. Threats found in the project's threat model add the requirements linked to them in the **threat library**.
3. Each requirement's **evidence definition** says what counts as addressed or partly addressed. The status comes from the evidence, not from opinion.
4. The **risk methodology** turns attributes into an inherent score and status into a residual score and rating.
5. The project's category picks the **target** it must reach.
6. The project is **pinned** to catalog version 1.0.0. A later release changes nothing for it unless an approved move is made.
