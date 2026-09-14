# CDN + Cloud MagiTrickle

Готовые списки IPv4/IPv6 в формате CIDR для MagiTrickle.

Репозиторий собирает адресные диапазоны крупных CDN, cloud и hosting-провайдеров и публикует их в виде обычных текстовых списков. Основное обновление сетей выполняется автоматически два раза в сутки.

## Провайдеры

- AWS
- Cloudflare
- Hetzner
- OVH
- Akamai
- DigitalOcean
- Microsoft
- Oracle
- Alibaba
- CDN77
- Fastly
- Melbicom
- BuyVM / Frantech
- Vultr
- Contabo
- Scaleway
- Gcore
- Backblaze

Для AWS, Cloudflare, Fastly и Gcore используются публичные источники самих провайдеров. Для остальных сетей используются анонсируемые BGP-префиксы через RIPEstat. Backblaze подключён отдельным статическим набором сетей.

## Основные списки

Общий IPv4:

```text
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt
```

Общий IPv6:

```text
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt
```

Отдельный провайдер:

```text
https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/<provider>-v4.txt
```

Файлы `tests-*.txt` содержат **доменные имена**, а `*-v4.txt` и `*-v6.txt` содержат **CIDR**.

Поэтому подключать тестовые файлы нужно только в поле/группу MagiTrickle, которая принимает доменные правила. Не следует добавлять их в IP/CIDR-подписку.

## Источники

AWS

```text
https://ip-ranges.amazonaws.com/ip-ranges.json
```

Cloudflare

```text
https://www.cloudflare.com/ips-v4/
https://www.cloudflare.com/ips-v6/
```

Fastly

```text
https://api.fastly.com/public-ip-list
```

Gcore

```text
https://api.gcore.com/cdn/public-ip-list
```

Остальные провайдеры

```text
https://stat.ripe.net/data/announced-prefixes/data.json
```

Параметр `min_peers_seeing` установлен в `5`.

## Проверка и защита

Генератор проверяет IPv4/IPv6 CIDR, удаляет некорректные записи и дубликаты, объединяет пересекающиеся сети и отбрасывает не-global адресное пространство.

Также используются:

- повторные попытки запросов;
- таймауты;
- контроль пустых ответов;
- ограничение максимального количества prefix;
- сравнение с предыдущей рабочей версией;
- сохранение предыдущего списка при подозрительном резком падении;
- фиксация ошибок источников в `manifest.json`;
- атомарная запись;
- SHA-256 контроль файлов.

## DPI-aware режим

Источник проверки — Hyperion TCP 16–20. Issue #490 описывает ограничение, при котором подозрительные TCP-соединения могут зависать после определённого количества переданных данных; при этом поведение зависит от сети/провайдера, поэтому V14 не помечает ASN глобально как «плохой». citeturn0view0

Результаты проверки хранятся отдельно от генерации BGP/CIDR. Это позволяет не смешивать факт конкретного теста с общим списком провайдера.

## Автоматическое обновление

Workflow:

```text
.github/workflows/update.yml
```

Основные CIDR-списки обновляются каждые 12 часов. Workflow можно запустить вручную через GitHub Actions.

Изменения в `data/` сами по себе не запускают новый цикл обновления.

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
│   ├── tests-quic-http3.txt
│   ├── tests-proxy-anonymity.txt
│   ├── tests-dns-resolver.txt
│   ├── tests-google-connectivity.txt
│   ├── tests-privacy-fingerprint.txt
│   ├── tests-web-rtc-ip.txt
│   ├── tests-all.txt
│   ├── manifest.json
│   ├── checksums.sha256
│   └── last-update.txt
└── .github/
    └── workflows/
        └── update.yml
```

## Формат

CIDR-файлы:

```text
1.2.3.0/24
2001:db8::/32
```

Тестовые файлы:

```text
www.google.com
browserleaks.com
cloudflare-dns.com
```

Каждая запись находится на отдельной строке.

## Текущая версия

Основной генератор — V15.

V15 добавляет второй уровень DPI-контроля: `config/dpi-status.json` хранит результат по провайдеру/ASN, а `config/dpi-cidr.json` — результат по конкретным CIDR. В `dpi-recommended-v4.txt` и `dpi-recommended-v6.txt` попадают только CIDR со статусом `safe`. `blocked` исключается, `unknown` остаётся за пределами рекомендуемого списка. Это позволяет не считать весь ASN плохим из-за одного проблемного диапазона.

V15 сохраняет дополнительные cloud/hosting-провайдеры и усиливает контроль обновлений IPv4/IPv6, дубликатов ASN, аномальных объёмов и целостности файлов.

## Примечание

Списки тестовых сервисов являются подборкой endpoints для диагностики. Они не являются механизмом блокировки рекламы, полноценной анонимизации или гарантией отсутствия утечек.

WebRTC, DNS, IPv6 и fingerprint необходимо проверять отдельно: один только маршрут через VPN не гарантирует, что браузер не раскроет дополнительные сведения о сетевом окружении. citeturn0search0turn0search7
