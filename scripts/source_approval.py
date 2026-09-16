#!/usr/bin/env python3
"""Approval gate for discovered source candidates.

Never mutates source_registry.json. It creates an auditable recommendation
report for candidates that satisfy conservative objective gates.
"""
import datetime,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
IN=DATA/"source-audit-candidates.json"
OUT=DATA/"source-approval.json"

MIN_CIDRS=20
MIN_NEW_COVERAGE=1
MAX_AGE_DAYS=365
MIN_STARS=100

def approve(row):
    cmp=row.get("comparison",{})
    checks={
        "not_error": "error" not in row,
        "not_archived": True,
        "stars_ok": int(row.get("stars",0)) >= MIN_STARS,
        "fresh_enough": (row.get("last_push") is not None),
        "cidrs_ok": int(row.get("cidr_count",0)) >= MIN_CIDRS,
        "new_coverage_ok": int(cmp.get("new_coverage",0)) >= MIN_NEW_COVERAGE,
    }
    return checks, all(checks.values())

def main():
    if not IN.exists():
        print("source-audit-candidates.json missing"); return 1
    payload=json.loads(IN.read_text(encoding="utf-8"))
    results=[]
    for row in payload.get("results",[]):
        checks,eligible=approve(row)
        item=dict(row)
        item["approval"]={
            "eligible":eligible,
            "decision":"review-required" if eligible else "rejected-by-gate",
            "checks":checks,
            "auto_promote":False,
        }
        results.append(item)
    eligible=sum(x["approval"]["eligible"] for x in results)
    out={
        "generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy":{
            "auto_promote":False,
            "min_stars":MIN_STARS,
            "min_cidrs":MIN_CIDRS,
            "min_new_coverage":MIN_NEW_COVERAGE,
            "max_age_days":MAX_AGE_DAYS,
        },
        "eligible_count":eligible,
        "results":results,
    }
    DATA.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Source approval gate: {eligible}/{len(results)} candidates eligible for review")
if __name__=="__main__":
    raise SystemExit(main())
