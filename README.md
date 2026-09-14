# CDN + Cloud MagiTrickle

Готовые списки IPv4/IPv6 для MagiTrickle.

Репозиторий собирает адресные диапазоны крупных CDN, cloud и hosting-провайдеров и публикует их в формате CIDR. Списки обновляются автоматически через GitHub Actions, поэтому в MagiTrickle можно использовать постоянную Raw-ссылку.

## Провайдеры

AWS, Cloudflare, Hetzner, OVH, Akamai, DigitalOcean, Microsoft, Oracle, Alibaba, CDN77, Fastly, Melbicom, BuyVM / Frantech, Vultr, Contabo, Scaleway, Gcore и Backblaze.

Для AWS, Cloudflare, Fastly и Gcore используются публичные списки самих провайдеров. Для остальных сетей берутся анонсируемые BGP-префиксы из RIPEstat. Backblaze подключён отдельным статическим набором сетей.

## Основные списки

IPv4 всех провайдеров:

```text
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt
```

IPv6 всех провайдеров:

```text
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt
```

Отдельный провайдер:

```text
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/<provider>-v4.txt
```

Примеры:

```text
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v4.txt
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v4.txt
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v4.txt
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v4.txt
```

Для IPv6 используется тот же путь с `-v6.txt`.

## Источники

AWS

`https://ip-ranges.amazonaws.com/ip-ranges.json`

Cloudflare

`https://www.cloudflare.com/ips-v4/`

`https://www.cloudflare.com/ips-v6/`

Fastly

`https://api.fastly.com/public-ip-list`

Gcore

`https://api.gcore.com/cdn/public-ip-list`

Для остальных провайдеров используется RIPEstat announced-prefixes с `min_peers_seeing=5`.

## Обновление

Списки собираются два раза в сутки. Запуск можно также выполнить вручную через GitHub Actions.

При каждом обновлении скрипт получает данные от источников, приводит записи к CIDR, убирает дубликаты, объединяет сети и записывает отдельные списки провайдеров и общий список.

Внешний источник может временно не ответить. В таком случае выполняются повторные попытки. Если новый результат пустой, слишком маленький или явно аномальный, предыдущая рабочая версия списка сохраняется.

## Проверки перед публикацией

Перед отправкой изменений в `main` проверяется:

- корректность IPv4/IPv6 CIDR;
- наличие общего IPv4-списка;
- наличие IPv6-списка;
- корректная версия `manifest.json`;
- контрольные суммы SHA-256;
- отсутствие подмены рабочего списка пустым результатом.

## Структура

```text
CDN-Cloud-MagiTrickle/
├── config/
│   └── providers.json
├── scripts/
│   └── update_cdn_lists.py
├── data/
│   ├── *-v4.txt
│   ├── *-v6.txt
│   ├── all-cloud-v4.txt
│   ├── all-cloud-v6.txt
│   ├── manifest.json
│   ├── checksums.sha256
│   └── last-update.txt
└── .github/
    └── workflows/
        └── update.yml
```

`config/providers.json` содержит ASN провайдеров. Для Gcore используются AS199524 и AS202422. Backblaze работает без ASN, через статические CIDR.

## Генератор

Основной скрипт:

```text
scripts/update_cdn_lists.py
```

Он отвечает за загрузку исходных данных, проверку, нормализацию и агрегацию сетей, защиту предыдущей версии и подготовку итоговых файлов.

В генераторе используются повторные запросы с задержкой, таймауты, атомарная запись и ограничение на аномально большой объём prefix у одного провайдера.

## Формат

Каждая строка в списках — одна сеть в формате CIDR:

```text
1.2.3.0/24
2001:db8::/32
```

Файлы можно использовать напрямую в MagiTrickle и других инструментах, которые принимают IPv4/IPv6 prefix.

## Текущая версия

V8

Основная задача версии V8 — сделать обновления предсказуемыми. При проблемах с источниками рабочие списки не стираются, а результат проверяется до публикации.

## Примечание

Адресные пространства CDN и облачных платформ со временем меняются. Для постоянного использования рекомендуется подключать Raw-ссылку на нужный файл, а не сохранять список локально.

Отдельная лицензия в репозитории не задана.
