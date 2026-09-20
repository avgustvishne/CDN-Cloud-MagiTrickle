# Вклад в проект

## Добавить нового провайдера

Большинству провайдеров не нужен код — только конфиг:

1. Найди ASN провайдера через BGP/RIPEstat.
2. Добавь запись в `config/providers.json`.
3. При наличии официального CIDR-источника добавь его как источник верификации в `scripts/update_cdn_lists_impl.py`.
4. Если провайдер должен входить в специальный пресет (`cdn`, `cloud`, `video`, `vpn`, `messaging`), добавь его в `SPECIAL` в `scripts/generate_profiles.py`.
5. Открой PR. Автоматические проверки должны пройти до merge.

## Сообщить об ошибке в данных

Укажи провайдера, подсеть и источник (ASN/WHOIS/BGP/официальный список), на который можно сослаться.

## Локальный прогон тестов

```bash
python -m compileall scripts tests
python -m unittest discover -s tests -q
```
