# Книги НЭН: «Что почитать с детьми»

Новая версия сервиса [n-e-n.ru/knigi](https://n-e-n.ru/knigi/): контент виден поисковикам, у каждой книги своя рекомендация редакции, дизайн по стайлгайду НЭН.

**Рабочая версия:** https://nancykhacha.github.io/knigi/ — закрыта от индексации и пересобирается сама после каждого изменения в репозитории.

## Для редакции
- [AUDIT.md](AUDIT.md) — что мешало поиску и что исправлено.
- [cards/STYLEGUIDE.md](cards/STYLEGUIDE.md) — как писать карточки книг.
- [cards/PROGRESS.md](cards/PROGRESS.md) — сколько карточек готово.
- [cards/review.csv](cards/review.csv) — что проверить по каждой книге: тексты, написанные только по аннотации, предложенный возраст, ошибки каталога.
- [fixes/needs-review.csv](fixes/needs-review.csv), [fixes/editions.csv](fixes/editions.csv) — спорные данные и книги с несколькими карточками.
- [data/podborki-candidates.csv](data/podborki-candidates.csv) — подборки из архива НЭН для переноса в сервис.

## Для разработчика
- [TZ.md](TZ.md) — как поставить на n-e-n.ru (раздел 0) и что должно получиться.
- `site/build.py` — генератор сайта. `site/assets/` — стили и скрипт. `site/content/` — подборки и тексты страниц. `site/data/books.json` — каталог.
- `cards/pilot.json`, `cards/batches/*.json` — тексты карточек.

```bash
python3 site/build.py                          # рабочая версия в docs/ (noindex)
NEN_PREVIEW=0 python3 site/build.py --out dist # версия для n-e-n.ru/knigi/
python3 scripts/check_cards.py cards/batches/batch-001.json   # проверить карточки
python3 scripts/collect_notes.py               # обновить review.csv и PROGRESS.md
python3 scripts/seo_check.py dist              # SEO-проверка собранного сайта
python3 scripts/nen_mentions.py                # обновить ссылки на статьи НЭН (нужен архив журнала)
```
