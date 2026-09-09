# CDN + Cloud для MagiTrickle

Готовый репозиторий для автоматической подписки с IPv4/IPv6 CIDR основных CDN и hosting/cloud сетей.

## Что входит

Источник `123jjck/cdn-ip-ranges` и его список `cdn-only`, который включает CDN и hosting-провайдеров без Discord Voice, Telegram и Meta. В актуальном списке есть, среди прочего: Akamai, AWS, Bunny, BuyVM, CDN77, Cloudflare, Contabo, DigitalOcean, Fastly, Gcore, Hetzner, MelBiCom, Oracle, OVH, Scaleway, Vercel и др.

Скрипт:
- скачивает актуальные IPv4/IPv6 диапазоны;
- удаляет мусор и дубликаты;
- агрегирует соседние CIDR через `ipaddress.collapse_addresses()`;
- сохраняет готовые plain-text списки;
- GitHub Actions обновляет их каждые 12 часов.

## Файлы

- `data/cdn-cloud-v4.txt` — IPv4, по одному CIDR на строку.
- `data/cdn-cloud-v6.txt` — IPv6, по одному CIDR на строку.
- `data/last-update.txt` — статистика последнего обновления.

## Как подключить к MagiTrickle

После создания репозитория `USERNAME/REPO` используй:

IPv4:
`https://raw.githubusercontent.com/USERNAME/REPO/main/data/cdn-cloud-v4.txt`

IPv6:
`https://raw.githubusercontent.com/USERNAME/REPO/main/data/cdn-cloud-v6.txt`

Для MagiTrickle лучше использовать IPv4-список как отдельную группу `CDN + CLOUD ALL` с интерфейсом `Mihomo`.

## Установка

1. Создай новый публичный GitHub repository.
2. Загрузи содержимое этого проекта в корень репозитория.
3. Открой Actions и запусти `Update CDN + Cloud lists` вручную один раз.
4. После успешного запуска используй raw-ссылку из раздела выше.

GitHub Actions затем будет обновлять список каждые 12 часов.
