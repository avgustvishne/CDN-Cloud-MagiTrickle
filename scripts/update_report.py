#!/usr/bin/env python3
"""Generate UPDATE_REPORT.md from the real v43 generated datasets."""
import argparse,csv,datetime,ipaddress,json,pathlib
def read_nets(path):
    try:return [ipaddress.ip_network(x.strip(),strict=False) for x in pathlib.Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
    except Exception:return []
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='UPDATE_REPORT.md');a=ap.parse_args()
    root=pathlib.Path(__file__).resolve().parents[1];data=root/'data';now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    rows=[]
    for p in sorted((data/'presets').glob('*.txt')):
        ns=read_nets(p);rows.append((p.stem,len(ns),sum(n.version==4 for n in ns),sum(n.version==6 for n in ns)))
    providers=[];audit=data/'audit.csv'
    if audit.exists():
        with audit.open(encoding='utf-8') as f: providers=list(csv.DictReader(f))
    lines=['# CDN-Cloud-MagiTrickle — Update Report','',f'Обновлено: {now}','','## Подписки','','| Подписка | CIDR | IPv4 | IPv6 |','|---|---:|---:|---:|']
    for n,c,v4,v6 in rows: lines.append(f'| {n} | {c:,} | {v4:,} | {v6:,} |'.replace(',',' '))
    lines += ['','## Провайдеры','','| Провайдер | IPv4 | IPv6 | Статус |','|---|---:|---:|---|']
    for r in providers: lines.append(f"| {r.get('Provider','')} | {r.get('IPv4','0')} | {r.get('IPv6','0')} | {r.get('Status','')} |")
    manifest={}
    try:manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    except Exception:pass
    lines += ['','## Проверки','',f"- Engine: {manifest.get('engine','unknown')}",f"- Global-only: {manifest.get('global_only','unknown')}",f"- Лимит на провайдера: {manifest.get('max_provider_prefixes')} (искусственного лимита нет)",f"- Общий IPv4: {manifest.get('aggregate',{}).get('ipv4',0)} CIDR",f"- Общий IPv6: {manifest.get('aggregate',{}).get('ipv6',0)} CIDR"]
    (root/a.output).write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__':main()