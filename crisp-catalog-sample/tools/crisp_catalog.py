#!/usr/bin/env python3
"""Sample tool for the CRISP catalog.
  validate  check the catalog files for mistakes (run on every proposed change)
  build     turn the catalog files into one JSON bundle for a release
  assess    read the JSON bundle and apply it to the sample project
Needs Python 3 and PyYAML. Run from the catalog folder:  python3 tools/crisp_catalog.py validate
"""
import sys, json, math, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
def load(rel): return yaml.safe_load((ROOT / rel).read_text())

def load_catalog():
    m = load("catalog.yaml"); c = {"manifest": {k: m[k] for k in ("catalog_id", "version", "status", "framework_basis")}}
    for key, files in m["files"].items():
        parts = [load(f) for f in files]
        c[key] = parts[0] if len(parts) == 1 else [x for p in parts for x in p]
    return c

# ---------- rule evaluation (the same few lines every time) ----------
def cond(c, attrs): return attrs.get(c["attribute"]) in c["in"]
def matches(when, attrs):
    if when == "always": return True
    if "all" in when: return all(cond(c, attrs) for c in when["all"])
    if "any" in when: return any(cond(c, attrs) for c in when["any"])
    raise ValueError(when)
def all_conds(when):
    if when == "always": return []
    return when.get("all", []) + when.get("any", [])

# ---------- validate ----------
def validate(c):
    errs, warns = [], []
    reqs = {r["id"]: r for r in c["requirements"]}
    if len(reqs) != len(c["requirements"]): errs.append("duplicate requirement ids")
    attrs = {a["id"]: a for a in c["project_attributes"]}
    adopted = {d["control"] for d in c["framework"]["decisions"] if d["decision"] != "exclude"}
    for r in reqs.values():
        for f in ("title", "statement", "framework_refs", "domain", "owner", "source", "version", "evidence"):
            if not r.get(f): errs.append(f"{r['id']}: missing {f}")
        for f in ("addressed", "partly_addressed", "accepted_evidence", "verifier"):
            if not r.get("evidence", {}).get(f): errs.append(f"{r['id']}: evidence missing {f}")
        for ref in r.get("framework_refs", []):
            base = re.sub(r"\(.*\)", "", ref.split(":")[-1]).strip()
            if base not in adopted: errs.append(f"{r['id']}: {ref} is not adopted or tailored in framework/adoption.yaml")
    def check_when(owner, when):
        for k in all_conds(when):
            a = attrs.get(k["attribute"])
            if not a: errs.append(f"{owner}: unknown attribute {k['attribute']}"); continue
            for v in k["in"]:
                if v not in a["values"]: errs.append(f"{owner}: {v!r} is not an allowed value of {k['attribute']}")
    required = set()
    for r in c["applicability_rules"]:
        check_when(r["id"], r["when"])
        for q in r["require"]:
            required.add(q)
            if q not in reqs: errs.append(f"{r['id']}: requires unknown {q}")
    for r in c["classification_rules"]: check_when(r["id"], r["when"])
    if c["classification_rules"][-1]["when"] != "always": errs.append("classification rules need a default (when: always) last")
    cats = {t["category"] for t in c["targets"]["targets"]}
    for r in c["classification_rules"]:
        if r["category"] not in cats: errs.append(f"{r['id']}: no target for category {r['category']}")
    linked = set()
    for t in c["threat_library"]:
        for q in t["requirements"]:
            linked.add(q)
            if q not in reqs: errs.append(f"{t['id']}: links unknown {q}")
    for q in reqs:
        if q not in linked: errs.append(f"{q}: not linked to any threat")
        if q not in required: warns.append(f"{q}: no applicability rule requires it")
    for p in c["patterns"]:
        for q in p["meets_by_design"]:
            if q not in reqs: errs.append(f"{p['id']}: unknown {q}")
    th = sorted(c["risk_methodology"]["rating_thresholds"], key=lambda t: t["min"])
    if th[0]["min"] != 1 or th[-1]["max"] != 16 or any(b["min"] != a["max"] + 1 for a, b in zip(th, th[1:])):
        errs.append("risk thresholds must cover 1 to 16 with no gaps")
    return errs, warns

