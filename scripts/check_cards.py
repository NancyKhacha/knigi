#!/usr/bin/env python3
"""Проверка карточек по стайлгайду и сборка превью для редакции.

  python3 scripts/check_cards.py cards/pilot.json cards/pilot.md
"""
import json, re, sys

LIMITS = {'seoTitle': 70, 'seoDescription': 160}
RANGES = {'about': (250, 650), 'whyRecommended': (300, 750), 'parentsNote': (100, 450)}
# Книгу знаем только по аннотации: дописывать нечем, выдумывать нельзя.
RANGES_ANNOTATION = {'about': (150, 650), 'whyRecommended': (200, 750), 'parentsNote': (100, 450)}
BANNED = re.compile(r'чудесн|увлекательн|незабываем|красочн|лучший подарок|развиваш|обязательно прочитайте|развивает воображение', re.I)
QUESTIONS = 3


def check(card):
    problems = []
    for field, limit in LIMITS.items():
        if len(card.get(field, '')) > limit:
            problems.append(f'{field}: {len(card[field])} знаков (лимит {limit})')
    ranges = RANGES_ANNOTATION if card.get('source') == 'annotation' else RANGES
    for field, (lo, hi) in ranges.items():
        n = len(card.get(field, ''))
        if not lo <= n <= hi:
            problems.append(f'{field}: {n} знаков (нужно {lo}–{hi})')
    for field in ('about', 'whyRecommended', 'parentsNote', 'seoDescription'):
        m = BANNED.search(card.get(field, ''))
        if m:
            problems.append(f'{field}: рекламное слово «{m.group(0)}»')
    if len(card.get('discussionQuestions', [])) != QUESTIONS:
        problems.append(f'вопросов {len(card.get("discussionQuestions", []))}, нужно {QUESTIONS}')
    # Подпись возраста стоит в именительном падеже: «2–4 года». Во фразах «для детей 2–4 лет» — родительный, это верно.
    labels = [card.get('ageLabel', ''), (card.get('ageSuggestion') or {}).get('label', '')]
    for lo, hi in (m for l in labels for m in re.findall(r'(\d+)–(\d+) лет', l)):
        h = int(hi)
        if h % 10 in (1, 2, 3, 4) and h % 100 not in (11, 12, 13, 14):
            problems.append(f'подпись возраста «{lo}–{hi} лет»')
    return problems


def plural(n):
    if n % 10 == 1 and n % 100 != 11:
        return 'карточка'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'карточки'
    return 'карточек'


def render(cards):
    out = ['# Пилот: новые карточки книг', '',
           f'{len(cards)} {plural(len(cards))} по [стайлгайду](STYLEGUIDE.md). '
           'Пометка «по аннотации» — книгу мы не знаем, текст написан только по описанию издательства, редактору нужно сверить с книгой.', '']
    for c in cards:
        age = c['ageLabel']
        if c.get('ageSuggestion'):
            age += f' → предлагаем **{c["ageSuggestion"]["label"]}** ({c["ageSuggestion"]["reason"]})'
        src = ' · *по аннотации*' if c['source'] == 'annotation' else ''
        out += [f'## {c["title"]}', '', f'{c["author"]} · {age}{src} · [карточка на сайте](https://n-e-n.ru/knigi/kniga/{c["slug"]}/)', '',
                f'**Заголовок в поиске:** {c["seoTitle"]}  ', f'**Описание в поиске:** {c["seoDescription"]}', '',
                '**О чём книга**', '', c['about'], '',
                '**Почему советуем**', '', c['whyRecommended'], '',
                '**Что важно знать родителям**', '', c['parentsNote'], '',
                '**О чём поговорить после чтения**', '']
        out += [f'- {q}' for q in c['discussionQuestions']]
        if c.get('editorNotes'):
            out += ['', '> **Редактору:** ' + ' '.join(c['editorNotes'])]
        out += ['', '---', '']
    return '\n'.join(out)


def main(src, dst=None):
    cards = json.load(open(src, encoding='utf-8'))
    bad = 0
    for c in cards:
        p = check(c)
        if p:
            bad += 1
            print(f'{c["slug"]}: ' + '; '.join(p))
    print(f'карточек: {len(cards)}, с замечаниями: {bad}')
    if dst:
        open(dst, 'w', encoding='utf-8').write(render(cards))


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(*sys.argv[1:])
