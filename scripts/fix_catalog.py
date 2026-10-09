#!/usr/bin/env python3
"""Исправления данных каталога «Что почитать с детьми» (n-e-n.ru/knigi/).

  python3 scripts/fix_catalog.py catalog-index.json fixes/

Пишет в папку:
  catalog-fixes.json       — патч для разработчика: {slug: {поле: новое значение}};
  catalog-fixes.csv        — те же правки построчно (было → стало), для проверки редактором;
  catalog-index.fixed.json — каталог с примененными правками;
  needs-review.csv         — что автоматически не исправить: решает редакция;
  editions.csv             — несколько карточек одного произведения.

Правится только то, в чем нет сомнений: склонение возраста, сбойные числа страниц,
формат имен авторов, опечатки, данные издания в названии, падежи в «Почему рекомендуем».
"""
import collections, copy, csv, json, os, re, sys

# --- Возраст -----------------------------------------------------------------

def age_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return 'год'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'года'
    return 'лет'


def age_label(lo, hi):
    if lo == hi:
        return f'{hi} {age_word(hi)}'
    return f'{lo}–{hi} {age_word(hi)}'


# --- Авторы ------------------------------------------------------------------

# Варианты, которые правилами не поймать: опечатки, поля, собранные задом наперед,
# разные написания одного человека.
AUTHOR_OVERRIDES = {
    'Е дуард Николаевич Успенскии': 'Эдуард Успенский',
    'Едуард Успенский': 'Эдуард Успенский',
    'Ерик Булатов': 'Эрик Булатов',
    'Алексеи Биргер': 'Алексей Биргер',
    'юлия Кузнецова': 'Юлия Кузнецова',
    'драматурги Молодые': 'Молодые драматурги',
    'сказки Эскимосские': 'Эскимосские сказки',
    'сборника рассказов «Школа Шрёдингера» Авторы': 'Авторы сборника рассказов «Школа Шрёдингера»',
    'Г.-Х. Андерсен': 'Ханс Кристиан Андерсен',
    'Андерсен Ханс Кристиан': 'Ханс Кристиан Андерсен',
    'Клайв С. Льюис': 'Клайв Стейплз Льюис',
    'Кир Булычев': 'Кир Булычёв',
    'К. Булычев': 'Кир Булычёв',
    'Даниела Кулот': 'Даниэла Кулот',
    'Рудольф Распе': 'Рудольф Эрих Распе',
    'П. П. Ершов': 'Пётр Ершов',
    'Петр Ершов': 'Пётр Ершов',
    'А. Н. Афанасьев': 'Александр Афанасьев',
    'А. С. Пушкин': 'Александр Пушкин',
    'Л. Лагин': 'Лазарь Лагин',
    'В. Чижиков': 'Виктор Чижиков',
    'Л. Пантелеев': 'Леонид Пантелеев',
    'В. Драгунский': 'Виктор Драгунский',
    'Г. Цыферов': 'Геннадий Цыферов',
    'А. Волков': 'Александр Волков',
    'А. Курляндский': 'Александр Курляндский',
    'А. Усачёв': 'Андрей Усачёв',
    'В. Постников': 'Валентин Постников',
    'С. Г. Козлов': 'Сергей Козлов',
}

# Уже записаны как «Имя Фамилия», хотя по словарю имен похожи на перевернутые.
KEEP_AS_IS = {'Элисон Джей', 'Энджи Томас', 'Рэйко Хиросима', 'Янец Леви'}

# В поле автора стоит переводчик или иллюстратор, хотя у книги известный автор.
TITLE_AUTHOR = {
    'Маленький принц': 'Антуан де Сент-Экзюпери',
    'Снежная королева': 'Ханс Кристиан Андерсен',
    'Алиса в Стране чудес': 'Льюис Кэрролл',
}

SURNAME_END = re.compile(r'(ов|ова|ев|ева|ёв|ёва|ин|ина|ын|ына|ский|ская|цкий|цкая|ой|ых|их|ко|ук|юк|ич|ман|сон|сен|ер|ли|ти|ни)$')
PATRONYMIC = re.compile(r'(вич|вна|ична|ьич)$')
INITIAL = re.compile(r'^[А-ЯЁA-Z]\.(-[А-ЯЁA-Z]\.)?$')


def is_patronymic(token):
    return bool(PATRONYMIC.search(token))


MANUAL_GIVEN = {'Роб', 'Тьерри', 'Елена', 'Кристина', 'Анна', 'Мария', 'Юлия', 'Ольга', 'Наталья', 'Татьяна',
    'Ирина', 'Екатерина', 'Светлана', 'Анастасия', 'Алексей', 'Андрей', 'Сергей', 'Дмитрий', 'Михаил',
    'Александр', 'Борис', 'Ксения', 'Марина', 'Дарья', 'Лидия', 'Лида', 'Виктория', 'Софи', 'Люси',
    'Эв', 'Тереза', 'Стив', 'Мелани', 'Норберт', 'Фиона', 'Кармен', 'Мартин', 'Андреа', 'Бертран',
    'Кристиан', 'Пьер', 'Мари-Элен', 'Тибо', 'Альба', 'Ксабье', 'Дженис', 'Стефани', 'Нелли',
    'Джейн', 'Аксель', 'Бьянка', 'Натали', 'Наталия', 'Роберт', 'Льюис', 'Ханс', 'Йолан', 'Агнешка',
    'Нина'}


