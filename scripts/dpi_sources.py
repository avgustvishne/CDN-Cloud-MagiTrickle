#!/usr/bin/env python3
"""Registry of DPI projects used as references/optional probe engines."""
import json,pathlib,datetime
SOURCES=[
 {"id":"dpi-detector","repo":"Runnin4ik/dpi-detector","role":"detection","enabled":True},
 {"id":"zapret","repo":"bol-van/zapret","role":"strategy-reference","enabled":True},
 {"id":"zapret2","repo":"bol-van/zapret","role":"strategy-reference","enabled":True},
 {"id":"dpi-checker","repo":"LoonyMan/DPI-Checker","role":"compatibility-reference","enabled":True},
 {"id":"goodbyedpi","repo":"ValdikSS/GoodbyeDPI","role":"strategy-reference","enabled":True},
 {"id":"spoofdpi","repo":"xvzc/SpoofDPI","role":"strategy-reference","enabled":True},
 {"id":"byedpi","repo":"hufrea/byedpi","role":"strategy-reference","enabled":True},
 {"id":"zapret2-openwrt","repo":"rikkichy/zapret2-openwrt","role":"observed-strategy-reference","enabled":True},
]
def main():
 out=pathlib.Path("data/dpi/sources.json");out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({"schema_version":1,"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"sources":SOURCES},indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
