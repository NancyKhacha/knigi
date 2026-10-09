#!/usr/bin/env python3
"""Статьи НЭН, в которых упоминаются книги каталога, — для блока «Книга в статьях НЭН».

  python3 scripts/nen_mentions.py <nen_archive.jsonl.xz>

Ищет в архиве журнала название книги в кавычках-«елочках», рядом с которым стоит фамилия
автора («Груффало» … Дональдсон), и только в материалах о книгах и чтении. Народные сказки и названия без автора пропускает: слишком
много совпадений с мультфильмами и устойчивыми выражениями. Рекламные материалы не берет.
Результат — site/content/nen-articles.json: {slug: [{url, title, date, section}]}, до трех статей
на книгу, сначала подборки и ликбезы, потом свежие. Генератор читает этот файл, архив ему не нужен.
"""
import collections, glob, json, lzma, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'site'))
sys.argv, _args = sys.argv[:1], sys.argv[1:]
import build  # noqa: E402  (clean_title и load — те же, что на сайте)

SECTION_RANK = {'Подборки': 0, 'Ликбез': 1, 'Интервью': 2, 'Мнения': 2, 'Отцовство': 2, 'Лайфхаки': 3, 'Б&Р': 3, 'Новости': 4}
PER_BOOK = 3
WINDOW = 250          # фамилия автора должна стоять не дальше этого числа знаков от названия
BOOKISH = re.compile(r'книг|книж|чита|сказк|писател|литератур|библиотек|роман|повест|стих|комикс', re.I)


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^\w ]+', ' ', s.lower().replace('ё', 'е'))).strip()


def stems(author):
    """Основы фамилий для поиска в любом падеже: «Драгунский» → «Драгунск»."""
    out = []
    for name in re.split(r'\s*;\s*', author):
        words = [w for w in re.findall(r'[А-ЯЁA-Z][а-яёa-z\-]{3,}', name)]
        for w in words[-1:] + words[:1]:          # фамилия обычно последняя, но бывает и первой
            out.append(w[:max(4, len(w) - 2)])
    return set(out)


def main(archive):
    books, _, _ = build.load()
    by_title = collections.defaultdict(list)
    for b in books:
        if re.search(r'народн|фольклор|сказки народов', b['author'], re.I) or not stems(b['author']):
            continue
        for t in {b['title'], b.get('catalogTitle', '')} - {''}:
            key = norm(t)
            if len(key) >= 4:
                by_title[key].append(b)
    found = collections.defaultdict(dict)
    n_articles = 0
    with lzma.open(archive, 'rt', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            body = r.get('body') or ''
            if 'реклама' in (r.get('tags') or '') or 'erid' in body.lower():
                continue
            title = r.get('title') or ''
            text = title + '\n' + body
            hit = False
            for m in re.finditer(r'«([^«»]{3,120})»', text):
                for b in by_title.get(norm(m.group(1)), []):
                    near = text[max(0, m.start() - WINDOW):m.end() + WINDOW]
                    if not any(st in near for st in stems(b['author'])):
                        continue
                    if not (BOOKISH.search(title) or norm(m.group(1)) in norm(title)):
                        continue
                    found[b['slug']][r['url']] = {'url': r['url'], 'title': title, 'date': r.get('date') or '',
                                                  'section': r.get('section') or ''}
                    hit = True
            n_articles += hit
    result = {}
    for slug, arts in found.items():
        arts = sorted(arts.values(), key=lambda a: a['date'], reverse=True)
        arts.sort(key=lambda a: SECTION_RANK.get(a['section'], 3))
        result[slug] = arts[:PER_BOOK]
    out = os.path.join(ROOT, 'site/content/nen-articles.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(dict(sorted(result.items())), fh, ensure_ascii=False, indent=1)
    print(f'книг со статьями: {len(result)} из {len(books)}; статей с упоминаниями: {n_articles}; файл: {out}')


if __name__ == '__main__':
    path = _args[0] if _args else next(iter(glob.glob(os.path.expanduser('~/.claude/skills/synced/*/nen-archive/data/nen_archive.jsonl.xz'))), None)
    if not path:
        sys.exit(__doc__)
    main(path)