def learn_given_names(authors):
    """Имена берем из самого каталога: первое слово в записях «Имя Фамилия»."""
    given = collections.Counter()
    for a in authors:
        for one in re.split(r'\s*;\s*', a):
            t = one.split()
            if len(t) == 2 and SURNAME_END.search(t[1]) and not SURNAME_END.search(t[0]) and t[1] not in MANUAL_GIVEN:
                given[t[0]] += 1
            if len(t) == 3 and is_patronymic(t[1]):
                given[t[0]] += 1
    names = {n for n, c in given.items() if c >= 1}
    names |= MANUAL_GIVEN
    return names


def given_first(name, given):
    """«Ульева Елена» → «Елена Ульева», «Скоттон Роб» → «Роб Скоттон»."""
    t = name.split()
    if len(t) < 2:
        return name
    t = [x for x in t if not (is_patronymic(x) and x not in given)] if len(t) > 2 else t
    if len(t) >= 2 and t[0] not in given and not INITIAL.match(t[0]):
        tail = t[1:]
        if all(x in given or INITIAL.match(x) for x in tail) and any(x in given for x in tail):
            return ' '.join(tail + [t[0]])
    return ' '.join(t)


def split_authors(raw):
    raw = raw.strip()
    if ';' in raw:
        # «Дельваль, Мари-Элен; Эртель Пьер»: внутри части тоже может стоять «Фамилия, Имя».
        return [' '.join(reversed([x.strip() for x in p.split(',')])) if p.count(',') == 1 else p.strip()
                for p in raw.split(';') if p.strip()]
    if ',' in raw:
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        # «Дельваль, Мари-Элен, Эртель, Пьер»: фамилия и имя чередуются через запятую.
        if len(parts) % 2 == 0 and all(len(p.split()) == 1 for p in parts[1::2]) \
                and all(len(p.split()) <= 2 for p in parts[0::2]):
            return [f'{parts[i + 1]} {parts[i]}' for i in range(0, len(parts), 2)]
        return parts
    return [raw]


def normalize_author(raw, given):
    if raw in AUTHOR_OVERRIDES:
        return AUTHOR_OVERRIDES[raw]
    out = []
    for one in split_authors(raw):
        one = AUTHOR_OVERRIDES.get(one, one)
        t = one.split()
        if len(t) == 3 and is_patronymic(t[1]):          # Сергей Владимирович Михалков
            one = f'{t[0]} {t[2]}'
        if one not in KEEP_AS_IS:
            one = given_first(one, given)
        # Инициалы раскрываем только по списку AUTHOR_OVERRIDES: «Л. Сидорова» может быть кем угодно.
        out.append(AUTHOR_OVERRIDES.get(one, one))
    return '; '.join(dict.fromkeys(out))


# --- Названия ----------------------------------------------------------------

EDITION = re.compile(r'\s*\((?:ил\.|иллюстрации|худ\.)[^)]*\)|\s*\(син\.\)|\s*\(Внеклассное чтение\)'
                     r'|\s*\(\d-е изд\.?\)|,?\s*\d-е изд(?:ание|\.)?(?!\w)', re.I)
SERIES_NO = re.compile(r'\s*\(#(\d+)\)\s*$')
TITLE_TYPOS = {'Новыи': 'Новый', 'волшебнои': 'волшебной', 'Таина ': 'Тайна ', 'непослушаня': 'непослушания'}


def clean_title(title):
    note = '; '.join(m.strip(' ()') for m in EDITION.findall(title))
    t = EDITION.sub('', title).strip()
    series_no = None
    m = SERIES_NO.search(t)
    if m:
        series_no = int(m.group(1))
        t = SERIES_NO.sub('', t).strip()
    for bad, good in TITLE_TYPOS.items():
        t = t.replace(bad, good)
    return t, note, series_no


# --- «Почему рекомендуем» ----------------------------------------------------

GENRE_ACC = {
    'народная сказка': 'народные сказки', 'литературная сказка': 'литературные сказки',
    'книжка-картинка': 'книжки-картинки', 'философская сказка': 'философские сказки',
    'сказочная история': 'сказочные истории', 'стихотворная история': 'стихотворные истории',
    'подростковая повесть': 'подростковые повести', 'автобиографическая повесть': 'автобиографические повести',
    'графический роман': 'графические романы', 'научно-популярная литература': 'научно-популярные книги',
    'сборник рассказов': 'сборники рассказов', 'книга-игра': 'книги-игры', 'книга-искалка': 'книги-искалки',
    'роман': 'романы', 'повесть': 'повести', 'поэзия': 'поэзию', 'комедия': 'комедии', 'рассказ': 'рассказы',
    'фантастика': 'фантастику',
}