# ---------- risk ----------
def score(attrs, defs, name): return defs[name]["scores"][attrs[name]]
def rate(s, th): return next(t["rating"] for t in th if t["min"] <= s <= t["max"])
def half_up(x): return int(math.floor(x + 0.5))
def risk(c, a):
    defs = {d["id"]: d for d in c["project_attributes"]}
    impact = max(score(a, defs, "data_class"), score(a, defs, "criticality"))
    likelihood = math.ceil((score(a, defs, "exposure") + score(a, defs, "threat_context")) / 2)
    return impact, likelihood, impact * likelihood

# ---------- commands ----------
def cmd_validate():
    c = load_catalog(); errs, warns = validate(c)
    for w in warns: print("warning:", w)
    for e in errs: print("ERROR:", e)
    print(f"{len(c['requirements'])} requirements, {len(c['applicability_rules'])} rules, {len(c['threat_library'])} threats checked: "
          + ("FAILED" if errs else "passed"))
    return 1 if errs else 0

def cmd_build():
    c = load_catalog(); errs, _ = validate(c)
    if errs: print("Cannot build: validation failed. Run validate."); return 1
    out = ROOT / "dist" / f"catalog-{c['manifest']['version']}.json"
    out.write_text(json.dumps(c, indent=2, default=str)); print("built", out.relative_to(ROOT)); return 0

def cmd_assess():
    p = load("project/sample-project.yaml"); v = p["pinned_catalog_version"]
    c = json.loads((ROOT / "dist" / f"catalog-{v}.json").read_text())      # the assessor reads the bundle only
    a = p["attributes"]; reqs = {r["id"]: r for r in c["requirements"]}
    print(f"Project: {p['project']}   Catalog: {v} (pinned)\n")
    cat = next(r for r in c["classification_rules"] if matches(r["when"], a))
    print(f"Category: {cat['category']}  ({cat['id']} v{cat['version']}: {cat['reason']})")
    tm = [r for r in c["threat_methods"]["trigger_rules"] if matches(r["when"], a)]
    meth = next(r for r in c["threat_methods"]["selection_rules"] if matches(r["when"], a))["method"]
    print(f"Threat model: {'required' if tm else 'not required'} ({tm[0]['id']}), method {meth}\n")
    result = {}
    for r in c["applicability_rules"]:
        if matches(r["when"], a):
            for q in r["require"]: result.setdefault(q, []).append(f"{r['id']} v{r['version']}: {r['reason']}")
    threats = {t["id"]: t for t in c["threat_library"]}
    for tid in p["threat_model"]["threats_found"]:
        for q in threats[tid]["requirements"]: result.setdefault(q, []).append(f"{tid}: {threats[tid]['threat']}")
    impact, likelihood, inherent = risk(c, a); th = c["risk_methodology"]["rating_thresholds"]
    sf = c["risk_methodology"]["residual_risk"]["status_factors"]
    print(f"Risk: impact {impact} x likelihood {likelihood} = inherent {inherent} ({rate(inherent, th)})\n")
    print(f"{'Requirement':<17}{'Status':<18}{'Residual':<14}Why it applies")
    for q in sorted(result):
        st = p["evidence_status"].get(q, "not_yet_assessed")
        res = max(1, half_up(inherent * sf[st]))
        print(f"{q:<17}{st:<18}{str(res) + ' (' + rate(res, th) + ')':<14}{result[q][0]}")
        for extra in result[q][1:]: print(f"{'':<49}{extra}")
    t = next(x for x in c["targets"]["targets"] if x["category"] == cat["category"])
    print(f"\nTarget for {cat['category']}: {t['at_go_live']}")
    return 0

if __name__ == "__main__":
    cmds = {"validate": cmd_validate, "build": cmd_build, "assess": cmd_assess}
    sys.exit(cmds[sys.argv[1]]() if len(sys.argv) > 1 and sys.argv[1] in cmds else print(__doc__) or 2)
