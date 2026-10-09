#!/usr/bin/env python3
"""Генератор сервиса «Что почитать с детьми» (n-e-n.ru/knigi/) в виде готового HTML.

  python3 site/build.py            # превью: noindex, обложки с n-e-n.ru, папка docs/
  NEN_PREVIEW=0 python3 site/build.py --out dist   # сборка для боевого сайта

Каждая страница содержит весь текст, ссылки и разметку schema.org прямо в HTML —
JavaScript только улучшает работу (фильтры каталога, подбор книги, избранное).

Данные: site/data/books.json (каталог, см. prepare_data.py), cards/pilot.json и
cards/batches/*.json (тексты карточек), site/content/*.json (подборки, вступления).
"""
import collections, csv, datetime, glob, hashlib, html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEW = os.environ.get('NEN_PREVIEW', '1') != '0'
BASE = '/knigi'                         # путь сервиса на сайте; совпадает с путем на GitHub Pages
ORIGIN = 'https://n-e-n.ru'             # для canonical, og:url и разметки
COVERS = ORIGIN + BASE if PREVIEW else BASE   # для <img>
COVERS_ABS = ORIGIN + BASE                      # для og:image и разметки — всегда полный адрес
# Полный адрес сайта со своими картинками (иллюстрация для соцсетей): в превью — GitHub Pages
SITE_ABS = os.environ.get('NEN_SITE_ABS') or ('https://nancykhacha.github.io/knigi' if PREVIEW else ORIGIN + BASE)
OG_DEFAULT = (SITE_ABS + '/assets/og.jpg', 1200, 630, 'Малыш с игрушкой разглядывает книжку — иллюстрация НЭН')
NO_YO = os.environ.get('NEN_YO', '0') != '1'   # в статьях НЭН пишут без «ё»
PER_PAGE = 48
OUT = os.path.join(ROOT, sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else 'docs')
TODAY = datetime.date.today().isoformat()

MODE = {'together': 'читаем вместе', 'independent': 'читает сам', 'both': 'сам или вместе'}
MODE_LONG = {'together': 'Для чтения со взрослым', 'independent': 'Для самостоятельного чтения',
             'both': 'Можно читать самостоятельно или вместе'}
LENGTH = {'very-short': 'короткая история', 'short': 'на один вечер', 'medium': 'на несколько вечеров',
          'long': 'длинное чтение'}

# Темы и жанры: адрес, заголовок страницы и короткое описание для поиска.
THEMES = {
    'животные': ('pro-zhivotnyh', 'Книги про животных для детей'),
    'семья': ('o-seme', 'Книги о семье для детей'),
    'дружба': ('o-druzhbe', 'Книги о дружбе для детей'),
    'природа': ('o-prirode', 'Книги о природе для детей'),
    'школа': ('pro-shkolu', 'Книги про школу для детей'),
    'волшебство': ('o-volshebstve', 'Книги о волшебстве для детей'),
    'взросление': ('o-vzroslenii', 'Книги о взрослении'),
    'приключения': ('o-priklyucheniyah', 'Книги о приключениях для детей'),
    'братья и сёстры': ('o-bratyah-i-sestrah', 'Книги о братьях и сестрах'),
    'юмор': ('smeshnye', 'Смешные книги для детей'),
    'отношения': ('ob-otnosheniyah', 'Книги об отношениях для подростков'),
    'эмоции': ('pro-emocii', 'Книги про эмоции для детей'),
    'путешествия': ('o-puteshestviyah', 'Книги о путешествиях для детей'),
    'история': ('ob-istorii', 'Книги об истории для детей'),
    'страх': ('pro-strahi', 'Книги про страхи для детей'),
    'детский сад': ('pro-detskiy-sad', 'Книги про детский сад'),
    'творчество': ('o-tvorchestve', 'Книги о творчестве для детей'),
    'космос': ('pro-kosmos', 'Книги про космос для детей'),
    'мифология': ('mify', 'Мифы и легенды для детей'),
    'смелость': ('o-smelosti', 'Книги о смелости для детей'),
    'война': ('o-voyne', 'Книги о войне для детей'),
    'смерть': ('o-smerti', 'Книги о смерти и утрате для детей'),
    'спорт': ('o-sporte', 'Книги о спорте для детей'),
    'самооценка': ('o-samoocenke', 'Книги о самооценке для детей и подростков'),
    'первая любовь': ('o-pervoy-lyubvi', 'Книги о первой любви для подростков'),
    'музыка': ('o-muzyke', 'Книги о музыке для детей'),
    'ответственность': ('ob-otvetstvennosti', 'Книги об ответственности для детей'),
    'экология': ('ob-ekologii', 'Книги об экологии для детей'),
    'театр': ('o-teatre', 'Книги о театре для детей'),
    'динозавры': ('pro-dinozavrov', 'Книги про динозавров для детей'),
    'безопасность': ('o-bezopasnosti', 'Книги о безопасности для детей'),
    'доброта': ('o-dobrote', 'Книги о доброте для детей'),
    'культурное разнообразие': ('o-raznyh-kulturah', 'Книги о разных культурах для детей'),
    'инклюзия': ('ob-inklyuzii', 'Книги об инклюзии для детей'),
    'буллинг': ('o-bullinge', 'Книги о травле для детей и подростков'),
    'принятие себя': ('o-prinyatii-sebya', 'Книги о принятии себя'),
    'наука': ('o-nauke', 'Книги о науке для детей'),
    'изобретения': ('ob-izobreteniyah', 'Книги об изобретениях для детей'),
    'развод родителей': ('o-razvode', 'Книги о разводе родителей для детей'),
    'техника': ('o-tehnike', 'Книги о технике для детей'),
    'тело': ('o-tele', 'Книги о теле для детей'),
    'морские приключения': ('morskie-priklyucheniya', 'Морские приключения для детей'),
    'детектив': ('detektivnye-istorii', 'Детективные истории для детей'),
    'фантастика': ('fantasticheskie-istorii', 'Фантастические истории для детей'),
}
GENRES = {
    'сказка': ('skazki', 'Сказки для детей'),
    'приключения': ('priklyucheniya', 'Приключенческие книги для детей'),
    'юмор': ('yumor', 'Юмористические книги для детей'),
    'реалистическая проза': ('realisticheskaya-proza', 'Реалистическая проза для детей и подростков'),
    'фэнтези': ('fentezi', 'Фэнтези для детей и подростков'),
    'детектив': ('detektivy', 'Детективы для детей'),
    'поэзия': ('stihi', 'Стихи для детей'),
    'научная фантастика': ('nauchnaya-fantastika', 'Научная фантастика для детей и подростков'),
    'семейная история': ('semeynye-istorii', 'Семейные истории для детей'),
    'историческая проза': ('istoricheskaya-proza', 'Историческая проза для подростков'),
    'книжка-картинка': ('knizhki-kartinki', 'Книжки-картинки для малышей'),
}
# Короткие подписи тем и жанров для навигации: «Про эмоции», а не «Книги про эмоции для детей».
THEME_SHORT = {
    'животные': 'Про животных', 'семья': 'О семье', 'дружба': 'О дружбе', 'природа': 'О природе', 'школа': 'Про школу',
    'волшебство': 'О волшебстве', 'взросление': 'О взрослении', 'приключения': 'Приключения',
    'братья и сёстры': 'О братьях и сёстрах', 'юмор': 'Смешные', 'отношения': 'Об отношениях', 'эмоции': 'Про эмоции',
    'путешествия': 'О путешествиях', 'история': 'Об истории', 'страх': 'Про страхи', 'детский сад': 'Про детский сад',
    'творчество': 'О творчестве', 'космос': 'Про космос', 'мифология': 'Мифы и легенды', 'смелость': 'О смелости',
    'война': 'О войне', 'смерть': 'О смерти и утрате', 'спорт': 'О спорте', 'самооценка': 'О самооценке',
    'первая любовь': 'О первой любви', 'музыка': 'О музыке', 'ответственность': 'Об ответственности',
    'экология': 'Об экологии', 'театр': 'О театре', 'динозавры': 'Про динозавров', 'безопасность': 'О безопасности',
    'доброта': 'О доброте', 'культурное разнообразие': 'О разных культурах', 'инклюзия': 'Об инклюзии',
    'буллинг': 'О травле', 'принятие себя': 'О принятии себя', 'наука': 'О науке', 'изобретения': 'Об изобретениях',
    'развод родителей': 'О разводе', 'техника': 'О технике', 'тело': 'О теле', 'морские приключения': 'Морские приключения',
    'детектив': 'Детективные истории', 'фантастика': 'Фантастика',
}
GENRE_SHORT = {
    'сказка': 'Сказки', 'приключения': 'Приключения', 'юмор': 'Юмор', 'реалистическая проза': 'Реалистическая проза',
    'фэнтези': 'Фэнтези', 'детектив': 'Детективы', 'поэзия': 'Стихи', 'научная фантастика': 'Научная фантастика',
    'семейная история': 'Семейные истории', 'историческая проза': 'Историческая проза', 'книжка-картинка': 'Книжки-картинки',
}
# Возрастные вилки — те же, что в возрастных тегах НЭН: 1-2 года, 2-3 года, 3-6 лет, 7-10 лет, подростки.
# (адрес, подпись, от, до, заголовок страницы, крупная цифра на плитке, подпись на плитке)
AGE_BANDS = [
    ('1-2-goda', '1–2 года', 0, 2, 'Книги для детей 1–2 лет', '1–2', 'года'),
    ('2-3-goda', '2–3 года', 2, 3, 'Книги для детей 2–3 лет', '2–3', 'года'),
    ('3-6-let', '3–6 лет', 3, 6, 'Книги для детей 3–6 лет', '3–6', 'лет'),
    ('7-10-let', '7–10 лет', 7, 10, 'Книги для детей 7–10 лет', '7–10', 'лет'),
    ('podrostki', 'Подростки', 11, 20, 'Книги для подростков', '11+', 'лет'),   # подростки в НЭН — до 20 лет
]


