# CDN + Cloud MagiTrickle — V5

Автообновляемые подписки для MagiTrickle по основным CDN, cloud и hosting-провайдерам.

## Что делает V5

V5 автоматически собирает и публикует IPv4/IPv6 prefixes провайдеров, удаляет дубликаты, агрегирует CIDR и проверяет результат перед публикацией.

Основные особенности:

- 🔄 автоматическое обновление каждые 12 часов;
- ▶️ ручной запуск через GitHub Actions;
- 🌐 отдельные IPv4 и IPv6 подписки;
- 📦 общий агрегированный список всех провайдеров;
- 🧹 удаление дублей и CIDR aggregation;
- 🔁 3 попытки получения данных при временных ошибках;
- 🛡️ safe fallback — если новый результат подозрительно мал, предыдущий рабочий список сохраняется;
- 💾 атомарная запись файлов;
- 🔎 автоматическая проверка CIDR перед публикацией;
- 📊 `data/manifest.json` с датой обновления, количеством префиксов, источником и статусом;
- 🚫 пустой или некорректный общий список не публикуется.

## Источники

Для AWS и Cloudflare используются официальные источники, когда они доступны:

- AWS — официальный `ip-ranges.amazonaws.com/ip-ranges.json`;
- Cloudflare — официальные IPv4/IPv6 списки;
- остальные провайдеры — RIPEstat Announced Prefixes API как fallback/основной источник.

Для RIPEstat используется `min_peers_seeing=5`, чтобы отбрасывать префиксы с очень низкой видимостью.

## Провайдеры

- AWS — AS16509, AS14618
- Cloudflare — AS13335, AS14789, AS132892, AS133877, AS139242, AS202623, AS203898, AS209242, AS394536, AS395747, AS400095
- Hetzner — AS24940, AS213230, AS212317, AS215859
- OVH — AS16276, AS35540, AS199949
- Akamai — AS16625, AS20940, AS12222, AS18680, AS18717, AS22207, AS23903, AS32787, AS35994, AS36183, AS63949
- DigitalOcean — AS14061, AS133165, AS394362, AS393406, AS135340, AS201229, AS202018, AS202109
- Microsoft — AS8075, AS12076, AS54489, AS3598, AS6584, AS8068
- Oracle — AS31898, AS23871, AS39648
- Alibaba — AS37963, AS45102, AS24429, AS45090
- CDN77 — AS60068
- Fastly — AS54113
- Melbicom — AS56630, AS8849
- BuyVM / Frantech — AS53667
- Vultr — AS20473
- Contabo — AS51167
- Scaleway — AS12876

Полный источник ASN: `config/providers.json`.

## Подписки MagiTrickle

### IPv4

Для каждого провайдера создаётся отдельный файл:

`aws-v4.txt`  
`cloudflare-v4.txt`  
`hetzner-v4.txt`  
`ovh-v4.txt`  
`akamai-v4.txt`  
`digitalocean-v4.txt`  
`microsoft-v4.txt`  
`oracle-v4.txt`  
`alibaba-v4.txt`  
`cdn77-v4.txt`  
`fastly-v4.txt`  
`melbicom-v4.txt`  
`buyvm-v4.txt`  
`vultr-v4.txt`  
`contabo-v4.txt`  
`scaleway-v4.txt`

### IPv6

Для провайдеров создаются соответствующие:

`<provider>-v6.txt`

### Общие подписки

IPv4:

`all-cloud-v4.txt`

IPv6:

`all-cloud-v6.txt`

## Raw URL

Шаблон:

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/<provider>-v4.txt`

Примеры:

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v4.txt`

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v4.txt`

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v4.txt`

Общая IPv4 подписка:

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt`

Общая IPv6 подписка:

`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt`

## GitHub Actions

Workflow:

`.github/workflows/update.yml`

Запускается:

- автоматически каждые 12 часов;
- вручную через **Actions → Update MagiTrickle V5 subscriptions → Run workflow**;
- автоматически при изменении конфигурации провайдеров или скрипта обновления.

Перед публикацией выполняется validation:

1. проверяется наличие общего IPv4 списка;
2. проверяется синтаксис всех CIDR;
3. проверяется версия `manifest.json`;
4. только после успешной проверки изменения коммитятся в репозиторий.

## Структура проекта

```
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
│   └── last-update.txt
└── .github/
    └── workflows/
        └── update.yml
```

## Статус

Текущая версия генератора: **V5**.

Данные подписок формируются автоматически и предназначены для прямого подключения в MagiTrickle через Raw GitHub URL.
