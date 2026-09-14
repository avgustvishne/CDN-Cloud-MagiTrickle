# CDN + Cloud MagiTrickle — V2

Автообновляемые отдельные подписки по CDN/Cloud/hosting-провайдерам.

## Источник

V2 получает актуальные BGP-announced prefixes через официальный RIPE NCC RIPEstat Data API endpoint **announced-prefixes**. RIPEstat документирует этот endpoint как источник всех объявленных префиксов для указанного ASN. Используется фильтр видимости `min_peers_seeing=5`, чтобы отсекать маловидимые локальные объявления.

AWS дополнительно публикует собственный официальный `ip-ranges.json`; при необходимости AWS можно перевести на этот источник отдельно.

## Провайдеры

AWS, Cloudflare, Hetzner, OVH, Akamai, DigitalOcean, Microsoft, Oracle, Alibaba, CDN77, Fastly, Melbicom, BuyVM/Frantech, Vultr, Contabo и Scaleway.

Список ASN находится в `config/providers.json`.

## Подписки MagiTrickle

IPv4:

- `aws-v4.txt`
- `cloudflare-v4.txt`
- `hetzner-v4.txt`
- `ovh-v4.txt`
- `akamai-v4.txt`
- `digitalocean-v4.txt`
- `microsoft-v4.txt`
- `oracle-v4.txt`
- `alibaba-v4.txt`
- `cdn77-v4.txt`
- `fastly-v4.txt`
- `melbicom-v4.txt`
- `buyvm-v4.txt`
- `vultr-v4.txt`
- `contabo-v4.txt`
- `scaleway-v4.txt`

Также создаются одноимённые `-v6.txt`.

Общие списки:

- `all-cloud-v4.txt`
- `all-cloud-v6.txt`

## Raw URL

Шаблон:

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v4.txt`

Например:

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v4.txt`

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v4.txt`

Общий:

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt`

## Автообновление

GitHub Actions запускает обновление каждые 12 часов и вручную через `workflow_dispatch`. Перед commit выполняется проверка CIDR.

