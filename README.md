# CDN + Cloud MagiTrickle

Готовые списки IPv4/IPv6 в формате CIDR для MagiTrickle.

Репозиторий собирает адресные диапазоны крупных CDN, cloud и hosting-провайдеров и публикует их в виде обычных текстовых списков. Обновление выполняется автоматически два раза в сутки.

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

## Как собираются списки

Генератор получает исходные prefix, проверяет их как IPv4/IPv6 сети, удаляет некорректные записи и дубликаты, после чего объединяет пересекающиеся диапазоны.

В итоговые файлы попадают только глобальные адресные пространства. Слишком широкие prefix также отбрасываются: для IPv4 минимальная длина префикса — `/8`, для IPv6 — `/16`. Это дополнительная защита от случайного попадания слишком большого диапазона в подписку.

Для каждого провайдера сохраняется отдельный список. После этого строятся два общих файла — IPv4 и IPv6.

## Защита от сбоев источников

Ошибки внешнего сервиса не должны превращать рабочую подписку в пустой файл.

Используются:

- повторные попытки запроса;
- таймауты;
- контроль пустого ответа;
- ограничение на максимальное число prefix одного провайдера;
- сравнение с предыдущей рабочей версией;
- сохранение предыдущего списка при подозрительном резком падении количества сетей;
- отдельная фиксация ошибок источников в `manifest.json`;
- атомарная запись файлов.

Для провайдеров с несколькими ASN ошибка одного запроса не стирает результаты остальных ASN.

## Проверка перед публикацией

GitHub Actions проверяет:

- корректность каждого IPv4/IPv6 CIDR;
- наличие только глобальных сетей;
- отсутствие слишком широких prefix;
- наличие общего IPv4-списка;
- наличие IPv6-файла;
- версию `manifest.json`;
- контрольные SHA-256 для опубликованных списков.

Только после успешной проверки сгенерированные файлы отправляются в `main`.

## Автоматическое обновление

Workflow находится здесь:

```text
.github/workflows/update.yml
```

Запуск выполняется каждые 12 часов. Дополнительно его можно запустить вручную через GitHub Actions.

Изменения в `data/` сами по себе не запускают новый цикл обновления, поэтому публикация результатов не создаёт бесконечную цепочку запусков.

## Файлы

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

`config/providers.json` содержит список ASN. Для Gcore используются AS199524 и AS202422. Для Backblaze ASN не используются.

## Формат списков

Каждая строка — одна сеть в формате CIDR:

```text
1.2.3.0/24
2001:db8::/32
```

Списки подходят для MagiTrickle и других инструментов, которые принимают IPv4/IPv6 prefix.

## Текущая версия

V9

В V9 основной упор сделан на защиту от ошибочных обновлений: глобальные сети, отсечение слишком широких prefix, контроль аномальных изменений, обработка частичных ошибок источников, повторные запросы и проверка целостности перед публикацией.

## Примечание

Адресные пространства CDN и облачных платформ меняются со временем. Для постоянного использования удобнее подключать Raw-ссылку на нужный файл, а не копировать список вручную.

Лицензия в репозитории отдельно не задана.