def band_of(b):
    """Вилка, с которой у книги больше всего общих лет; при равенстве — младшая."""
    best = max(AGE_BANDS, key=lambda band: (min(b['ageMax'], band[3]) - max(b['ageMin'], band[2]), -band[2]))
    return best


def band_path(band):
    return f'/vozrast/{band[0]}/'


NOT_PEOPLE = re.compile(r'народн|сказк|коллектив|авторы|драматурги|^редакц|^сборник', re.I)
TRANSLIT = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                    ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't',
                     'u', 'f', 'h', 'ts', 'ch', 'sh', 'shch', '', 'y', '', 'e', 'yu', 'ya']))


# ── Текст ────────────────────────────────────────────────────────────────────

def yo(s):
    return s.replace('ё', 'е').replace('Ё', 'Е') if NO_YO and isinstance(s, str) else s


# Неразрывные пробелы: короткие слова не висят в конце строки, тире не переносится в начало,
# число не отрывается от слова («5 лет»), инициалы — от фамилии.
NBSP = '\u00a0'
SHORT_WORDS = re.compile(r'(?<![^\s\u00a0(«„"—])([А-Яа-яЁёA-Za-z]{1,2}|(?i:для|без|под|над|про|при|обо|изо|или|что|как|это|все|его|еще|уже))'
                         r' (?=\S)')
TYPO_RULES = [
    (re.compile(r' (?=[—–] )'), NBSP),                               # «слово — слово»
    (re.compile(r'(?<=\d) (?=[А-Яа-яЁё%])'), NBSP),                   # «5 лет», «48 книг»
    (re.compile(r'(?<=\b[А-ЯЁA-Z]\.) (?=[А-ЯЁA-Z])'), NBSP),            # «А. С. Пушкин»
    (re.compile(r' (?=(?:ли|же|бы|ль)\b)'), NBSP),                     # частицы — к предыдущему слову
    (re.compile(r'(?<=№) '), NBSP),
]


def typo(text):
    """Неразрывные пробелы в обычном тексте (не в HTML)."""
    if not isinstance(text, str):
        return text
    text = SHORT_WORDS.sub(lambda m: m.group(1) + NBSP, text)
    for rx, rep in TYPO_RULES:
        text = rx.sub(rep, text)
    return text


def typo_html(doc):
    """Типографика для текста страницы: только <body>, мимо тегов, скриптов и стилей."""
    head, sep, body = doc.partition('<body')
    parts = re.split(r'(<[^>]+>)', body)
    skip = False
    for i, part in enumerate(parts):
        if part.startswith('<'):
            tag = part[1:].split(None, 1)[0].lower().rstrip('>') if len(part) > 2 else ''
            if tag in ('script', 'style', 'textarea'):
                skip = True
            elif tag in ('/script', '/style', '/textarea'):
                skip = False
        elif part and not skip and i:
            parts[i] = typo(part)
    return head + sep + ''.join(parts)


def e(s):
    """Текст для HTML: «ё» по правилам НЭН и экранирование."""
    return html.escape(yo(str(s)), quote=True)


def slugify(s):
    s = ''.join(TRANSLIT.get(ch, ch) for ch in s.lower())
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')


def age_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return 'год'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'года'
    return 'лет'


def age_gen(n):
    """«для детей 1 года», «для детей 5 лет»."""
    return f'{n} года' if n % 10 == 1 and n % 100 != 11 else f'{n} лет'


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def books_word(n):
    return f'{n} {plural(n, "книга", "книги", "книг")}'


def short(text, limit):
    text = re.sub(r'\s+', ' ', text or '').strip().rstrip('…')
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].rstrip(',;:—-')
    return cut + '…'


def first_sentences(text, limit=150):
    text = re.sub(r'\s+', ' ', text or '').strip()
    out = ''
    for sent in re.split(r'(?<=[.!?…])\s+', text):
        if out and len(out) + len(sent) > limit:
            break
        out = (out + ' ' + sent).strip()
    return short(out, limit + 40)


def url(path):
    return f'{BASE}{path}'


# ── Данные ───────────────────────────────────────────────────────────────────

# Серии издательства, которые попали в название книги: «Книжки-картинки (мягкая обложка). Макс и Лунный Боб».
SERIES_PREFIX = re.compile(r'^(?:Семейные сказки\.\s*)?(?:Книжки-картинки(?: с наклейками)?|Большая сказочная серия|Библиотека приключений|Золотая классика для детей)'
                           r'(?:\s*\(мягкая обложка\))?\.\s+')


def clean_title(t):
    out = re.sub(r'\s*\(мягкая обложка\)', '', SERIES_PREFIX.sub('', t)).strip()
    out = re.sub(r'^(.{3,40}?)\.\s+(\1\b.*)$', r'\2', out)          # «Котенок Шмяк. Котенок Шмяк на фабрике…»
    return out if len(out) >= 3 else t


def removed_slugs():
    """Книги, которые редакция убрала из каталога (fixes/removed.csv)."""
    path = os.path.join(ROOT, 'fixes/removed.csv')
    if not os.path.exists(path):
        return set()
    return {row['slug'] for row in csv.DictReader(open(path, encoding='utf-8-sig'))}


def load():
    removed = removed_slugs()
    books = [b for b in json.load(open(os.path.join(ROOT, 'site/data/books.json'), encoding='utf-8')) if b['slug'] not in removed]
    authors_fix = {}
    path = os.path.join(ROOT, 'fixes/author-fixes.json')
    if os.path.exists(path):
        authors_fix = {k: v for k, v in json.load(open(path, encoding='utf-8')).items() if v.get('confidence') == 'high'}
    nen_ann = {}
    path = os.path.join(ROOT, 'site/content/annotations-nen.json')
    if os.path.exists(path):
        nen_ann = json.load(open(path, encoding='utf-8'))
    cards = {}
    for f in [os.path.join(ROOT, 'cards/pilot.json')] + sorted(glob.glob(os.path.join(ROOT, 'cards/batches/*.json'))):
        for c in json.load(open(f, encoding='utf-8')):
            cards[c['slug']] = c
    for b in books:
        c = cards.get(b['slug'])
        b['card'] = c
        if c:
            b['title'], b['author'], b['ageLabel'] = c.get('title', b['title']), c.get('author', b['author']), c.get('ageLabel', b['ageLabel'])
            if 'suitableForBedtime' in c:
                b['suitableForBedtime'] = c['suitableForBedtime']
            # Возраст, предложенный автором карточки, точнее каталожного (часто стоит «7–12 лет» по умолчанию).
            sug = (c.get('ageSuggestion') or {}).get('label', '')
            m = re.match(r'\s*(\d+)\s*[–-]\s*(\d+)', sug) or re.match(r'\s*(\d+)\s*\+', sug)
            if m:
                lo = int(m.group(1))
                hi = int(m.group(2)) if m.lastindex == 2 else max(lo, 20)
                b['ageCatalog'] = b['ageLabel']
                b['ageMin'], b['ageMax'] = lo, hi
                if m.lastindex == 1:
                    b['ageLabel'] = f'{lo}+'
                else:
                    b['ageLabel'] = f'{lo}–{hi} {age_word(hi)}' if lo != hi else f'{hi} {age_word(hi)}'
        if clean_title(b['title']) != b['title']:
            b['catalogTitle'], b['title'] = b['title'], clean_title(b['title'])
        b['snippet'] = first_sentences(c['about']) if c else short(b.get('shortDescription', ''), 160)
        fix = authors_fix.get(b['slug'])
        if fix:
            b['author'] = fix['author']
            for k in ('illustrator', 'translator', 'reteller', 'compiler'):
                if fix.get(k) and not b.get(k):
                    b[k] = fix[k]
        if b['slug'] in nen_ann:
            b['annotation'], b['annotationSource'], b['annotationByNen'] = nen_ann[b['slug']]['annotation'], 'Текст редакции НЭН', True
        b['adult'] = b['ageMin'] >= 18          # 18+: подростковая вилка НЭН (до 20 лет), но свой блок «перед чтением»
        b['rank'] = (0 if c and c.get('source', '').startswith('knowledge') else 1 if c else 2)
        b['url'] = url(f'/kniga/{b["slug"]}/')
        b['authors'] = [a.strip() for a in re.split(r'\s*;\s*', b['author']) if a.strip()]
    collections_ = json.load(open(os.path.join(ROOT, 'site/content/collections.json'), encoding='utf-8'))
    landings_path = os.path.join(ROOT, 'site/content/landings.json')
    landings = json.load(open(landings_path, encoding='utf-8')) if os.path.exists(landings_path) else {}
    for name, target in (('nen-articles.json', NEN_ARTICLES), ('nen-reading.json', NEN_READING)):
        path = os.path.join(ROOT, 'site/content', name)
        if os.path.exists(path):
            target.update(json.load(open(path, encoding='utf-8')))
    return books, collections_, landings


