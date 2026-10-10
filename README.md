<div align="center">

<img src="docs/assets/hero.svg" alt="CDN-Cloud-MagiTrickle" width="100%">

# CDN-Cloud-MagiTrickle

**Готовые IPv4/IPv6 CIDR-подписки для [MagiTrickle](https://github.com/MagiTrickle/MagiTrickle) — CDN, облака, видео, VPN, Telegram, Twitter/X**

[![Update MagiTrickle subscriptions](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle/actions/workflows/update.yml/badge.svg)](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle/actions/workflows/update.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Поддержать проект](https://img.shields.io/badge/%E2%9D%A4-Поддержать%20проект-e25555)](https://tips.tips/000484125)

[📊 Статус](STATUS.md) · [📝 Изменения](CHANGELOG.md) · [🇬🇧 English](docs/README.en.md) · [📚 Документация](docs/README.md) · [🤝 Вклад в проект](CONTRIBUTING.md)

</div>

---

## Что это

Репозиторий дважды в сутки собирает диапазоны адресов CDN, облачных провайдеров и отдельных сервисов, сверяет их между собой и публикует готовые `.txt`-подписки, которые можно напрямую подключить в MagiTrickle.

## Как использовать

1. Выбери набор в таблице ниже.
2. Открой ссылку IPv4 или IPv6 — она ведёт прямо на файл со списком адресов.
3. Добавь эту ссылку в MagiTrickle как источник подписки (URL, не файл).

## Готовые наборы

| Нужно | Набор | IPv4 | IPv6 |
|---|---|:---:|:---:|
| Максимальное покрытие | **FULL** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v6.txt) |
| Широкое покрытие без гиперскейл-пулов | **BALANCED** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v6.txt) |
| CDN + компактный периферийный набор | **PERFORMANCE** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/performance-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/performance-v6.txt) |
| Только базовый набор CDN | **MINIMAL** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v6.txt) |
| Только CDN | **CDN** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v6.txt) |
| Облако/VPS | **CLOUD** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v6.txt) |
| Видео/CDN | **VIDEO** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v6.txt) |
| VPN/VPS | **VPN** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v6.txt) |
| Все собранные ASN | **ASN ALL** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v6.txt) |
| То же, что FULL, но обновляется раз в неделю | **STABLE** | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/stable-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/stable-v6.txt) |

**FULL** включает все провайдеры. **ALL-CLOUD** ([IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt)/[IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt)) — только AWS, Cloudflare, Microsoft, Oracle, Alibaba и DigitalOcean, отдельно от FULL.

## Отдельные провайдеры

Если нужен не готовый набор, а конкретный провайдер:

<!-- PROVIDER-HEALTH:START -->

| Провайдер | IPv4 | IPv6 | Состояние |
|---|:---:|:---:|---|
| Akamai | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/akamai-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/akamai-v6.txt) | 🟢 OK · обновлено |
| Alibaba Cloud | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/alibaba-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/alibaba-v6.txt) | 🟢 OK · обновлено |
| AWS | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v6.txt) | 🟢 OK · обновлено |
| Backblaze | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/backblaze-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/backblaze-v6.txt) | 🟢 OK · без изменений |
| BuyVM | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/buyvm-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/buyvm-v6.txt) | 🟢 OK · без изменений |
| CDN77 | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cdn77-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cdn77-v6.txt) | 🟢 OK · без изменений |
| Cloudflare | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v6.txt) | 🟢 OK · обновлено |
| Contabo | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/contabo-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/contabo-v6.txt) | 🟢 OK · без изменений |
| DigitalOcean | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/digitalocean-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/digitalocean-v6.txt) | 🟢 OK · без изменений |
| Fastly | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v6.txt) | 🟢 OK · без изменений |
| Gcore | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v6.txt) | 🟢 OK · обновлено |
| Hetzner | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/hetzner-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/hetzner-v6.txt) | 🟢 OK · обновлено |
| Melbicom | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/melbicom-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/melbicom-v6.txt) | 🟢 OK · без изменений |
| Microsoft Azure | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/microsoft-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/microsoft-v6.txt) | 🟢 OK · обновлено |
| Oracle Cloud | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/oracle-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/oracle-v6.txt) | 🛡️ старая версия |
| OVH | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/ovh-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/ovh-v6.txt) | 🟢 OK · обновлено |
| Scaleway | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/scaleway-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/scaleway-v6.txt) | 🟢 OK · без изменений |
| Telegram | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/telegram-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/telegram-v6.txt) | 🟢 OK · без изменений |
| Twitter/X | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/twitter-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/twitter-v6.txt) | 🟢 OK · обновлено |
| Vultr | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v4.txt) | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v6.txt) | 🟢 OK · обновлено |

> 🟢 OK = опубликовано нормально · 🟡 PARTIAL/FILTERED = опубликовано с предупреждением · 🛡️ старая версия = сработала защита от плохого обновления.

> Последняя проверка: 2026-10-10T06:25:00Z · [машиночитаемый отчёт](data/provider-health.json)
<!-- PROVIDER-HEALTH:END -->

<!-- AUTO-STATS:START -->
## 📊 Актуальная статистика

| Набор | IPv4 | IPv6 |
|---|---:|---:|
| **FULL** | **18 143 CIDR** | **5 354 CIDR** |
| **BALANCED** | **9 771 CIDR** | **3 095 CIDR** |
| **PERFORMANCE** | **2 225 CIDR** | **696 CIDR** |
| **MINIMAL** | **1 982 CIDR** | **681 CIDR** |
| **STABLE** | **18 063 CIDR** | **5 431 CIDR** |
| **CDN** | **1 982 CIDR** | **681 CIDR** |
| **CLOUD** | **9 174 CIDR** | **2 348 CIDR** |
| **VIDEO** | **7 506 CIDR** | **2 110 CIDR** |
| **VPN** | **8 695 CIDR** | **2 690 CIDR** |
| **MESSAGING** | **18 CIDR** | **8 CIDR** |
| **ASN ALL** | **12 949 CIDR** | **6 026 CIDR** |
| **ALL-CLOUD** | **9 174 CIDR** | **2 348 CIDR** |

**Обновлено:** 10 октября 2026, 06:25 UTC · [полная статистика](data/statistics.json)

> Статистика рассчитывается из опубликованных нормализованных CIDR-файлов после успешного прохождения проверок.
<!-- AUTO-STATS:END -->

---

Подписки обновляются автоматически дважды в сутки. Для разработчиков и контрибьюторов — устройство пайплайна и как добавить провайдера в [CONTRIBUTING.md](CONTRIBUTING.md), история изменений в [CHANGELOG.md](CHANGELOG.md).

Лицензия — [MIT](LICENSE).

Если проект оказался полезен — можно [поддержать его](https://tips.tips/000484125) ❤️
