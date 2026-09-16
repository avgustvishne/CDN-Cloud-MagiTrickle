#!/usr/bin/env python3
"""Fast structural validation of generated CIDR and evidence artifacts."""
import ipaddress,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
def validate_cidrs():
    errors=[]
    for p in sorted(DATA.glob("*.txt")):
        if p.name.endswith(("-v4.txt","-v6.txt")):
            for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
                s=line.strip()
                if not s: continue
                try: ipaddress.ip_network(s,strict=False)
                except ValueError: errors.append(f"{p.name}:{n}:{s}")
    return errors
def main():
    errors=validate_cidrs()
    for name in ("consensus.json","source-audit.json","evidence.json"):
        p=DATA/name
        if p.exists():
            try: json.loads(p.read_text(encoding="utf-8"))
            except Exception as e: errors.append(f"{name}: invalid JSON: {e}")
    if errors:
        print("\n".join(errors[:50])); return 1
    print("Generated output validation: OK"); return 0
if __name__=="__main__": raise SystemExit(main())
