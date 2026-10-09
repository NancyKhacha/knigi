# Книги НЭН: «Что почитать с детьми»

Новая версия сервиса [n-e-n.ru/knigi](https://n-e-n.ru/knigi/):
- все страницы отдаются готовым HTML, и поисковики видят текст;
- у каждой из 2495 книг своя рекомендация редакции;
- дизайн сделан по стайлгайду НЭН.

**Рабочая версия:** https://nancykhacha.github.io/knigi/. Она закрыта от индексации и пересобирается сама после каждого изменения в репозитории.

## Разработчику

Начать с [TZ.md](TZ.md). Там:
- что сделать на сайте сразу — удалить пять книг из [`fixes/removed.csv`](fixes/removed.csv);
- как собрать и поставить новую версию на n-e-n.ru;
- что в ней есть и где лежат данные.

```bash
NEN_PREVIEW=0 python3 site/build.py --out dist   # сборка для n-e-n.ru/knigi/ (Python 3, без зависимостей)
python3 scripts/seo_check.py dist                # проверка перед выкладкой: «ошибок: 0»
python3 site/build.py                            # рабочая версия в docs/ (noindex)
```

Устройство репозитория:

| Папка | Что в ней |
|---|---|
| `site/build.py` | генератор сайта: шаблоны страниц, мета-теги, JSON-LD, sitemap |
| `site/assets/` | стили (`nen.css`), скрипт (`app.js`: фильтры, подбор книги, избранное, «Поделиться»), картинки |
| `site/data/books.json` | каталог |
| `site/content/` | подборки, тексты страниц, аннотации редакции, сложные темы, ссылки на статьи журнала |
| `cards/` | тексты карточек книг (`pilot.json`, `batches/*.json`) и все, что связано с их написанием |
| `fixes/` | исправления данных каталога для переноса в базу сайта |
| `scripts/` | проверки и сборка данных |
| `.github/workflows/pages.yml` | автосборка рабочей версии на GitHub Pages |

## Редакции

- [cards/DECISIONS.md](cards/DECISIONS.md) — что редакция уже решила и что еще осталось решить:
  - книги 18+;
  - удаленные книги;
  - ошибки авторов и аннотаций;
  - дубли;
  - возраст;
  - сложные темы.
- [cards/STYLEGUIDE.md](cards/STYLEGUIDE.md) — как писать карточки книг.
- [cards/review.csv](cards/review.csv) — пометки по каждой книге: откуда текст, предложенный возраст, замечания к данным каталога.
- [fixes/author-fixes.csv](fixes/author-fixes.csv) — правки авторов. У 104 строк статус «проверить»: их нужно сверить с книгой.
- [fixes/needs-review.csv](fixes/needs-review.csv), [fixes/editions.csv](fixes/editions.csv) — спорные данные и книги с несколькими изданиями.
- [data/podborki-candidates.csv](data/podborki-candidates.csv) — 131 книжная подборка из архива журнала, которые можно перенести в сервис.
- [AUDIT.md](AUDIT.md) — исходный аудит: что мешало поиску и что из этого уже сделано.

Другие команды:

```bash
python3 scripts/check_cards.py cards/batches/batch-001.json   # проверить тексты карточек
python3 scripts/collect_notes.py               # обновить review.csv и PROGRESS.md
python3 scripts/nen_mentions.py                # обновить ссылки на статьи НЭН (нужен архив журнала)
```
