# CDN + Cloud MagiTrickle

Готовые **IPv4/IPv6 CIDR-подписки** для MagiTrickle.

Списки автоматически обновляются **2 раза в сутки**, очищаются от дублей и проверяются перед публикацией.

## Провайдеры

AWS · Cloudflare · Hetzner · OVH · Akamai · DigitalOcean · Microsoft · Oracle · Alibaba · CDN77 · Fastly · Melbicom · BuyVM/Frantech · Vultr · Contabo · Scaleway · Gcore · Backblaze

## Готовые подписки

**Все IPv4**
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v4.txt`

**Все IPv6**
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/all-cloud-v6.txt`

**Отдельный провайдер**
`https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/<provider>-v4.txt`

Для IPv6 используйте `<provider>-v6.txt`.

## Источники

Для AWS, Cloudflare, Fastly и Gcore используются официальные списки провайдеров. Для остальных — анонсируемые BGP-префиксы через RIPEstat.

При обновлении:

- удаляются дубли и некорректные CIDR;
- объединяются пересекающиеся сети;
- отбрасываются не-global адреса;
- проверяется резкое уменьшение списка;
- при ошибке сохраняется предыдущая рабочая версия.

## Автообновление

GitHub Actions запускает обновление каждые **12 часов**.

Файл workflow:

`.github/workflows/update.yml`

Запуск также можно выполнить вручную через **GitHub → Actions → Update MagiTrickle subscriptions → Run workflow**.

## Формат

Каждый адрес находится на отдельной строке:

```
1.2.3.0/24
2001:db8::/32
```

Файлы `*-v4.txt` и `*-v6.txt` — это **CIDR-подписки**.

## Структура

```
config/    настройки провайдеров
scripts/   генератор списков
data/      готовые подписки
.github/   GitHub Actions
```

## Версия

**V15**

V15 — стабильный генератор подписок IPv4/IPv6 без дополнительного программного обеспечения.

> Списки предназначены для маршрутизации и правил MagiTrickle. Наличие IP в списке не гарантирует доступность конкретного сервиса.