def fix_why(text):
    def acc(m):
        words = m.group(2)
        for nom, a in sorted(GENRE_ACC.items(), key=lambda kv: -len(kv[0])):
            words = re.sub(rf'(?<![\w-]){re.escape(nom)}(?![\w-])', a, words)
        return m.group(1) + words + m.group(3)
    text = re.sub(r'(люб(?:ит|ят) )(.*?)( и сюжеты о|\.)', acc, text, count=1)
    text = re.sub(r'\bо (?=[аиоуэыАИОУЭЫ])', 'об ', text)
    return text


# --- Главное -----------------------------------------------------------------

def main(src, outdir):
    books = json.load(open(src, encoding='utf-8'))
    os.makedirs(outdir, exist_ok=True)
    given = learn_given_names(b['author'] for b in books)

    patch, rows, review = {}, [], []
    fixed = []
    for b in books:
        nb = copy.deepcopy(b)
        ch = {}

        lbl = age_label(b['ageMin'], b['ageMax'])
        if lbl != b['ageLabel']:
            ch['ageLabel'] = lbl

        pages = b.get('pages') or 0
        reason = None
        if pages > 1500:
            reason = f'{pages} — сбой импорта'
        elif 1900 <= pages <= 2030:
            reason = f'{pages} — год издания'
        elif 0 < pages < 8:
            reason = f'{pages} — номер в серии'
        if reason:
            ch['pages'] = None
            if b.get('lengthCategory'):
                ch['lengthCategory'] = None
            review.append((b['slug'], b['title'], 'объем', f'Число страниц было {reason}; объем чтения нужно определить заново'))

        title, note, series_no = clean_title(b['title'])
        if title != b['title']:
            ch['title'] = title
        if note:
            ch['editionNote'] = note
        if series_no is not None:
            ch['seriesNumber'] = series_no

        author = normalize_author(b['author'], given)
        for prefix, real in TITLE_AUTHOR.items():
            if title.startswith(prefix) and real not in author:
                ch['editionContributors'] = author
                author = real
        if author != b['author']:
            ch['author'] = author

        why = fix_why(b['whyRecommended'])
        if why != b['whyRecommended']:
            ch['whyRecommended'] = why

        if re.search(r'Котятова|Баринова', b['author']):
            review.append((b['slug'], b['title'], 'автор', f'В поле автора составители пересказа: «{b["author"]}». Указать автора или «Русская народная сказка»'))
        if b['ageMin'] == 7 and b['ageMax'] == 12:
            review.append((b['slug'], b['title'], 'возраст', '«7–12 лет» стоит у 399 книг — похоже на значение по умолчанию; проверить'))

        if ch:
            patch[b['slug']] = ch
            for k, v in ch.items():
                rows.append({'slug': b['slug'], 'title': b['title'], 'field': k,
                             'old': json.dumps(b.get(k), ensure_ascii=False) if not isinstance(b.get(k), str) else b.get(k),
                             'new': json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v})
            nb.update(ch)
        fixed.append(nb)

    # Издания одного произведения: нужна одна главная карточка, остальные — издания.
    def work_key(b):
        t = b['title'].replace('ё', 'е').lower()
        return ' '.join(re.sub(r'[«»"“”.,!?…:;—–-]', ' ', t).split())
    groups = collections.defaultdict(list)
    for b in fixed:
        groups[work_key(b)].append(b)
    ed_rows = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        authors = {i['author'] for i in items}
        kind = 'одно произведение, разные издания' if len(authors) == 1 else 'одно название — проверить, одно ли это произведение'
        for i in items:
            ed_rows.append({'group': key, 'kind': kind, 'slug': i['slug'], 'title': i['title'], 'author': i['author'],
                            'age': i['ageLabel'], 'publisher': i.get('publisher') or '',
                            'url': f'https://n-e-n.ru/knigi/kniga/{i["slug"]}/'})

    json.dump(patch, open(os.path.join(outdir, 'catalog-fixes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(fixed, open(os.path.join(outdir, 'catalog-index.fixed.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    for name, data, fields in (
            ('catalog-fixes.csv', rows, ['slug', 'title', 'field', 'old', 'new']),
            ('needs-review.csv', [dict(zip(['slug', 'title', 'what', 'note'], r)) for r in review], ['slug', 'title', 'what', 'note']),
            ('editions.csv', ed_rows, ['group', 'kind', 'slug', 'title', 'author', 'age', 'publisher', 'url'])):
        with open(os.path.join(outdir, name), 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)

    print(f'карточек с правками: {len(patch)} из {len(books)}')
    for k, v in collections.Counter(r['field'] for r in rows).most_common():
        print(f'  {v:5}  {k}')
    print(f'на проверку редакции: {len(review)}; групп изданий: {len({r["group"] for r in ed_rows})} ({len(ed_rows)} карточек)')
    print(f'авторов было {len({b["author"] for b in books})}, стало {len({b["author"] for b in fixed})}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
