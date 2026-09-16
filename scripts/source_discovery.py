#!/usr/bin/env python3
"""Discover candidate IP/CIDR data repositories for human review.

Discovery is advisory only: candidates are never promoted to production
automatically. GitHub search is performed by CI with GITHUB_TOKEN.
"""
import datetime,json,os,pathlib,urllib.parse,urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; OUT=DATA/"source-candidates.json"
QUERIES=[
    "cloud ip ranges",
    "cdn ip ranges",
    "asn ip prefixes",
    "bgp prefixes ip",
    "ipv4 ipv6 cidr cloud",
]
MIN_STARS=100
MAX_RESULTS=30
MIN_RECENT_DAYS=180

def github_search(query):
    token=os.environ.get("GITHUB_TOKEN","")
    url="https://api.github.com/search/repositories?"+urllib.parse.urlencode({"q":query,"sort":"stars","order":"desc","per_page":MAX_RESULTS})
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"CDN-Cloud-MagiTrickle","Authorization":f"Bearer {token}"} if token else {"Accept":"application/vnd.github+json","User-Agent":"CDN-Cloud-MagiTrickle"})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)

def candidate_score(item):
    """Operational discovery priority; not a data-quality rating."""
    import math
    now=datetime.datetime.now(datetime.timezone.utc)
    pushed=item.get("last_push")
    try:
        age=(now-datetime.datetime.fromisoformat(pushed.replace("Z","+00:00"))).days if pushed else 9999
    except Exception:
        age=9999
    freshness=max(0.0,1.0-min(age,365)/365.0)
    popularity=min(1.0,math.log10(max(1,int(item.get("stars",0))+1))/5.0)
    return round(0.65*freshness+0.35*popularity,4), age

def main():
    candidates={}
    errors=[]
    for query in QUERIES:
        try:
            for item in github_search(query).get("items",[]):
                if item.get("archived") or item.get("fork"): continue
                stars=int(item.get("stargazers_count",0))
                if stars<MIN_STARS: continue
                full=item["full_name"]
                score, age_days = candidate_score(item)
                candidates[full]={
                    "repository":full,
                    "url":item["html_url"],
                    "stars":stars,
                    "forks":int(item.get("forks_count",0)),
                    "last_push":item.get("pushed_at"),
                    "updated_at":item.get("updated_at"),
                    "description":item.get("description") or "",
                    "language":item.get("language"),
                    "topics":item.get("topics",[]),
                    "status":"candidate",
                    "last_push_age_days":age_days,
                    "discovery_priority":score,
                    "priority_basis":"freshness + GitHub popularity; not data-quality validation",
                }
        except Exception as e: errors.append({"query":query,"error":str(e)[:300]})
    rows=sorted(candidates.values(),key=lambda x:(x["discovery_priority"],x["stars"]),reverse=True)
    payload={
        "generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy":{"min_stars":MIN_STARS,"auto_promote":False,"archived_excluded":True,"forks_excluded":True,"min_recent_days":MIN_RECENT_DAYS},
        "queries":QUERIES,"candidates":rows[:100],"errors":errors,
    }
    DATA.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Source discovery: {len(rows)} candidates, {len(errors)} query errors")
if __name__=="__main__": main()
