#!/usr/bin/env python3
"""Core CIDR normalization, deduplication and overlap engine."""
import ipaddress

def normalize(values):
    out=set()
    for value in values:
        try: out.add(str(ipaddress.ip_network(value, strict=False)))
        except (ValueError,TypeError): pass
    return sorted(out,key=lambda x:(ipaddress.ip_network(x).version,int(ipaddress.ip_network(x).network_address),ipaddress.ip_network(x).prefixlen))

def collapse(values):
    nets=[ipaddress.ip_network(x,strict=False) for x in normalize(values)]
    return [str(x) for x in ipaddress.collapse_addresses(nets)]

def stats(values):
    n=normalize(values)
    return {"input":len(values),"valid_unique":len(n),"collapsed":len(collapse(n)) if n else 0,"ipv4":sum(ipaddress.ip_network(x).version==4 for x in n),"ipv6":sum(ipaddress.ip_network(x).version==6 for x in n)}
