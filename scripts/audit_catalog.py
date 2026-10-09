#!/usr/bin/env python3
"""Аудит данных каталога «Что почитать с детьми» (n-e-n.ru/knigi/).

Читает catalog-index.json — тот же файл, из которого сервис рисует каталог:
  curl -o catalog-index.json https://n-e-n.ru/knigi/data/catalog-index.json
  python3 scripts/audit_catalog.py catalog-index.json data/

Пишет в папку:
  books-issues.csv   — по строке на книгу: что не так с текстом и данными;
  landing-pages.csv  — сколько книг набирается под возраст, тему, жанр, автора, серию.
"""
import collections, csv, json, os, re, sys

SITE = 'https://n-e-n.ru/knigi/kniga/'


def age_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return 'год'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'года'
    return 'лет'


def skeleton(text):
    """Текст «Почему рекомендуем» без подставленных значений — чтобы найти шаблон."""
    s = re.sub(r'\d+–\d+ (лет|года|год)', '<возраст>', text)
    s = re.sub(r'любит .*? и сюжеты о .*?, книга', 'любит <жанр> и сюжеты о <темы>, книга', s)
    s = re.sub(r'которые любят .*?\. В книге затрагиваются темы .*?\.', 'которые любят <жанр>. В книге затрагиваются темы <темы>.', s)
    s = re.sub(r'это .*? о .*?\. Книгу', 'это <жанр> о <темы>. Книгу', s)
    return s


# «любит» + жанр в именительном падеже вместо винительного: «любит народная сказка».
WHY_CASE = re.compile(r'люб(?:ит|ят) (народная|литературная|волшебная|авторская|сказочная|философская|'
                      r'стихотворная|подростковая|историческая|научная) \w+|люб(?:ит|ят) (роман|повесть|поэзия|'
                      r'сказка|энциклопедия|книжка-картинка)\b', re.I)
# «о» перед гласной вместо «об»: «о отношениях», «о искусстве».
WHY_OB = re.compile(r'\bо [аиоуэыАИОУЭЫ]\w+')
AUTHOR_TYPO = re.compile(r'\b(Едуард|Ерик|Алексеи)\b')
# Поле автора, собранное из мусора: «драматурги Молодые», «сказки Эскимосские», «юлия Кузнецова».
AUTHOR_GARBLED = re.compile(r'^[a-zа-яё]|«|\bАвторы\b|\bМолодые\b|\bсказки\b')
# «й» потерялась при импорте: «волшебнои полянки», «Новыи год», «Таина».
Y_WORDS_OK = {'мои', 'свои', 'твои', 'герои', 'супергерои', 'феи', 'зеи', 'камеи', 'бои'}
EDITION_IN_TITLE = re.compile(r'\((ил|худ)\.|\d-е изд')


def lost_y(text):
    return [w for w in re.findall(r'\w+(?:ои|ыи|еи)\b', text) if w.lower() not in Y_WORDS_OK] + \
        re.findall(r'\bТаина\b', text)


def surname_first(name):
    """«Ульева Елена» вместо «Елена Ульева»: фамилия на -ова/-ев/-ин/-ский и т. п. стоит первой."""
    parts = name.split()
    return (len(parts) == 2 and re.search(r'(ов|ова|ев|ева|ин|ина|ский|ская|ко|ук|юк|ер|ман|ес)$', parts[0])
            and not re.search(r'(ов|ова|ев|ева|ин|ина|ский|ская)$', parts[1]))


