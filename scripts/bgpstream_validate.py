#!/usr/bin/env python3
"""Independent live-BGP validation using CAIDA BGPStream."""
import argparse, datetime as dt, json, pathlib, re
import pybgpstream

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_asns(limit):
    cfg=json.loads((ROOT/"config/providers.json").read_text(encoding="utf-8"))
    out=[]; seen=set()
    for provider, asns in cfg.get("providers",{}).items():
        for asn in asns:
            asn=str(asn)
            if asn not in seen:
                out.append((provider,asn)); seen.add(asn)
            if len(out)>=limit: return out
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--hours",type=float,default=2.0)
    ap.add_argument("--limit",type=int,default=16)
    args=ap.parse_args()
    pairs=load_asns(args.limit)
    asn_re="|".join(re.escape(a) for _,a in pairs)
    end=dt.datetime.now(dt.timezone.utc)
    start=end-dt.timedelta(hours=args.hours)
    stream=pybgpstream.BGPStream(
        from_time=start.strftime("%Y-%m-%d %H:%M:%S"),
        until_time=end.strftime("%Y-%m-%d %H:%M:%S"),
        projects=["routeviews","ris"],
        record_type="ribs",
        filter=f"aspath _({asn_re})$",
    )
    found={a:set() for _,a in pairs}
    peers={a:set() for _,a in pairs}
    for elem in stream:
        fields=elem.fields
        prefix=fields.get("prefix")
        path=fields.get("as-path","")
        if not prefix or not path: continue
        origin=path.split()[-1]
        if origin in found:
            found[origin].add(prefix)
            peer=getattr(elem,"peer_asn",None)
            if peer is not None: peers[origin].add(str(peer))
    rows=[{"provider":p,"asn":a,"prefixes":len(found[a]),"peers":len(peers[a]),"observed":bool(found[a])} for p,a in pairs]
    out={"engine":"v44","source":"CAIDA BGPStream","projects":["routeviews","ris"],"window_hours":args.hours,"generated_at":end.isoformat(),"sample_size":len(rows),"results":rows,"healthy_asns":sum(r["observed"] for r in rows)}
    path=ROOT/"data/bgpstream-health.json"
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