def book_title(b):
    c = b.get('card') or {}
    return c.get('seoTitle') or (f'«{b["title"]}», {b["author"]} — о чём книга и с какого возраста | НЭН'
                                 if len(b['title']) + len(b['author']) < 30 else f'«{short(b["title"], 40)}» — книга для детей {b["ageMin"]}–{b["ageMax"]} лет | НЭН')


def editions(books):
    """Издания одной книги: одно название и общий автор или одинаковый заголовок страницы.
    Основное издание — то, что мы знаем лучше и что в твердой обложке; у остальных canonical на него."""
    def norm(s):
        return re.sub(r'\s+', ' ', re.sub(r'[^\w ]+', ' ', yo(s).lower())).strip()
    parent = list(range(len(books)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    by_key = collections.defaultdict(list)
    for i, b in enumerate(books):
        by_key[('t', norm(b['title']))].append(i)
        by_key[('s', norm(book_title(b)))].append(i)
    for (kind, _), idx in by_key.items():
        for i in idx[1:]:
            a, o = books[idx[0]], books[i]
            words = lambda x: {w for w in norm(x['author']).split() if len(w) > 2}
            if kind == 's' or words(a) & words(o) or not (words(a) and words(o)):
                parent[find(i)] = find(idx[0])
    groups = collections.defaultdict(list)
    for i in range(len(books)):
        groups[find(i)].append(books[i])
    n = 0
    for g in groups.values():
        if len(g) < 2:
            continue
        g.sort(key=lambda b: (b['rank'], bool(re.search(r'myagkaya-oblozhka|paperback|vneklassnoe|podarochnoe', b['slug'])),
                              bool(b.get('editionNote')), len(b['slug'])))
        main = g[0]
        main['otherEditions'] = g[1:]
        for b in g[1:]:
            b['mainEdition'] = main
            n += 1
    return n


def similar(books):
    """Похожие книги: общие темы и жанры, пересечение по возрасту, другой автор."""
    by_theme = collections.defaultdict(set)
    for i, b in enumerate(books):
        for t in b.get('themes', []):
            by_theme[t].add(i)
    for i, b in enumerate(books):
        cand = set().union(*(by_theme[t] for t in b.get('themes', []))) if b.get('themes') else set()
        scored = []
        for j in cand:
            if j == i or books[j].get('mainEdition'):
                continue
            o = books[j]
            overlap = min(b['ageMax'], o['ageMax']) - max(b['ageMin'], o['ageMin'])
            if overlap < 0:
                continue
            score = 2 * len(set(b.get('themes', [])) & set(o.get('themes', []))) + len(set(b.get('genres', [])) & set(o.get('genres', [])))
            score += 1.5 if o['card'] else 0
            score -= 3 if set(o['authors']) & set(b['authors']) else 0
            scored.append((-score, o['rank'], o['title'], j))
        b['similar'] = [books[j] for *_, j in sorted(scored)[:4]]


# ── Разметка ─────────────────────────────────────────────────────────────────

def ld(obj):
    return '<script type="application/ld+json">' + yo(json.dumps(obj, ensure_ascii=False)).replace('</', '<\\/') + '</script>'


def breadcrumbs(items):
    """items: [(name, path|None)]"""
    lis = ''.join(f'<li><a href="{url(p)}">{e(n)}</a></li>' if p else f'<li aria-current="page">{e(n)}</li>' for n, p in items)
    data = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, **({'item': ORIGIN + url(p)} if p else {})}
        for i, (n, p) in enumerate(items)]}
    return f'<nav class="crumbs wrap" aria-label="Навигация"><ol>{lis}</ol></nav>', data


def item_list(books, name):
    return {'@type': 'ItemList', 'name': name, 'numberOfItems': len(books), 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'url': ORIGIN + b['url'], 'name': b['title']} for i, b in enumerate(books)]}


NEN_LINKS = [('Журнал «Нет, это нормально»', 'https://n-e-n.ru/'), ('Развитие ребенка', 'https://n-e-n.ru/razvitie/'),
             ('Эксперты НЭН', 'https://n-e-n.ru/eksperty/'), ('Генератор имен', 'https://n-e-n.ru/imena/'),
             ('Раскраска «Акварель»', 'https://n-e-n.ru/aquarelle/'), ('Тесты', 'https://n-e-n.ru/quizes/')]
NEN_SOCIAL = [('Телеграм', 'https://t.me/net_etonorm'), ('ВКонтакте', 'https://vk.com/net_eto_normalno'),
              ('Дзен', 'https://dzen.ru/nenru'), ('YouTube', 'https://www.youtube.com/@netetonorm'),
              ('Одноклассники', 'https://ok.ru/netetonorm')]
NEN_ORG = {'@type': 'Organization', '@id': 'https://n-e-n.ru/#organization', 'name': 'Нет, это нормально', 'alternateName': 'НЭН',
           'url': 'https://n-e-n.ru/', 'logo': {'@type': 'ImageObject', 'url': 'https://n-e-n.ru/img/nen_logo.png', 'width': 162, 'height': 74},
           'sameAs': [h for _, h in NEN_SOCIAL]}

TABBAR = [('Каталог', '/katalog/'), ('Подборки', '/podborki/'), ('Возраст', '/vozrast/'), ('Темы', '/tema/'), ('Найти книгу', '/podbor/')]
NAV = [('Каталог', '/katalog/'), ('Подборки', '/podborki/'), ('По возрасту', '/vozrast/'), ('Темы', '/tema/'),
       ('Подобрать книгу', '/podbor/'), ('Избранное', '/izbrannoe/')]


