<p align="center"><img src="docs/assets/hero.svg" alt="CDN-Cloud-MagiTrickle — IPv4, IPv6, ASN, CDN, Cloud, Video and VPN subscriptions" width="100%"></p>

<div align="center">

# CDN + Cloud MagiTrickle

**IPv4 / IPv6 CIDR · ASN · CDN · Cloud · Video · VPN**

Автоматически обновляемые сетевые подписки для MagiTrickle.

[🇷🇺 Русский](README.md) · [🇬🇧 English](README.en.md)

[⚡ Быстрый старт](#-быстрый-старт) · [📦 Профили](#-профили) · [☁️ Провайдеры](#️-провайдеры) · [🔢 ASN](#-asn-подписки) · [❤️ Поддержка](#️-поддержка)

[![MagiTrickle](https://img.shields.io/badge/MagiTrickle-subscriptions-2ea44f?style=flat-square)](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle)
[![IPv4](https://img.shields.io/badge/IP-v4-0969da?style=flat-square)](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle)
[![IPv6](https://img.shields.io/badge/IP-v6-8250df?style=flat-square)](https://github.com/avgustvishne/CDN-Cloud-MagiTrickle)

</div>

## ✨ Что здесь есть

- IPv4 и IPv6 CIDR
- ASN-подписки
- CDN и Cloud наборы
- Готовые профили **FULL / BALANCED / MINIMAL**
- Отдельные наборы **CDN / Cloud / Video / VPN**
- Отдельные списки по провайдерам
- Общий **ASN ALL** без повторяющихся CIDR
- Автоматическое обновление

## ⚡ Быстрый старт

Если не знаешь, что выбрать — используй **BALANCED**.

| Профиль | IPv4 | IPv6 | Для чего |
|---|---|---|---|
| **FULL** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/full-v6.txt) | Максимальное покрытие |
| **BALANCED** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/balanced-v6.txt) | Рекомендуемый вариант |
| **MINIMAL** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/minimal-v6.txt) | Минимальный объём |

## 📦 Специализированные наборы

| Набор | IPv4 | IPv6 |
|---|---|---|
| **CDN** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cdn-v6.txt) |
| **Cloud** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/cloud-v6.txt) |
| **Video** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/video-v6.txt) |
| **VPN** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/vpn-v6.txt) |

## 🔢 Все ASN сразу

- **ASN ALL IPv4:** [asn-all-v4.txt](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v4.txt)
- **ASN ALL IPv6:** [asn-all-v6.txt](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v6.txt)

**ALL-CLOUD IPv4:** [all-cloud-v4.txt](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt)  
**ALL-CLOUD IPv6:** [all-cloud-v6.txt](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt)

`ALL-CLOUD` — единый дедуплицированный агрегат всех провайдерских списков. Отдельный `PROVIDERS ALL` не создаётся, чтобы не дублировать эти данные.

Все источники объединяются, одинаковые CIDR удаляются, вложенные сети агрегируются, IPv4 и IPv6 хранятся отдельно.

## ☁️ Провайдеры

Отдельные подписки каждого провайдера имеют **прямые raw-ссылки GitHub** на IPv4 и IPv6.

| Провайдер | IPv4 | IPv6 |
|---|---|---|
| **AWS** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/aws-v6.txt) |
| **Cloudflare** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cloudflare-v6.txt) |
| **Hetzner** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/hetzner-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/hetzner-v6.txt) |
| **OVH** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/ovh-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/ovh-v6.txt) |
| **Akamai** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/akamai-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/akamai-v6.txt) |
| **DigitalOcean** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/digitalocean-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/digitalocean-v6.txt) |
| **Microsoft** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/microsoft-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/microsoft-v6.txt) |
| **Oracle** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/oracle-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/oracle-v6.txt) |
| **Alibaba** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/alibaba-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/alibaba-v6.txt) |
| **CDN77** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cdn77-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/cdn77-v6.txt) |
| **Fastly** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/fastly-v6.txt) |
| **Melbicom** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/melbicom-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/melbicom-v6.txt) |
| **BuyVM** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/buyvm-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/buyvm-v6.txt) |
| **Vultr** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/vultr-v6.txt) |
| **Contabo** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/contabo-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/contabo-v6.txt) |
| **Scaleway** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/scaleway-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/scaleway-v6.txt) |
| **Gcore** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/gcore-v6.txt) |
| **Backblaze** | [IPv4](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/backblaze-v4.txt) | [IPv6](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/backblaze-v6.txt) |

Полный список ASN доступен в [конфигурации проекта](config/providers.json).

## ❤️ Поддержка

Если проект оказался полезен, его развитие можно поддержать:

**Поддержать проект:** https://tips.tips/000484125

Спасибо! ❤️

---

<sub>Автоматически генерируемые CIDR-подписки для MagiTrickle.</sub>
