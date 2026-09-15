# CDN + Cloud MagiTrickle

**Автоматические IPv4/IPv6 CIDR- и ASN-подписки CDN и облачных провайдеров для MagiTrickle.**

[English version](README.en.md)

Готовые **IPv4/IPv6 CIDR-подписки** для MagiTrickle.

## Проверки качества

- `BEST / GOOD / SLOW / BACKUP / BLOCKED / DEAD` — автоматическая DPI-оценка точек.


## Профили

Выбирай профиль в зависимости от нужного покрытия и нагрузки.

| Профиль | IPv4 | IPv6 | Назначение |
|---|---|---|---|
| **FULL** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v6.txt) | Максимальное покрытие всех провайдеров |
| **BALANCED** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v6.txt) | Оптимальный баланс покрытия и нагрузки |
| **MINIMAL** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v6.txt) | Минимальный набор основных сетей |

## Все сети

**IPv4**  
[Подписка IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt)

**IPv6**  
[Подписка IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt)

## Специализированные наборы

| Набор | IPv4 | IPv6 |
|---|---|---|
| **CDN** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v6.txt) |
| **Cloud** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v6.txt) |
| **Video** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v6.txt) |
| **VPN** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v6.txt) |


## Чем отличаются провайдерские и ASN-подписки

- **Отдельные провайдеры** — готовые списки IP/CIDR, собранные генератором из доступных источников. Обычно дают более полное и актуальное покрытие конкретного провайдера.
- **ASN-подписки** — IP/CIDR, относящиеся к указанному автономному номеру (ASN). Удобны для точечного выбора сети или конкретной инфраструктуры.

**Коротко:** провайдерская подписка — **всё покрытие провайдера**, ASN — **конкретная сеть провайдера**.


## Отдельные провайдеры

Для каждого провайдера доступны отдельные IPv4 и IPv6 подписки.

| Провайдер | IPv4 | IPv6 |
|---|---|---|
| **AWS** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v6.txt) |
| **Cloudflare** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v6.txt) |
| **Hetzner** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/hetzner-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/hetzner-v6.txt) |
| **OVH** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/ovh-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/ovh-v6.txt) |
| **Akamai** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/akamai-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/akamai-v6.txt) |
| **DigitalOcean** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/digitalocean-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/digitalocean-v6.txt) |
| **Microsoft** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/microsoft-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/microsoft-v6.txt) |
| **Oracle** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/oracle-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/oracle-v6.txt) |
| **Alibaba** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/alibaba-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/alibaba-v6.txt) |
| **CDN77** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cdn77-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cdn77-v6.txt) |
| **Fastly** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v6.txt) |
| **Melbicom** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/melbicom-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/melbicom-v6.txt) |
| **BuyVM / Frantech** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/buyvm-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/buyvm-v6.txt) |
| **Vultr** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v6.txt) |
| **Contabo** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/contabo-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/contabo-v6.txt) |
| **Scaleway** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/scaleway-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/scaleway-v6.txt) |
| **Gcore** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v6.txt) |
| **Backblaze** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/backblaze-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/backblaze-v6.txt) |

## ASN-подписки

| Провайдер | ASN | IPv4 | IPv6 |
|---|---|---|---|
| **AWS** | AS16509 | [IPv4](https://asn.web2core.workers.dev/AS16509?v4) | [IPv6](https://asn.web2core.workers.dev/AS16509?v6) |
| **AWS** | AS14618 | [IPv4](https://asn.web2core.workers.dev/AS14618?v4) | [IPv6](https://asn.web2core.workers.dev/AS14618?v6) |
| **Cloudflare** | AS13335 | [IPv4](https://asn.web2core.workers.dev/AS13335?v4) | [IPv6](https://asn.web2core.workers.dev/AS13335?v6) |
| **Hetzner** | AS24940 | [IPv4](https://asn.web2core.workers.dev/AS24940?v4) | [IPv6](https://asn.web2core.workers.dev/AS24940?v6) |
| **OVHcloud** | AS16276 | [IPv4](https://asn.web2core.workers.dev/AS16276?v4) | [IPv6](https://asn.web2core.workers.dev/AS16276?v6) |
| **Akamai** | AS20940 | [IPv4](https://asn.web2core.workers.dev/AS20940?v4) | [IPv6](https://asn.web2core.workers.dev/AS20940?v6) |
| **Akamai** | AS16625 | [IPv4](https://asn.web2core.workers.dev/AS16625?v4) | [IPv6](https://asn.web2core.workers.dev/AS16625?v6) |
| **Akamai** | AS63949 | [IPv4](https://asn.web2core.workers.dev/AS63949?v4) | [IPv6](https://asn.web2core.workers.dev/AS63949?v6) |
| **DigitalOcean** | AS14061 | [IPv4](https://asn.web2core.workers.dev/AS14061?v4) | [IPv6](https://asn.web2core.workers.dev/AS14061?v6) |
| **Microsoft** | AS8075 | [IPv4](https://asn.web2core.workers.dev/AS8075?v4) | [IPv6](https://asn.web2core.workers.dev/AS8075?v6) |
| **Oracle Cloud** | AS31898 | [IPv4](https://asn.web2core.workers.dev/AS31898?v4) | [IPv6](https://asn.web2core.workers.dev/AS31898?v6) |
| **Alibaba Cloud** | AS45102 | [IPv4](https://asn.web2core.workers.dev/AS45102?v4) | [IPv6](https://asn.web2core.workers.dev/AS45102?v6) |
| **Alibaba Cloud** | AS37963 | [IPv4](https://asn.web2core.workers.dev/AS37963?v4) | [IPv6](https://asn.web2core.workers.dev/AS37963?v6) |
| **CDN77** | AS60068 | [IPv4](https://asn.web2core.workers.dev/AS60068?v4) | [IPv6](https://asn.web2core.workers.dev/AS60068?v6) |
| **Fastly** | AS54113 | [IPv4](https://asn.web2core.workers.dev/AS54113?v4) | [IPv6](https://asn.web2core.workers.dev/AS54113?v6) |
| **BuyVM / FranTech** | AS53667 | [IPv4](https://asn.web2core.workers.dev/AS53667?v4) | [IPv6](https://asn.web2core.workers.dev/AS53667?v6) |
| **Vultr** | AS20473 | [IPv4](https://asn.web2core.workers.dev/AS20473?v4) | [IPv6](https://asn.web2core.workers.dev/AS20473?v6) |
| **Contabo** | AS51167 | [IPv4](https://asn.web2core.workers.dev/AS51167?v4) | [IPv6](https://asn.web2core.workers.dev/AS51167?v6) |
| **Scaleway** | AS12876 | [IPv4](https://asn.web2core.workers.dev/AS12876?v4) | [IPv6](https://asn.web2core.workers.dev/AS12876?v6) |
| **Gcore** | AS199524 | [IPv4](https://asn.web2core.workers.dev/AS199524?v4) | [IPv6](https://asn.web2core.workers.dev/AS199524?v6) |
| **Backblaze** | AS19503 | [IPv4](https://asn.web2core.workers.dev/AS19503?v4) | [IPv6](https://asn.web2core.workers.dev/AS19503?v6) |