def page(path, title, description, body, *, schema=(), og_type='website', image=None, active=None, noindex=False, canonical=None):
    canonical = ORIGIN + url(canonical or path)
    robots = 'noindex, nofollow' if PREVIEW or noindex else 'index, follow, max-image-preview:large, max-snippet:-1'
    nav = ''.join(f'<a href="{url(p)}"{" aria-current=page" if p == active else ""}>{e(n)}</a>' for n, p in NAV)
    tabbar = ''.join(f'<a href="{url(p)}"{" aria-current=page" if p == active else ""}>{e(n)}</a>' for n, p in TABBAR)
    if image:
        og_image = f'<meta property="og:image" content="{e(image)}">\n<meta name="twitter:image" content="{e(image)}">'
        card = 'summary'
    else:
        src, w, h, alt = OG_DEFAULT
        og_image = (f'<meta property="og:image" content="{e(src)}">\n<meta property="og:image:width" content="{w}">\n'
                    f'<meta property="og:image:height" content="{h}">\n<meta property="og:image:alt" content="{e(alt)}">\n'
                    f'<meta name="twitter:image" content="{e(src)}">')
        card = 'summary_large_image'
    preview = ('<div class="preview-bar">Рабочая версия для разработки. Сервис живет на '
               '<a href="https://n-e-n.ru/knigi/">n-e-n.ru/knigi</a></div>') if PREVIEW else ''
    graph = [s for s in schema if s]
    schema_html = ld({'@context': 'https://schema.org', '@graph': graph}) if graph else ''
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta name="robots" content="{robots}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="НЭН">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
{og_image}
<meta name="twitter:card" content="{card}">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&family=Unbounded:wght@500;600;700&display=swap">
<link rel="stylesheet" href="{url('/assets/nen.css')}?v={ASSET_VERSION}">
<link rel="icon" href="https://n-e-n.ru/img/favicons/favicon.svg" type="image/svg+xml">
{schema_html}
</head>
<body data-base="{BASE}">
{preview}
<header class="header"><div class="wrap">
<a class="wordmark" href="{url('/')}">НЭН<small>{e('Что почитать с детьми')}</small></a>
<nav class="nav" aria-label="Разделы сервиса">{nav}</nav>
<a class="header-fav" href="{url('/izbrannoe/')}">Избранное</a>
</div></header>
<nav class="tabbar" aria-label="Разделы сервиса">{tabbar}</nav>
<main>
{body}
</main>
<footer class="footer"><div class="wrap">
<div><h2>{e('Что почитать с детьми')}</h2><p>{e('Книжные рекомендации редакции НЭН: для каждой книги объясняем, кому она подойдет, что важно знать родителям и о чём поговорить после чтения.')}</p></div>
<div><h2>Разделы</h2><ul>{''.join(f'<li><a href="{url(p)}">{e(n)}</a></li>' for n, p in NAV[:5])}</ul></div>
<div><h2>НЭН</h2><ul>{''.join(f'<li><a href="{h}">{e(n)}</a></li>' for n, h in NEN_LINKS)}</ul></div>
<div><h2>{e('НЭН в соцсетях')}</h2><ul>{''.join(f'<li><a href="{h}" rel="noopener">{e(n)}</a></li>' for n, h in NEN_SOCIAL)}</ul></div>
</div></footer>
<script src="{url('/assets/app.js')}?v={ASSET_VERSION}" defer></script>
</body>
</html>
'''


def cover_img(b, cls='', eager=False, size=(240, 320)):
    if not b.get('cover'):
        return f'<div class="{cls}" aria-hidden="true"></div>'
    loading = ' fetchpriority="high"' if eager else ' loading="lazy"'
    return (f'<div class="{cls}"><img src="{e(COVERS + b["cover"])}" alt="{e("Обложка книги «" + b["title"] + "»")}" '
            f'width="{size[0]}" height="{size[1]}"{loading} decoding="async"></div>')


def book_tags(b, link_age=False):
    if link_age:
        out = [f'<a class="tag tag-blue" href="{url(band_path(band_of(b)))}" title="{e(band_of(b)[4])}">{e(b["ageLabel"])}</a>']
    else:
        out = [f'<span class="tag tag-blue">{e(b["ageLabel"])}</span>']
    if b.get('readingMode') in MODE:
        out.append(f'<span class="tag tag-pink">{e(MODE[b["readingMode"]])}</span>')
    if b.get('suitableForBedtime'):
        out.append('<span class="tag tag-yellow">перед сном</span>')
    return '<div class="tags">' + ''.join(out) + '</div>'


def book_card(b):
    return (f'<article class="card book-card">{cover_img(b, "cover")}'
            f'<h3 class="title"><a href="{b["url"]}">{e(b["title"])}</a></h3>'
            f'<p class="author">{e(b["author"])}</p>'
            f'<p class="snippet">{e(b["snippet"])}</p>{book_tags(b)}</article>')


def book_grid(books):
    return '<div class="grid grid-4">' + ''.join(book_card(b) for b in books) + '</div>'


def pager(base_path, n_pages, current):
    if n_pages < 2:
        return ''
    links = []
    for p in range(1, n_pages + 1):
        href = url(base_path if p == 1 else f'{base_path}{p}/')
        links.append(f'<span aria-current="page">{p}</span>' if p == current else f'<a href="{href}">{p}</a>')
    return '<nav class="pager" aria-label="Страницы">' + ''.join(links) + '</nav>'


# ── Страницы ─────────────────────────────────────────────────────────────────

WRITTEN = []


def write(path, content):
    target = os.path.join(OUT, path.strip('/'), 'index.html') if path.endswith('/') else os.path.join(OUT, path.strip('/'))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w', encoding='utf-8') as f:
        f.write(typo_html(yo(content)) if target.endswith('.html') else yo(content))
    if path.endswith('/'):
        WRITTEN.append(path)


def edition_kind(b):
    if re.search(r'myagkaya-oblozhka|paperback', b['slug']) or 'мягкая обложка' in b.get('catalogTitle', ''):
        return 'мягкая обложка'
    if 'podarochnoe' in b['slug']:
        return 'подарочное издание'
    return ''


def edition_label(b):
    parts = [b.get('publisher'), str(b.get('publicationYear') or ''), b.get('editionNote') or edition_kind(b)]
    label = ', '.join(x for x in parts if x) or b['title']
    return short(label, 60)


def render_book(b, in_collections):
    c = b.get('card') or {}
    crumbs_html, crumbs_ld = breadcrumbs([('Что почитать с детьми', '/'), ('Каталог', '/katalog/'), (b['title'], None)])
    facts = [('Возраст', b['ageLabel'])]
    if b.get('readingMode') in MODE_LONG:
        facts.append(('Формат', MODE_LONG[b['readingMode']]))
    vol = ' · '.join(x for x in [LENGTH.get(b.get('lengthCategory'), ''), f'{b["pages"]} стр.' if b.get('pages') else ''] if x)
    if vol:
        facts.append(('Объем', vol))
    if b.get('publisher'):
        facts.append(('Издательство', b['publisher'] + (f', {b["publicationYear"]}' if b.get('publicationYear') else '')))
    for key, label in (('reteller', 'Пересказ'), ('compiler', 'Составитель'), ('illustrator', 'Художник'), ('translator', 'Перевод')):
        if b.get(key):
            facts.append((label, b[key]))
    if b.get('editionNote'):
        facts.append(('Издание', b['editionNote']))
    if b.get('seriesName') and not re.search(r'вне серий|^книжки-картинки', b['seriesName'], re.I):
        facts.append(('Серия', b['seriesName'] + (f' · книга {b["seriesNumber"]}' if b.get('seriesNumber') else '')))
    if b.get('isbn13'):
        facts.append(('ISBN', b['isbn13']))
    facts_html = '<dl class="facts">' + ''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in facts) + '</dl>'

    authors_html = ', '.join(
        f'<a href="{url("/avtor/" + slugify(a) + "/")}">{e(a)}</a>' if a in AUTHOR_PAGES else e(a) for a in b['authors'])
    blocks = []
    if c:
        blocks.append(f'<section class="block"><h2 class="h3">О чём книга</h2><div class="prose"><p>{e(c["about"])}</p></div></section>')
        blocks.append(f'<section class="block"><h2 class="h3">Почему советуем</h2><div class="prose"><p>{e(c["whyRecommended"])}</p></div></section>')
        blocks.append(f'<section class="plate plate-care"><h2 class="h3">{"Что важно знать перед чтением" if b["adult"] else "Что важно знать родителям"}</h2><p class="body">{e(c["parentsNote"])}</p></section>')
        qs = ''.join(f'<li>{e(q)}</li>' for q in c['discussionQuestions'])
        blocks.append(f'<section class="plate plate-community"><h2 class="h3">О чём поговорить после чтения</h2><ol class="questions">{qs}</ol></section>')
    else:
        if b.get('shortDescription'):
            blocks.append(f'<section class="block"><h2 class="h3">О чём книга</h2><div class="prose"><p>{e(b["shortDescription"])}</p></div></section>')
        if b.get('whyRecommended'):
            blocks.append(f'<section class="block"><h2 class="h3">Почему советуем</h2><div class="prose"><p>{e(b["whyRecommended"])}</p></div></section>')
    if b.get('annotation'):
        paras = ''.join(f'<p>{e(p)}</p>' for p in re.split(r'\n+', b['annotation']) if p.strip())
        source = f'<p class="meta">Источник: {e(b["annotationSource"])}</p>' if b.get('annotationSource') else ''
        blocks.append(f'<details class="annotation"><summary>{"Аннотация" if b.get("annotationByNen") else "Аннотация издательства"}</summary><div class="prose">{paras}</div>{source}</details>')

    links = []
    for t in b.get('themes', []):
        if t in THEME_PAGES:
            links.append(f'<a class="chip" href="{url("/tema/" + THEMES[t][0] + "/")}">{e(THEME_SHORT.get(t, t))}</a>')
    for g in b.get('genres', []):
        if g in GENRE_PAGES:
            links.append(f'<a class="chip" href="{url("/zhanr/" + GENRES[g][0] + "/")}">{e(GENRE_SHORT.get(g, g))}</a>')
    band = band_of(b)
    links.append(f'<a class="chip" href="{url(band_path(band))}">{e(band[4])}</a>')
    if links:
        blocks.append('<section class="block"><h2 class="h3">Темы и жанры</h2><div class="chips">' + ''.join(links) + '</div></section>')
    if b.get('otherEditions') or b.get('mainEdition'):
        main_ed = b.get('mainEdition') or b
        eds = [main_ed] + main_ed.get('otherEditions', [])
        items = ''.join(f'<a class="chip" href="{x["url"]}">{e(edition_label(x))}</a>' for x in eds if x is not b)
        lead = ('Это одно из изданий книги. Главная страница с рекомендацией — '
                f'<a href="{main_ed["url"]}">«{e(main_ed["title"])}»</a>.') if b.get('mainEdition') else 'В каталоге есть и другие издания этой книги.'
        blocks.append(f'<section class="block"><h2 class="h3">Другие издания</h2><p class="body">{lead}</p><div class="chips">{items}</div></section>')
    arts = list(NEN_ARTICLES.get(b['slug'], []))
    for x in [b.get('mainEdition')] + (b.get('otherEditions') or []) + (b['mainEdition'].get('otherEditions', []) if b.get('mainEdition') else []):
        for a in NEN_ARTICLES.get(x['slug'], []) if x else []:
            if a['url'] not in {y['url'] for y in arts}:
                arts.append(a)
    if arts:
        items = ''.join(f'<li><a href="{e(a["url"])}">{e(a["title"])}</a><span class="meta">{e(" · ".join(x for x in (a.get("section"), ru_date(a.get("date"))) if x and x != "Без рубрики"))}</span></li>'
                        for a in arts[:3])
        blocks.append(f'<section class="block"><h2 class="h3">Книга в статьях НЭН</h2><ul class="reads">{items}</ul></section>')
    if in_collections:
        items = ''.join(f'<a class="chip" href="{url("/podborki/" + col["slug"] + "/")}">{e(col["title"])}</a>' for col in in_collections)
        blocks.append(f'<section class="block"><h2 class="h3">Книга в подборках НЭН</h2><div class="chips">{items}</div></section>')

    sim = f'<section class="section wrap"><div class="section-head"><h2 class="h2">Похожие книги</h2></div>{book_grid(b["similar"])}</section>' if b.get('similar') else ''
    body = f'''{crumbs_html}
