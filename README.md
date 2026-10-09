# Книги НЭН: аудит для поиска

Как сделать сервис [«Что почитать с детьми»](https://n-e-n.ru/knigi/) заметнее в Яндексе и Google.

- [AUDIT.md](AUDIT.md) — отчет: что мешает поиску, что исправить и в каком порядке.
- [data/](data/) — таблицы с проблемами по каждой книге, расчетом посадочных страниц и подборками из архива для переноса.
- [scripts/audit_catalog.py](scripts/audit_catalog.py) — пересчет таблиц по свежим данным каталога:

```bash
curl -o catalog-index.json https://n-e-n.ru/knigi/data/catalog-index.json
python3 scripts/audit_catalog.py catalog-index.json data/
```
