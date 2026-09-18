<div align="center">

# 🌐 CDN-Cloud-MagiTrickle

## Актуальные IP/CIDR-подписки для MagiTrickle

**CDN · Cloud · Video · VPN · ASN**  
**IPv4 + IPv6 · автоматическое обновление · без дублей**

[![Update](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle/actions/workflows/update.yml/badge.svg)](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle/actions/workflows/update.yml)

[**🚀 FULL**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v4.txt) · [**⚡ PERFORMANCE**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/performance-v4.txt) · [**⚖️ BALANCED**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v4.txt) · [**📦 MINIMAL**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v4.txt)

[📊 Status](STATUS.md) · [📁 Все подписки](data/) · [⚙️ Providers](config/providers.json)

</div>

---

## 🚀 Быстрый выбор

| Нужно | Профиль |
|---|---|
| Максимальное покрытие | **FULL** |
| Хороший баланс покрытия и размера | **BALANCED** |
| Минимальный объём правил | **MINIMAL** |
| CDN с упором на скорость | **PERFORMANCE** |
| Только CDN | [**CDN**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v4.txt) |
| Cloud/VPS | [**CLOUD**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v4.txt) |
| Video/CDN | [**VIDEO**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v4.txt) |
| VPN/VPS | [**VPN**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v4.txt) |
| Все собранные ASN | [**ASN ALL**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v4.txt) |

### Основные подписки

| Профиль | IPv4 | IPv6 |
|---|---|---|
| **FULL** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v6.txt) |
| **BALANCED** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v6.txt) |
| **PERFORMANCE** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/performance-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/performance-v6.txt) |
| **MINIMAL** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v6.txt) |

## 🌐 Отдельные провайдеры

Готовые IPv4/IPv6-подписки для основных CDN и cloud-провайдеров:

### Провайдеры

AWS · Cloudflare · Hetzner · OVH · Akamai · DigitalOcean · Microsoft · Oracle · Alibaba · CDN77 · Fastly · Melbicom · BuyVM · Vultr · Contabo · Scaleway · Gcore · Backblaze

Полный список и ссылки: [**`data/`**](data/) · [**`config/providers.json`**](config/providers.json)

## 💬 Сервисы

Отдельные доменные подписки для сервисов. Они формируются автоматически из реестра сервисов и обновляются каждые 12 часов. DNS-адреса используются только как evidence и не публикуются как эксклюзивные IP-маршруты.

| Сервис | Домены | Состояние |
|---|---|---|
| **Telegram** | [Raw](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/services/telegram-domains.txt) | `domain_ready` |
| **WhatsApp** | [Raw](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/services/whatsapp-domains.txt) | `domain_ready` |
| **Signal** | [Raw](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/services/signal-domains.txt) | `domain_ready` |

Машиночитаемый отчёт: [**service-intelligence.json**](data/service-intelligence.json). Источник истины для списка доменов — официальная документация соответствующего сервиса.

## 🧠 Внешняя разведка источников

Проект дополнительно проверяет внешние списки как **evidence/cross-check**, но не использует их для автоматического изменения опубликованных провайдерских подписок.

Проверяются 9 независимых внешних источников:

- Antifilter IP и Community IP;
- Antifilter Domain и Community Domain;
- Re:filter IP и Domain;
- ItDogInfo GeoBlock domains;
- независимый агрегат CDN/hosting CIDR;
- **Russia Whitelist GeoIP** — отфильтрованные IPv4-диапазоны из белых списков РФ (`other`, `vk`, `yandex`).

Russia Whitelist GeoIP учитывается только как внешнее свидетельство: его диапазоны **не приписываются автоматически** Cloudflare, Akamai, Fastly или другим провайдерам. Источник собирается из трёх категорий и анализируется с точным объединением перекрывающихся CIDR.

Каждые 12 часов workflow сохраняет только метаданные: количество записей, SHA-256 источника, точное IPv4/IPv6-покрытие и пересечение с `FULL`/`PERFORMANCE`. Сырые внешние списки в репозиторий не копируются. Ошибка внешнего источника не заменяет и не удаляет рабочие данные проекта.

Машиночитаемый отчёт: [**external-source-intelligence.json**](data/external-source-intelligence.json) · реестр источников: [**source_registry.json**](config/source_registry.json).

## 🔗 ASN

[**ASN ALL — IPv4**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v4.txt) · [**ASN ALL — IPv6**](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v6.txt)

## 🛠️ Как использовать

1. Откройте нужную подписку.
2. Скопируйте **Raw URL**.
3. Добавьте URL в MagiTrickle как источник CIDR.

Если не знаете, что выбрать, начните с **BALANCED**. Для максимального покрытия используйте **FULL**, для меньшего объёма правил — **MINIMAL** или **PERFORMANCE**.

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

> Статистика рассчитывается из опубликованных нормализованных CIDR-файлов после успешного прохождения проверок.
<!-- AUTO-STATS:END -->

## 🔄 Обновление

Данные и количество CIDR обновляются автоматически после успешной генерации и проверок. Последняя генерация: `2026-09-18T04:45:09Z`. [Машиночитаемая статистика](data/statistics.json).

## ℹ️ Важно

CIDR — это сетевой диапазон, а не количество отдельных IP. Наличие CIDR не гарантирует доступность каждого адреса внутри него.

## 📊 Статус

[**Открыть текущий статус проекта →**](STATUS.md)

## ❤️ Поддержка

[Поддержать проект](https://tips.tips/000484125)