<div class="wrap"><article class="book">
<aside class="book-aside">{cover_img(b, "book-cover", eager=True, size=(280, 373))}<p class="cover-credit">Обложка предоставлена издательством.</p>
<button class="fav" type="button" data-fav="{b["slug"]}" aria-pressed="false">Сохранить в избранное</button>{facts_html}</aside>
<div class="book-main">
<header class="book-head"><span class="eyebrow">{e("Возрастная рекомендация НЭН · " + b["ageLabel"])}</span>
<h1 class="h1">{e(b["title"])}</h1><p class="author">{authors_html}</p>{book_tags(b, link_age=True)}</header>
{''.join(blocks)}
</div></article></div>
{sim}<div class="page-end"></div>'''

    main_ed = b.get('mainEdition')
    title = book_title(b)
    if main_ed:
        hint = short(b.get('editionNote') or edition_kind(b) or ', '.join(x for x in (b.get('publisher'), str(b.get('publicationYear') or '')) if x) or 'другое издание', 24)
        title = f'«{short(b["title"], 64 - len(hint) - 9)}» — {hint} | НЭН'
    desc = c.get('seoDescription') or short(f'Для детей {b["ageMin"]}–{b["ageMax"]} лет. {b.get("shortDescription", "")}', 160)
    book_ld = {'@type': 'Book', '@id': ORIGIN + b['url'] + '#book', 'url': ORIGIN + b['url'], 'name': b['title'],
               'author': [{'@type': 'Person' if not NOT_PEOPLE.search(a) else 'Organization', 'name': a} for a in b['authors']],
               'inLanguage': 'ru', 'typicalAgeRange': '18-' if b['adult'] else f'{b["ageMin"]}-{b["ageMax"]}',
               'description': c.get('about') or b.get('shortDescription', '')}
    for k, v in (('alternateName', b.get('originalTitle')), ('isbn', b.get('isbn13')), ('numberOfPages', b.get('pages')),
                 ('genre', ', '.join(b.get('genres', [])) or None), ('translator', {'@type': 'Person', 'name': b['translator']} if b.get('translator') else None),
                 ('publisher', {'@type': 'Organization', 'name': b['publisher']} if b.get('publisher') else None),
                 ('image', COVERS_ABS + b['cover'] if b.get('cover') else None)):
        if v:
            book_ld[k] = v
    write(f'/kniga/{b["slug"]}/', page(f'/kniga/{b["slug"]}/', title, desc, body, schema=[book_ld, crumbs_ld], og_type='book',
                                      image=(COVERS_ABS + b['cover']) if b.get('cover') else None, active=None,
                                      canonical=f'/kniga/{main_ed["slug"]}/' if main_ed else None))


MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']


def ru_date(iso):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', iso or '')
    return f'{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]} {m.group(1)}' if m else ''


def nen_reading(path):
    """Подборки журнала НЭН по теме страницы (site/content/nen-reading.json)."""
    arts = NEN_READING.get(path)
    if not arts:
        return ''
    cards = ''.join(f'<article class="text-card"><span class="num">{e(ru_date(a["date"]) or "НЭН")}</span>'
                    f'<h3><a href="{e(a["url"])}">{e(a["title"])}</a></h3></article>' for a in arts)
    return (f'<section class="section wrap"><div class="section-head"><h2 class="h2">Читайте в журнале НЭН</h2></div>'
            f'<div class="grid grid-3">{cards}</div></section>')


def render_list(path, crumbs, h1, title, description, intro_html, books, *, faq=None, extra_top='', active=None, related=''):
    n_pages = max(1, -(-len(books) // PER_PAGE))
    crumbs_html, crumbs_ld = breadcrumbs(crumbs)
    for p in range(1, n_pages + 1):
        part = books[(p - 1) * PER_PAGE:p * PER_PAGE]
        sub = path if p == 1 else f'{path}{p}/'
        h1_p = h1 if p == 1 else f'{h1} · страница {p}'
        faq_html = ''
        faq_ld = None
        if faq and p == 1:
            faq_html = ('<section class="section wrap"><h2 class="h2">Вопросы и ответы</h2><div class="faq" style="margin-top:20px">' +
                        ''.join(f'<details><summary>{e(q["q"])}</summary><p>{e(q["a"])}</p></details>' for q in faq) + '</div></section>')
            faq_ld = {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': q['a']}} for q in faq]}
        body = f'''{crumbs_html}
