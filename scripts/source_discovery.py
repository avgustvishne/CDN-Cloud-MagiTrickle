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

def github_search(query):
    token=os.environ.get("GITHUB_TOKEN","")
    url="https://api.github.com/search/repositories?"+urllib.parse.urlencode({"q":query,"sort":"stars","order":"desc","per_page":MAX_RESULTS})
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"CDN-Cloud-MagiTrickle","Authorization":f"Bearer {token}"} if token else {"Accept":"application/vnd.github+json","User-Agent":"CDN-Cloud-MagiTrickle"})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)

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
                }
        except Exception as e: errors.append({"query":query,"error":str(e)[:300]})
    rows=sorted(candidates.values(),key=lambda x:(x["stars"],x["last_push"] or ""),reverse=True)
    payload={
        "generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy":{"min_stars":MIN_STARS,"auto_promote":False,"archived_excluded":True,"forks_excluded":True},
        "queries":QUERIES,"candidates":rows[:100],"errors":errors,
    }
    DATA.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Source discovery: {len(rows)} candidates, {len(errors)} query errors")
if __name__=="__main__": main()
