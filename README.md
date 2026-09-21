<div align="center">

<img src="docs/assets/hero.svg" alt="CDN-Cloud-MagiTrickle" width="100%">

# CDN-Cloud-MagiTrickle

**Актуальные IPv4/IPv6 CIDR-подписки для [MagiTrickle](https://github.com/MagiTrickle/MagiTrickle) — CDN, облака, видео, VPN, Telegram, Twitter/X**

[![Update MagiTrickle subscriptions](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle/actions/workflows/update.yml/badge.svg)](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle/actions/workflows/update.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Обновление](https://img.shields.io/badge/обновление-каждые%2012ч-16b9ff)](.github/workflows/update.yml)

[📈 Дашборд](https://avgustvishne.github.io/CDN-Cloud-MagiTrickle/) · [📊 Статус](STATUS.md) · [💚 Здоровье источников](HEALTH.md) · [📝 Изменения](CHANGELOG.md) · [⚙️ Провайдеры](config/providers.json) · [🤝 Вклад в проект](CONTRIBUTING.md)

</div>

---

## Что это

Репозиторий дважды в сутки собирает диапазоны адресов CDN, облачных провайдеров и отдельных сервисов (Telegram, Twitter/X) из официальных источников, ASN/BGP-данных и RIPEstat, сверяет их между собой и публикует готовые .txt-подписки, которые можно напрямую подключить в MagiTrickle.

## Быстрый выбор

| Нужно | Профиль | IPv4 | IPv6 |
|---|---|:---:|:---:|
| Максимальное покрытие | **FULL** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v6.txt) |
| Широкое покрытие без гиперскейл-пулов | **BALANCED** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v6.txt) |
| CDN + компактный периферийный набор | **PERFORMANCE** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/performance-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/performance-v6.txt) |
| Только базовый набор CDN | **MINIMAL** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v6.txt) |
| Только CDN | **CDN** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v6.txt) |
| Облако/VPS | **CLOUD** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v6.txt) |
| Видео/CDN | **VIDEO** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v6.txt) |
| VPN/VPS | **VPN** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v6.txt) |
| Все собранные ASN | **ASN ALL** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v6.txt) |
| Тот же набор, что FULL, но обновляется раз в неделю | **STABLE** | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/stable-v4.txt) | [↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/stable-v6.txt) |

**FULL** включает все настроенные провайдеры. **ALL-CLOUD** — отдельный агрегат для AWS, Cloudflare, Microsoft, Oracle, Alibaba и DigitalOcean; он намеренно отличается от FULL. **STABLE** — это те же данные, что в FULL, просто публикуются раз в неделю (по воскресеньям), а не дважды в сутки — для роутеров/прошивок, где частая перезагрузка правил маршрутизации нежелательна.

> **MESSAGING (Telegram + Twitter/X)** временно убран из этой таблицы: провайдерские файлы для Telegram/Twitter ещё ни разу не были успешно опубликованы (`data/telegram-v4.txt`/`twitter-v4.txt` отсутствуют), и держать в README ссылку на несуществующий файл ломает `check_links.py` на каждом прогоне. Вернём строку в таблицу, как только пайплайн один раз успешно сгенерирует реальные данные для обоих провайдеров.

## Как использовать

1. Выбери профиль в таблице.
2. Открой IPv4 или IPv6 — это прямая raw-ссылка.
3. Добавь URL в MagiTrickle как источник подписки.

<!-- AUTO-STATS:START -->
## 📊 Актуальная статистика

| Набор | IPv4 | IPv6 |
|---|---:|---:|
| **FULL** | **17 471 CIDR** | **5 264 CIDR** |
| **PERFORMANCE** | **8 499 CIDR** | **1 516 CIDR** |
| **BALANCED** | **15 322 CIDR** | **4 696 CIDR** |
| **MINIMAL** | **8 242 CIDR** | **2 763 CIDR** |
| **ASN ALL** | **12 601 CIDR** | **5 963 CIDR** |
| **ALL-CLOUD** | **17 471 CIDR** | **5 264 CIDR** |

**Обновлено:** `2026-09-18T04:45:09Z` · [полная статистика](data/statistics.json)
<!-- AUTO-STATS:END -->

## Провайдеры

CDN: Cloudflare, Akamai, Fastly, CDN77, Gcore.  
Облака/хостинг: AWS, Microsoft Azure, Oracle Cloud, Alibaba Cloud, DigitalOcean, Hetzner, OVH, Vultr, Scaleway, Contabo, BuyVM, Backblaze, Melbicom.  
Сервисы: Telegram, Twitter/X.

Полный список ASN — в [config/providers.json](config/providers.json). Инструкции для новых провайдеров — в [CONTRIBUTING.md](CONTRIBUTING.md).

## Как это работает

1. Источники провайдеров собираются из официальных CIDR-списков и ASN/BGP/RIPEstat.
2. Политика config/policy.json применяется и к обычным провайдерским данным, и к ASN-агрегатам.
3. Генератор строит FULL и специализированные профили, включая отдельный MESSAGING.
4. Проверки валидируют CIDR, покрытие, ссылки, статистику и регрессионные изменения.
5. Только успешный прогон публикует обновлённые подписки.

## Автоматизация

GitHub Actions запускает обновление каждые 12 часов. Реальные обновления получают отдельные data-YYYYMMDD-HHMM теги. История изменений хранится в [CHANGELOG.md](CHANGELOG.md).

## Вклад

См. [CONTRIBUTING.md](CONTRIBUTING.md).

## Лицензия

MIT.