<div class="wrap"><header class="list-head"><span class="eyebrow">{e(books_word(len(books)))}</span><h1 class="h1">{e(h1_p)}</h1>
{intro_html if p == 1 else ''}</header>{extra_top if p == 1 else ''}
<div class="results-meta"><span class="meta">{e(f"Показаны {(p - 1) * PER_PAGE + 1}–{(p - 1) * PER_PAGE + len(part)} из {len(books)}")}</span></div>
{book_grid(part)}{pager(path, n_pages, p)}</div>
{related if p == 1 else ''}{nen_reading(path) if p == 1 else ''}{faq_html}<div class="page-end"></div>'''
        coll = {'@type': 'CollectionPage', 'url': ORIGIN + url(sub), 'name': h1_p, 'description': description,
                'mainEntity': item_list(part, h1_p)}
        write(sub, page(sub, title if p == 1 else f'{h1} — страница {p} | НЭН',
                        description if p == 1 else f'{short(description, 135)} Страница {p} из {n_pages}.', body,
                        schema=[coll, crumbs_ld, faq_ld], active=active))


def intro(landing, fallback):
    paras = (landing or {}).get('intro') or fallback
    if isinstance(paras, str):
        paras = [paras]
    return '<div class="intro">' + ''.join(f'<p>{e(p)}</p>' for p in paras) + '</div>'


def main():
    global ASSET_VERSION, AUTHOR_PAGES, THEME_PAGES, GENRE_PAGES, AGE_PAGES
    books, cols, landings = load()
    by_slug = {b['slug']: b for b in books}
    n_editions = editions(books)
    listed = [b for b in books if not b.get('mainEdition')]   # в тематических списках — только основное издание
    similar(books)

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ROOT, 'site/assets'), os.path.join(OUT, 'assets'))
    ASSET_VERSION = hashlib.md5(b''.join(open(f, 'rb').read() for f in sorted(glob.glob(os.path.join(OUT, 'assets/*'))))).hexdigest()[:8]

    ordered = sorted(books, key=lambda b: (b['rank'], b['title']))
    themes = collections.Counter(t for b in listed for t in b.get('themes', []))
    genres = collections.Counter(g for b in listed for g in b.get('genres', []))
    THEME_PAGES = {t for t, n in themes.items() if n >= 8 and t in THEMES}
    GENRE_PAGES = {g for g, n in genres.items() if n >= 8 and g in GENRES}
    authors = collections.Counter(a for b in listed for a in b['authors'] if not NOT_PEOPLE.search(a))
    AUTHOR_PAGES = {a for a, n in authors.items() if n >= 3}
    AGE_PAGES = {a: f'/vozrast/{a}-{slugify(age_word(a))}/' for a in range(1, 15)}

    # Карточки книг
    in_cols = collections.defaultdict(list)
    for col in cols:
        for s in col['books']:
            in_cols[s].append(col)
    for b in books:
        render_book(b, in_cols.get(b['slug'], []))

    # По возрасту: вилки, как в возрастных тегах НЭН, и уточнение по годам внутри вилки
    band_counts = {}
    for band in AGE_BANDS:
        slug, label, lo, hi, h1, big, small = band
        sel = [b for b in listed if b['ageMin'] <= hi and b['ageMax'] >= lo]
        def fit(b, lo=lo, hi=hi):
            span = b['ageMax'] - b['ageMin'] + 1
            inside = min(b['ageMax'], hi) - max(b['ageMin'], lo) + 1
            return inside / span
        sel.sort(key=lambda b: (b['rank'], -round(fit(b), 1), b['ageMin'], b['title']))
        band_counts[slug] = len(sel)
        path = band_path(band)
        land = landings.get(path, {})
        years = [a for a in range(max(lo, 1), min(hi, 14) + 1)]
        year_chips = ''.join(f'<a class="chip" href="{url(AGE_PAGES[a])}">{e(f"{a} {age_word(a)}")}</a>' for a in years)
        other = ''.join(f'<a class="chip" href="{url(band_path(x))}">{e(x[1])}</a>' for x in AGE_BANDS if x is not band)
        related = (f'<section class="section wrap"><h2 class="h3">Уточнить возраст</h2><div class="chips" style="margin-top:12px">{year_chips}</div>'
                   f'<h2 class="h3" style="margin-top:24px">Другие возрасты</h2><div class="chips" style="margin-top:12px">{other}</div></section>')
        render_list(path, [('Что почитать с детьми', '/'), ('По возрасту', '/vozrast/'), (land.get('h1') or h1, None)], land.get('h1') or h1,
                    land.get('title') or f'{h1}: что почитать — рекомендации НЭН',
                    land.get('description') or short(f'{h1}: {books_word(len(sel))} с рекомендациями редакции НЭН — о чём книга, почему советуем и о чём поговорить после чтения.', 160),
                    intro(land, f'Книги, которые подходят детям {label}. Первыми идут те, что мы знаем и советуем лучше всего.' if slug != 'podrostki' else
                          'Книги для подростков от 11 до 20 лет — так подростковый возраст определяют в НЭН. Книги для самых старших отмечены пометкой 18+. '
                          'Первыми идут те, что мы знаем и советуем лучше всего.'),
                    sel, faq=land.get('faq'), active='/vozrast/', related=related)

    age_counts = {}
    for a in range(1, 15):
        sel = [b for b in listed if b['ageMin'] <= a <= b['ageMax']]
        sel.sort(key=lambda b: (b['rank'], abs((b['ageMin'] + b['ageMax']) / 2 - a) + 0.2 * (b['ageMax'] - b['ageMin']), b['title']))
        age_counts[a] = len(sel)
        path = AGE_PAGES[a]
        land = landings.get(path, {})
        h1 = land.get('h1') or f'Книги для детей {age_gen(a)}'
        neighbours = ''.join(f'<a class="chip" href="{url(AGE_PAGES[x])}">{e(str(x) + " " + age_word(x))}</a>'
                             for x in (a - 2, a - 1, a + 1, a + 2) if x in AGE_PAGES)
        related = f'<section class="section wrap"><h2 class="h3">Соседние возрасты</h2><div class="chips" style="margin-top:12px">{neighbours}</div></section>'
        band = AGE_BANDS[0] if a < 2 else AGE_BANDS[1] if a < 3 else AGE_BANDS[2] if a <= 6 else AGE_BANDS[3] if a <= 10 else AGE_BANDS[4]
        render_list(path, [('Что почитать с детьми', '/'), ('По возрасту', '/vozrast/'), (band[4], band_path(band)), (h1, None)], h1,
                    land.get('title') or f'{h1}: что почитать — рекомендации НЭН',
                    land.get('description') or f'Что почитать ребенку в {a} {age_word(a)}: {books_word(len(sel))} с рекомендациями редакции НЭН — о чём книга, почему советуем и о чём поговорить после чтения.',
                    intro(land, f'Мы собрали книги, которые подходят детям в {a} {age_word(a)}. Для каждой есть короткое описание, объяснение, почему мы ее советуем, и вопросы для разговора после чтения.'),
                    sel, faq=land.get('faq'), active='/vozrast/', related=related)

    # Темы и жанры
    for kind, table, pages_set, field, prefix, crumb in (('tema', THEMES, THEME_PAGES, 'themes', '/tema/', 'Темы'),
                                                        ('zhanr', GENRES, GENRE_PAGES, 'genres', '/zhanr/', 'Темы')):
        for key in sorted(pages_set):
            slug, h1 = table[key]
            path = f'{prefix}{slug}/'
            land = landings.get(path, {})
            sel = sorted((b for b in listed if key in b.get(field, [])), key=lambda b: (b['rank'], b['ageMin'], b['title']))
            render_list(path, [('Что почитать с детьми', '/'), (crumb, '/tema/'), (land.get('h1') or h1, None)], land.get('h1') or h1,
                        land.get('title') or f'{h1}: что почитать — рекомендации НЭН',
                        land.get('description') or short(f'{h1}: {books_word(len(sel))} для разного возраста с рекомендациями редакции НЭН — о чём книга, почему советуем и о чём поговорить после чтения.', 160),
                        intro(land, f'{books_word(len(sel)).capitalize()} из каталога НЭН. Выбирайте по возрасту: он указан на каждой обложке, а в карточке книги мы объясняем, кому она подойдет и что важно знать родителям.'),
                        sel, faq=land.get('faq'), active='/tema/')

    # Перед сном
    bed = sorted((b for b in listed if b.get('suitableForBedtime')), key=lambda b: (b['rank'], b['ageMin'], b['title']))
    land = landings.get('/pered-snom/', {})
    render_list('/pered-snom/', [('Что почитать с детьми', '/'), ('Книги перед сном', None)], land.get('h1') or 'Книги для чтения перед сном',
                land.get('title') or 'Книги для чтения перед сном: спокойные истории для детей | НЭН',
                land.get('description') or f'Спокойные книги для вечернего чтения: {books_word(len(bed))} для детей разного возраста с рекомендациями редакции НЭН.',
                intro(land, 'Спокойные истории без страшных поворотов, которые хорошо читать вечером. Многие из них короткие — можно читать по одной главе или сказке за вечер.'),
                bed, faq=land.get('faq'), active=None)

    # Авторы
    for a in sorted(AUTHOR_PAGES):
        sel = sorted((b for b in listed if a in b['authors']), key=lambda b: (b['ageMin'], b['title']))
        path = f'/avtor/{slugify(a)}/'
        title = next(t for t in (f'{a} — книги для детей: что почитать и с какого возраста | НЭН',
                                 f'{a}: книги для детей и с какого возраста | НЭН', f'{a}: книги для детей | НЭН') if len(t) <= 70 or t.endswith('детей | НЭН'))
        lo, hi = min(b['ageMin'] for b in sel), max(b['ageMax'] for b in sel)
        ages = f'Они подойдут читателям {lo}–{hi} {age_word(hi)}' if hi > 17 else f'Они подойдут детям {lo}–{hi} {age_word(hi)}'
        names = [f'«{b["title"]}»' for b in sel[:4]]
        listing = (', '.join(names[:-1]) + ' и ' + names[-1]) if len(names) > 1 else names[0]
        top = [THEME_SHORT.get(t, t).lower() for t, _ in collections.Counter(t for b in sel for t in b.get('themes', [])).most_common(3)]
        fallback = [f'{a}: {books_word(len(sel))} в каталоге НЭН — {listing}{" и другие" if len(sel) > 4 else ""}. ' +
                    ages + (f', а главные темы — {", ".join(top)}.' if top else '.'),
                    'Книги отсортированы по возрасту — от младших читателей к старшим. В карточке каждой мы рассказываем, о чём книга, '
                    'почему мы ее советуем, что важно знать родителям и о чём поговорить с ребенком после чтения.']
        render_list(path, [('Что почитать с детьми', '/'), ('Авторы', '/avtor/'), (a, None)], f'{a}: книги для детей', title,
                    short(f'{a}: {books_word(len(sel))} в каталоге НЭН для {"читателей" if hi > 17 else "детей"} {lo}–{hi} {age_word(hi)} — о чём каждая книга, с какого возраста читать и почему мы ее советуем.', 160),
                    intro(landings.get(path), fallback), sel, active=None)

    # Подборки
    for col in cols:
        sel = [by_slug[s] for s in col['books'] if s in by_slug]
        path = f'/podborki/{col["slug"]}/'
        crumbs_html, crumbs_ld = breadcrumbs([('Что почитать с детьми', '/'), ('Подборки', '/podborki/'), (col['title'], None)])
        items = ''.join(
            f'<article class="text-card"><span class="num">{i + 1:02d}</span><h3><a href="{b["url"]}">{e(b["title"])}</a></h3>'
            f'<p class="meta">{e(b["author"] + " · " + b["ageLabel"])}</p><p>{e((b.get("card") or {}).get("whyRecommended") or b["snippet"])}</p></article>'
            for i, b in enumerate(sel))
        source = f'<p class="meta">Подборка основана на статье НЭН: <a href="{e(col["sourceUrl"])}">{e(col["sourceUrl"].replace("https://", ""))}</a> · обновлено {e(col["updatedAt"])}</p>' if col.get('sourceUrl') else ''
        body = f'''{crumbs_html}<div class="wrap"><header class="list-head"><span class="eyebrow">{e(col["ageLabel"] + " · " + books_word(len(sel)))}</span>
<h1 class="h1">{e(col["title"])}</h1><div class="intro"><p>{e(col["description"])}</p><p>{e(col["introduction"])}</p></div>{source}</header>
<div class="grid grid-2" style="margin-top:28px">{items}</div></div><div class="page-end"></div>'''
        coll = {'@type': 'CollectionPage', 'url': ORIGIN + url(path), 'name': col['title'], 'description': col['description'],
                'mainEntity': item_list(sel, col['title'])}
        col_title = col.get('seoTitle') or (f'{col["title"]} — подборка НЭН' if len(col['title']) <= 52 else f'{col["title"]} | НЭН')
        write(path, page(path, col_title, short(col['description'], 160), body,
                         schema=[coll, crumbs_ld], active='/podborki/'))
    crumbs_html, crumbs_ld = breadcrumbs([('Что почитать с детьми', '/'), ('Подборки', None)])
    cards_html = ''.join(
        f'<article class="text-card"><span class="num">{e(col["ageLabel"])}</span><h3><a href="{url("/podborki/" + col["slug"] + "/")}">{e(col["title"])}</a></h3>'
        f'<p>{e(col["description"])}</p><p class="meta">{e(books_word(len(col["books"])))}</p></article>' for col in cols)
    body = f'''{crumbs_html}<div class="wrap"><header class="list-head"><h1 class="h1">Подборки НЭН</h1>
<div class="intro"><p>Редакционные подборки детских книг для разных возрастов и семейных ситуаций.</p></div></header>
<div class="grid grid-2" style="margin-top:28px">{cards_html}</div></div><div class="page-end"></div>'''
    write('/podborki/', page('/podborki/', 'Подборки детских книг — НЭН', 'Редакционные подборки детских книг НЭН для разных возрастов и семейных ситуаций.',
                             body, schema=[crumbs_ld], active='/podborki/'))

    # Указатели: возраст, темы, авторы
    crumbs_html, crumbs_ld = breadcrumbs([('Что почитать с детьми', '/'), ('По возрасту', None)])
    groups = ''.join(
        f'<section class="age-group"><a class="age-tile" href="{url(band_path(band))}"><b>{e(band[5])} <small>{e(band[6])}</small></b><span>{e(books_word(band_counts[band[0]]))}</span></a>'
        f'<div class="chips">' + ''.join(f'<a class="chip" href="{url(AGE_PAGES[a])}">{e(f"{a} {age_word(a)}")}</a>' for a in range(max(band[2], 1), min(band[3], 14) + 1)) +
        '</div></section>' for band in AGE_BANDS)
    body = f'''{crumbs_html}<div class="wrap"><header class="list-head"><h1 class="h1">Книги по возрасту</h1>