def main(src, outdir):
    books = json.load(open(src, encoding='utf-8'))
    os.makedirs(outdir, exist_ok=True)

    skel = collections.Counter(skeleton(b['whyRecommended']) for b in books)
    titles = collections.Counter(b['title'].strip().lower() for b in books)
    authors_by_surname = collections.defaultdict(set)
    for b in books:
        for one in re.split(r';\s*', b['author']):
            toks = [t for t in re.split(r'[\s.,]+', one) if len(t) > 2 and not re.search(r'(вич|вна)$', t)]
            if toks:
                authors_by_surname[toks[-1] if not surname_first(one) else toks[0]].add(one.strip())

    rows, totals = [], collections.Counter()
    for b in books:
        flags = []
        desc = b['shortDescription'].strip()
        if desc.endswith('…'):
            flags.append('описание: обрезанная аннотация издательства')
        if skel[skeleton(b['whyRecommended'])] > 1:
            flags.append(f'«почему рекомендуем»: шаблон ×{skel[skeleton(b["whyRecommended"])]}')
        if WHY_CASE.search(b['whyRecommended']):
            flags.append('«почему рекомендуем»: падеж («любит народная сказка»)')
        if WHY_OB.search(b['whyRecommended']):
            flags.append('«почему рекомендуем»: «о» вместо «об»')
        lo, hi = b['ageMin'], b['ageMax']
        if lo == hi:
            flags.append(f'возраст: вырожденный диапазон {b["ageLabel"]}')
        if age_word(hi) != 'лет' and b['ageLabel'].endswith('лет'):
            flags.append(f'возраст: «{b["ageLabel"]}» → «{lo}–{hi} {age_word(hi)}»')
        if AUTHOR_TYPO.search(b['author']):
            flags.append('автор: опечатка в имени')
        if AUTHOR_GARBLED.search(b['author']):
            flags.append('автор: поле собрано с ошибкой')
        if lost_y(b['title'] + ' ' + b['author']):
            flags.append(f'опечатка: «{"», «".join(lost_y(b["title"] + " " + b["author"]))}» (потеряна «й»)')
        if EDITION_IN_TITLE.search(b['title']):
            flags.append('название: данные издания (иллюстратор, номер издания) внутри названия')
        if surname_first(b['author']):
            flags.append('автор: фамилия перед именем')
        for one in re.split(r';\s*', b['author']):
            toks = [t for t in re.split(r'[\s.,]+', one) if len(t) > 2 and not re.search(r'(вич|вна)$', t)]
            key = toks[-1] if toks and not surname_first(one) else (toks[0] if toks else '')
            variants = authors_by_surname.get(key, set())
            if len(variants) > 1 and any(v != one.strip() and v.split()[-1] == one.strip().split()[-1] for v in variants):
                flags.append('автор: имя записано по-разному в разных карточках')
                break
        if titles[b['title'].strip().lower()] > 1:
            flags.append(f'название повторяется ×{titles[b["title"].strip().lower()]} — проверить дубль')
        pages = b.get('pages') or 0
        if 1900 <= pages <= 2030:
            flags.append(f'страницы: {pages} — похоже на год издания')
        elif pages > 1500:
            flags.append(f'страницы: {pages} — сбой импорта')
        elif 0 < pages < 8:
            flags.append(f'страницы: {pages} — похоже на номер в серии; объём считается неверно')
        for field, label in (('publisher', 'издательство'), ('isbn13', 'ISBN'), ('pages', 'число страниц')):
            if not b.get(field):
                flags.append(f'нет поля: {label}')
        for f in flags:
            totals[re.sub(r'(?<=страницы: )\d+|×\d+|«\d+–\d+ лет» → «\d+–\d+ \w+»|\d+–\d+ лет', '…', f)] += 1
        rows.append({
            'url': SITE + b['slug'] + '/', 'title': b['title'], 'author': b['author'],
            'publisher': b.get('publisher') or '', 'age': b['ageLabel'], 'themes': ', '.join(b['themes']),
            'genres': ', '.join(b['genres']), 'description_len': len(desc),
            'issues_count': len(flags), 'issues': '; '.join(flags),
        })
    rows.sort(key=lambda r: (-r['issues_count'], r['title']))
    with open(os.path.join(outdir, 'books-issues.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # Посадочные страницы: сколько книг из каталога набирается под каждый срез.
    land = []
    for a in range(0, 15):
        n = sum(b['ageMin'] <= a <= b['ageMax'] for b in books)
        name = 'книги для детей до года' if a == 0 else f'книги для детей {a} {age_word(a)}'
        land.append(('возраст', name, n))
    for kind, field in (('тема', 'themes'), ('жанр', 'genres')):
        for k, n in collections.Counter(t for b in books for t in b[field]).most_common():
            land.append((kind, k, n))
    land.append(('ситуация', 'книги перед сном (suitableForBedtime)', sum(bool(b.get('suitableForBedtime')) for b in books)))
    for k, n in collections.Counter(b['author'] for b in books).most_common():
        if n >= 5:
            land.append(('автор', k, n))
    for k, n in collections.Counter(b.get('seriesName') for b in books if b.get('seriesName')).most_common():
        if n >= 5:
            land.append(('серия', k, n))
    with open(os.path.join(outdir, 'landing-pages.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['type', 'slice', 'books', 'verdict'])
        for kind, name, n in land:
            verdict = 'пробел: меньше 10 книг' if n < 10 else 'мало: 10–29 книг' if n < 30 else 'хватает'
            w.writerow([kind, name, n, verdict])

    print(f'книг: {len(books)}, с замечаниями: {sum(1 for r in rows if r["issues_count"])}')
    for k, v in totals.most_common():
        print(f'  {v:5}  {k}')
    print(f'шаблонов «почему рекомендуем»: {len(skel)}; самый частый — у {skel.most_common(1)[0][1]} книг')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
