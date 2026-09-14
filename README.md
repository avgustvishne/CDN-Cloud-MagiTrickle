# CDN + Cloud MagiTrickle — V6

Автообновляемые IPv4/IPv6-подписки для MagiTrickle по основным CDN, cloud и hosting-провайдерам.

## V6

V6 расширяет V5 официальными источниками для AWS, Cloudflare, Fastly, Gcore и Backblaze, сохраняя RIPEstat fallback для остальных провайдеров.

- AWS: официальный `ip-ranges.json`.
- Cloudflare: официальные `ips-v4` и `ips-v6`.
- Fastly: официальный `https://api.fastly.com/public-ip-list`.
- Gcore: официальный `https://api.gcore.com/cdn/public-ip-list`.
- Backblaze: опубликованные компанией сервисные CIDR.
- Остальные: RIPEstat announced-prefixes с `min_peers_seeing=5`.

Дополнительно:
- 3 попытки загрузки источника с backoff;
- safe keep-old при аномально маленьком результате;
- атомарная запись файлов;
- удаление дублей и агрегация CIDR;
- проверка всех CIDR перед commit;
- `manifest.json` со статусом и источником каждого провайдера;
- `checksums.sha256` для контроля целостности опубликованных списков;
- общий `all-cloud-v4.txt` и `all-cloud-v6.txt`;
- отдельные файлы каждого провайдера;
- GitHub Actions каждые 12 часов и ручной запуск.

## Провайдеры

AWS, Cloudflare, Hetzner, OVH, Akamai, DigitalOcean, Microsoft, Oracle, Alibaba, CDN77, Fastly, Melbicom, BuyVM/Frantech, Vultr, Contabo, Scaleway, Gcore и Backblaze.

ASN перечислены в `config/providers.json`. Для Gcore используются AS199524 и AS202422. Backblaze использует официальный опубликованный список CIDR и не требует ASN.

## Raw URL

Шаблон:
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/<provider>-v4.txt`

Общий IPv4:
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt`

Общий IPv6:
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt`

AWS IPv4:
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v4.txt`

Cloudflare IPv4:
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v4.txt`

Fastly IPv4:
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v4.txt`

Gcore IPv4:
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v4.txt`

## Структура

```text
CDN-Cloud-MagiTrickle/
├── config/
│   └── providers.json
├── scripts/
│   └── update_cdn_lists.py
├── data/
│   ├── <provider>-v4.txt
│   ├── <provider>-v6.txt
│   ├── all-cloud-v4.txt
│   ├── all-cloud-v6.txt
│   ├── manifest.json
│   ├── checksums.sha256
│   └── last-update.txt
└── .github/
    └── workflows/
        └── update.yml
```

## GitHub Actions

Workflow: `.github/workflows/update.yml`

Автоматический запуск — каждые 12 часов. Также доступен `workflow_dispatch`.

Перед публикацией выполняется проверка наличия агрегированного IPv4, корректности CIDR и версии manifest. Если официальный источник не отвечает, используется fallback, а при аномально малом результате сохраняется предыдущий рабочий список.

## Статус

**V6** — текущая версия генератора подписок.