<div class="intro"><p>Выберите возраст ребенка — покажем книги, которые ему подойдут, начиная с тех, что мы знаем и советуем лучше всего. Внутри каждой группы можно уточнить возраст до года.</p>
<p>Возраст на каждой книге — рекомендация редакции НЭН, а не издательская маркировка 0+, 6+ или 12+. Маркировка говорит, кому книгу можно продавать, но не когда ее интересно читать. Мы смотрим на объем, язык и темы: можно ли книгу слушать или уже читать самому, нужна ли помощь взрослого, чтобы обсудить сложное. Группы совпадают с возрастными тегами в журнале НЭН.</p></div></header>
<div class="age-groups" style="margin-top:28px">{groups}</div></div><div class="page-end"></div>'''
    write('/vozrast/', page('/vozrast/', 'Книги для детей по возрасту — НЭН', 'Что почитать ребенку от 1 года до 14 лет: книги по возрасту с рекомендациями редакции НЭН.',
                            body, schema=[crumbs_ld], active='/vozrast/'))

    crumbs_html, crumbs_ld = breadcrumbs([('Что почитать с детьми', '/'), ('Темы', None)])
    t_chips = ''.join(f'<a class="topic" href="{url("/tema/" + THEMES[t][0] + "/")}">{e(THEME_SHORT.get(t, t))}<span class="count">{themes[t]}</span></a>' for t in sorted(THEME_PAGES, key=lambda t: -themes[t]))
    g_chips = ''.join(f'<a class="topic" href="{url("/zhanr/" + GENRES[g][0] + "/")}">{e(GENRE_SHORT.get(g, g))}<span class="count">{genres[g]}</span></a>' for g in sorted(GENRE_PAGES, key=lambda g: -genres[g]))
    body = f'''{crumbs_html}<div class="wrap"><header class="list-head"><h1 class="h1">Книги по темам и жанрам</h1>
<div class="intro"><p>Книги о том, что волнует ребенка прямо сейчас: детский сад, страхи, дружба, развод родителей, — и подборки по любимым жанрам.</p></div></header>
<section class="section"><h2 class="h2" style="margin-bottom:16px">Темы</h2><div class="topics">{t_chips}</div></section>
<section class="section"><h2 class="h2" style="margin-bottom:16px">Жанры</h2><div class="topics">{g_chips}</div></section>
<section class="section"><h2 class="h2" style="margin-bottom:16px">Ещё</h2><div class="topics"><a class="topic" href="{url('/pered-snom/')}">{e('Перед сном')}<span class="count">{len(bed)}</span></a><a class="topic" href="{url('/avtor/')}">Авторы<span class="count">{len(AUTHOR_PAGES)}</span></a></div></section>
</div><div class="page-end"></div>'''
    write('/tema/', page('/tema/', 'Детские книги по темам и жанрам — НЭН', 'Детские книги по темам — эмоции, страхи, дружба, школа, война, смерть — и по жанрам: сказки, детективы, фэнтези, стихи.',
                         body, schema=[crumbs_ld], active='/tema/'))

    crumbs_html, crumbs_ld = breadcrumbs([('Что почитать с детьми', '/'), ('Авторы', None)])
    letters = collections.defaultdict(list)
    for a in sorted(AUTHOR_PAGES, key=lambda a: a.split()[-1]):
        letters[yo(a.split()[-1][0].upper())].append(a)
    blocks = ''.join(f'<section class="section"><h2 class="h3" style="margin-bottom:12px">{e(L)}</h2><div class="chips">' +
                     ''.join(f'<a class="chip" href="{url("/avtor/" + slugify(a) + "/")}">{e(a)}<span class="count">{authors[a]}</span></a>' for a in names) +
                     '</div></section>' for L, names in sorted(letters.items()))
    body = f'''{crumbs_html}<div class="wrap"><header class="list-head"><h1 class="h1">Детские писатели</h1>
<div class="intro"><p>Авторы, у которых в каталоге НЭН три книги и больше.</p></div></header>{blocks}</div><div class="page-end"></div>'''
    write('/avtor/', page('/avtor/', 'Детские писатели: книги по авторам — НЭН', 'Книги любимых детских писателей с рекомендациями редакции НЭН: с какого возраста читать и о чём каждая книга.',
                          body, schema=[crumbs_ld], active=None))

    # Каталог
    theme_opts = ''.join(f'<option value="{e(t)}">{e(t)}</option>' for t in sorted(t for t in themes if themes[t] >= 8))
    genre_opts = ''.join(f'<option value="{e(g)}">{e(g)}</option>' for g in sorted(g for g in genres if genres[g] >= 3))
    age_opts = ''.join(f'<option value="{band[0]}">{e(band[1])}</option>' for band in AGE_BANDS)
    filters = f'''<form class="filters" id="catalog-filters" action="{url('/katalog/')}" method="get" role="search">
<div class="row"><label><span class="visually-hidden">Поиск</span><input type="search" name="q" placeholder="{e('Название, автор или тема')}"></label>
<label><span class="visually-hidden">Возраст</span><select name="age"><option value="">Любой возраст</option>{age_opts}</select></label>
<label><span class="visually-hidden">Тема</span><select name="theme"><option value="">Любая тема</option>{theme_opts}</select></label>
<label><span class="visually-hidden">Жанр</span><select name="genre"><option value="">Любой жанр</option>{genre_opts}</select></label></div>
<div class="chips" role="group" aria-label="Формат чтения">{''.join(f'<button class="chip" type="button" data-mode="{k}" aria-pressed="false">{e(v)}</button>' for k, v in MODE.items())}<button class="chip" type="button" data-bed="1" aria-pressed="false">перед сном</button></div>
</form>'''
    land = landings.get('/katalog/', {})
    render_list('/katalog/', [('Что почитать с детьми', '/'), ('Каталог', None)], land.get('h1') or 'Каталог детских книг',
                land.get('title') or 'Каталог детских книг с рекомендациями — НЭН',
                land.get('description') or f'{books_word(len(books)).capitalize()} для детей и подростков от 1 года до 20 лет с рекомендациями редакции НЭН: поиск по возрасту, теме, жанру и формату чтения.',
                intro(landings.get('/katalog/'), 'Ищите по названию, автору или теме. Фильтры применяются сразу и сохраняются в ссылке — ее можно отправить.'),
                ordered, extra_top=filters + '<div id="catalog-results" hidden></div>', active='/katalog/')

    # Подбор книги и избранное
    crumbs_html, crumbs_ld = breadcrumbs([('Что почитать с детьми', '/'), ('Подобрать книгу', None)])
    theme_btns = ''.join(f'<button class="chip" type="button" data-theme="{e(t)}" aria-pressed="false">{e(t)}</button>'
                         for t, _ in themes.most_common(18))
    no_js = ''.join(f'<a class="chip" href="{url(band_path(band))}">{e(band[1])}</a>' for band in AGE_BANDS)
    body = f'''{crumbs_html}<div class="wrap"><header class="list-head"><h1 class="h1">Найдем подходящую книгу</h1>
<div class="intro"><p>Ответьте на три вопроса — мы предложим книги из каталога НЭН и объясним выбор.</p></div></header>
<form class="quiz" id="quiz" hidden>
<div class="step is-active" data-step="1"><span class="eyebrow">Шаг 1 из 3</span><h2 class="h2">Сколько лет ребенку?</h2>
<div class="stepper"><button type="button" data-age="-1" aria-label="Меньше">−</button><output name="age">5 лет</output><button type="button" data-age="1" aria-label="Больше">+</button></div>
<div class="btn-row"><button class="btn btn-primary" type="button" data-next>Дальше</button></div></div>
<div class="step" data-step="2"><span class="eyebrow">Шаг 2 из 3</span><h2 class="h2">Что ему сейчас интересно?</h2><p class="meta">Можно выбрать несколько тем или пропустить шаг.</p>
<div class="chips">{theme_btns}</div><div class="btn-row"><button class="btn btn-secondary" type="button" data-prev>Назад</button><button class="btn btn-primary" type="button" data-next>Дальше</button></div></div>
<div class="step" data-step="3"><span class="eyebrow">Шаг 3 из 3</span><h2 class="h2">Как будете читать?</h2>
<div class="chips">{''.join(f'<button class="chip" type="button" data-mode="{k}" aria-pressed="false">{e(v)}</button>' for k, v in MODE.items())}<button class="chip" type="button" data-bed="1" aria-pressed="false">перед сном</button></div>
<div class="btn-row"><button class="btn btn-secondary" type="button" data-prev>Назад</button><button class="btn btn-primary" type="submit">Показать книги</button></div></div>
</form>
<section class="section"><h2 class="h3" style="margin-bottom:12px">Или выберите сами</h2><p class="body" style="margin-bottom:16px">{e('Подбор учитывает возраст ребенка, выбранные темы и то, как вы будете читать: вместе, самостоятельно или перед сном. Первыми идут книги, которые редакция знает и советует лучше всего. Если хочется посмотреть всё, откройте книги по возрасту или по темам.')}</p><div class="chips">{no_js}<a class="chip" href="{url('/tema/')}">Все темы</a><a class="chip" href="{url('/pered-snom/')}">Перед сном</a></div></section>
<div id="quiz-results" style="margin-top:28px"></div></div><div class="page-end"></div>'''
    write('/podbor/', page('/podbor/', 'Подобрать книгу для ребенка — НЭН', 'Ответьте на три вопроса о возрасте и интересах ребенка — НЭН предложит подходящие книги и объяснит выбор.',
                           body, schema=[crumbs_ld], active='/podbor/'))
    body = f'''<div class="wrap"><header class="list-head"><h1 class="h1">Избранное</h1><div class="intro"><p>Книги, которые вы сохранили. Список хранится только в этом браузере.</p></div></header>
