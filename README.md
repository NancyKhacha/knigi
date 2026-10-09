# Книги НЭН: аудит и доработка для поиска

Как сделать сервис [«Что почитать с детьми»](https://n-e-n.ru/knigi/) заметнее в Яндексе и Google.

**Для редакции**
- [AUDIT.md](AUDIT.md) — что мешает поиску и в каком порядке это исправлять.
- [cards/STYLEGUIDE.md](cards/STYLEGUIDE.md) — как писать карточки книг в стиле НЭН.
- [cards/pilot.md](cards/pilot.md) — пилот: 32 карточки по новому шаблону, на согласование.
- [fixes/needs-review.csv](fixes/needs-review.csv) — что в данных каталога нужно решить вручную.
- [fixes/editions.csv](fixes/editions.csv) — книги с несколькими карточками: выбрать главную.
- [data/podborki-candidates.csv](data/podborki-candidates.csv) — подборки из архива НЭН для переноса в сервис.

**Для разработчика**
- [TZ.md](TZ.md) — техническое задание.
- [fixes/catalog-fixes.json](fixes/catalog-fixes.json) — исправления данных для 1142 карточек.
- [cards/pilot.json](cards/pilot.json) — новые тексты карточек в формате для импорта.

**Скрипты**

```bash
curl -o catalog-index.json https://n-e-n.ru/knigi/data/catalog-index.json
python3 scripts/audit_catalog.py catalog-index.json data/      # найти проблемы в каталоге
python3 scripts/fix_catalog.py catalog-index.json fixes/       # собрать исправления данных
python3 scripts/check_cards.py cards/pilot.json cards/pilot.md # проверить карточки и собрать превью
```