<div id="favorites" style="margin-top:28px"><p class="empty">Пока здесь пусто. Сохраняйте книги кнопкой «Сохранить в избранное» на их страницах.</p></div></div><div class="page-end"></div>'''
    write('/izbrannoe/', page('/izbrannoe/', 'Избранные книги — НЭН', 'Книги, которые вы сохранили в сервисе «Что почитать с детьми».', body, active='/izbrannoe/', noindex=True))

    # Главная
    start = [by_slug[s] for s in json.load(open(os.path.join(ROOT, 'site/content/home.json'), encoding='utf-8'))['start'] if s in by_slug]
    tiles = ''.join(f'<a class="age-tile" href="{url(band_path(band))}"><b>{e(band[5])} <small>{e(band[6])}</small></b><span>{e(books_word(band_counts[band[0]]))}</span></a>' for band in AGE_BANDS)
    hero_art = ''
    if os.path.exists(os.path.join(ROOT, 'site/assets/hero.webp')):
        hero_art = (f'<div class="hero-art"><img src="{url("/assets/hero.webp")}" srcset="{url("/assets/hero-600.webp")} 600w, {url("/assets/hero.webp")} 1200w" '
                    f'sizes="(min-width: 900px) 600px, 100vw" alt="" width="1200" height="630" fetchpriority="high" decoding="async"></div>')
    top_themes = ''.join(f'<a class="topic" href="{url("/tema/" + THEMES[t][0] + "/")}">{e(THEME_SHORT.get(t, t))}</a>' for t in
                         ['эмоции', 'страх', 'детский сад', 'школа', 'дружба', 'братья и сёстры', 'смерть', 'война', 'первая любовь', 'буллинг', 'космос', 'динозавры'] if t in THEME_PAGES)
    col_cards = ''.join(
        f'<article class="text-card"><span class="num">{e(col["ageLabel"])}</span><h3><a href="{url("/podborki/" + col["slug"] + "/")}">{e(col["title"])}</a></h3><p>{e(col["description"])}</p></article>'
        for col in cols[:6])
    written = sum(1 for b in books if b.get('card'))
    home = landings.get('/', {})
    body = f'''<div class="wrap">
<section class="hero{' hero-with-art' if hero_art else ''}"><div class="hero-copy"><span class="eyebrow">{e("Книги НЭН · " + books_word(len(books)))}</span>
<h1 class="h1">{e(home.get('h1', 'Что почитать с детьми'))}</h1>
<p class="lead">{e(home.get('lead', 'Подберем книги по возрасту, интересам и настроению ребенка. Для каждой книги рассказываем, кому она подойдет, что важно знать родителям и о чём поговорить после чтения.'))}</p>
<div class="btn-row"><a class="btn btn-primary" href="{url('/podbor/')}">Подобрать книгу</a><a class="btn btn-secondary" href="{url('/katalog/')}">Открыть каталог</a></div>
<div class="hero-stats"><div><b>{len(books)}</b>книг в каталоге</div><div><b>{len(cols)}</b>подборок редакции</div></div></div>{hero_art}</section>
<section class="section"><div class="section-head"><h2 class="h2">Книги по возрасту</h2><a href="{url('/vozrast/')}">Уточнить возраст</a></div><div class="age-grid age-bands">{tiles}</div></section>
<section class="section"><div class="section-head"><h2 class="h2">Подборки НЭН</h2><a href="{url('/podborki/')}">Все подборки</a></div><div class="grid grid-3">{col_cards}</div></section>
<section class="section"><div class="section-head"><h2 class="h2">О чём бы почитать</h2><a href="{url('/tema/')}">Все темы</a></div><div class="topics">{top_themes}</div></section>
<section class="section"><div class="section-head"><h2 class="h2">Книги, с которых можно начать</h2><a href="{url('/katalog/')}">Весь каталог</a></div>{book_grid(start)}</section>
<section class="section"><div class="panel-deep"><div><h2 class="h2">Не знаете, что выбрать</h2><p class="body" style="margin-top:12px">{e('Три вопроса о ребенке — и мы предложим книги из каталога с объяснением, почему они подойдут.')}</p></div>
<div><a class="btn btn-primary" href="{url('/podbor/')}">Подобрать книгу</a></div></div></section>
</div>{nen_reading('/')}<div class="wrap">
<section class="section"><h2 class="h2">Как мы выбираем книги</h2><div class="intro" style="margin-top:16px">{''.join(f'<p>{e(p)}</p>' for p in home.get('about', [
        'В каталоге — книги, которые редакция НЭН и наши эксперты советуют читать с детьми: классика, которую стоит перечитать, и современные книги о том, что волнует детей сегодня.',
        'Мы не пересказываем аннотации издательств. Для каждой книги пишем, о чём она, почему мы ее советуем, что важно знать родителям — от сложных тем до устаревших взглядов — и какие вопросы обсудить с ребенком после чтения.',
        'Возраст — это ориентир, а не правило: если ребенок любит слушать, многие книги можно начинать раньше, а сложные темы лучше обсуждать вместе.'])
    )}</div></section></div><div class="page-end"></div>'''
    site_ld = {'@type': 'WebPage', 'url': ORIGIN + url('/'), 'name': 'Что почитать с детьми — рекомендации НЭН',
               'description': 'Книги для детей по возрасту, интересам и настроению ребенка с рекомендациями редакции НЭН.',
               'inLanguage': 'ru', 'isPartOf': {'@type': 'WebSite', '@id': 'https://n-e-n.ru/#website', 'url': 'https://n-e-n.ru/', 'name': 'Нет, это нормально'},
               'publisher': {'@id': NEN_ORG['@id']}}
    write('/', page('/', 'Что почитать с детьми — книги по возрасту и темам | НЭН',
                    f'Что почитать ребенку: {books_word(len(books))} по возрасту, темам и жанрам с рекомендациями редакции НЭН — о чём книга, почему советуем и о чём поговорить после чтения.',
                    body, schema=[site_ld, NEN_ORG], active=None))

    # 404, индекс для фильтров, sitemap, robots
    write('/404.html', page('/404/', 'Страница не найдена — НЭН', 'Такой страницы нет.',
                            f'<div class="wrap"><header class="list-head"><h1 class="h1">Такой страницы нет</h1><div class="intro"><p>Возможно, книгу переименовали. Попробуйте <a href="{url("/katalog/")}">каталог</a> или <a href="{url("/podbor/")}">подбор книги</a>.</p></div></header></div><div class="page-end"></div>', noindex=True))
    theme_list = sorted({t for b in books for t in b.get('themes', [])})
    genre_list = sorted({g for b in books for g in b.get('genres', [])})
    index = {'themes': [yo(t) for t in theme_list], 'genres': [yo(g) for g in genre_list], 'modes': MODE, 'base': BASE, 'covers': COVERS,
             'bands': {band[0]: [band[2], band[3]] for band in AGE_BANDS},
             'books': [[b['slug'], yo(b['title']), yo(b['author']), b['ageMin'], b['ageMax'], b.get('readingMode') or '',
                        b.get('cover') or '', 1 if b.get('suitableForBedtime') else 0,
                        [theme_list.index(t) for t in b.get('themes', [])], [genre_list.index(g) for g in b.get('genres', [])],
                        typo(yo(short(b['snippet'], 120))), yo(b['ageLabel']), b['rank']] for b in ordered]}
    os.makedirs(os.path.join(OUT, 'data'), exist_ok=True)
    json.dump(index, open(os.path.join(OUT, 'data/index.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    secondary = {f'/kniga/{b["slug"]}/' for b in books if b.get('mainEdition')}
    urls = [p for p in WRITTEN if p not in ('/izbrannoe/',) and p not in secondary]
    sitemap = ''.join(f'<url><loc>{ORIGIN}{url(p)}</loc><lastmod>{TODAY}</lastmod></url>' for p in sorted(urls))
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sitemap}</urlset>\n')
    open(os.path.join(OUT, 'robots.txt'), 'w', encoding='utf-8').write(
        'User-agent: *\nDisallow: /\n' if PREVIEW else f'User-agent: *\nAllow: /\nSitemap: {ORIGIN}{BASE}/sitemap.xml\n')
    open(os.path.join(OUT, '.nojekyll'), 'w').close()
    print(f'страниц: {len(WRITTEN)}; карточек с новыми текстами: {written} из {len(books)}; '
          f'темы: {len(THEME_PAGES)}, жанры: {len(GENRE_PAGES)}, авторы: {len(AUTHOR_PAGES)}; '
          f'других изданий (canonical на основное): {n_editions}; папка: {OUT}')


ASSET_VERSION = ''
NEN_ARTICLES, NEN_READING = {}, {}
AUTHOR_PAGES, THEME_PAGES, GENRE_PAGES, AGE_PAGES = set(), set(), set(), {}

if __name__ == '__main__':
    main()
