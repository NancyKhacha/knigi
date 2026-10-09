#!/usr/bin/env python3
"""Сводка по готовым карточкам для редакции: cards/review.csv и cards/PROGRESS.md.

  python3 scripts/collect_notes.py

review.csv — по строке на карточку с пометками: откуда текст (знаем книгу или только
аннотация), предложенный возраст и все замечания авторов о данных каталога.
"""
import collections, csv, glob, json, os

SOURCE = {'knowledge': 'знаем книгу', 'knowledge+annotation': 'знаем книгу + аннотация', 'annotation': 'только аннотация'}


def main():
    files = ['cards/pilot.json'] + sorted(glob.glob('cards/batches/*.json'))
    rows, sources = [], collections.Counter()
    for f in files:
        for c in json.load(open(f, encoding='utf-8')):
            sources[c.get('source', '')] += 1
            sug = c.get('ageSuggestion') or {}
            notes = c.get('editorNotes') or []
            if not notes and not sug and c.get('source') != 'annotation':
                continue
            rows.append({'file': os.path.basename(f), 'slug': c['slug'], 'title': c['title'], 'author': c['author'],
                         'url': f'https://nancykhacha.github.io/knigi/kniga/{c["slug"]}/',
                         'source': SOURCE.get(c.get('source'), c.get('source', '')), 'age_catalog': c.get('ageLabel', ''),
                         'age_suggested': sug.get('label', ''), 'age_reason': sug.get('reason', ''),
                         'notes': ' | '.join(notes)})
    with open('cards/review.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    total = sum(sources.values())
    with open('cards/PROGRESS.md', 'w', encoding='utf-8') as f:
        f.write('# Карточки: прогресс\n\n')
        removed = sum(1 for _ in csv.DictReader(open('fixes/removed.csv', encoding='utf-8-sig'))) if os.path.exists('fixes/removed.csv') else 0
        f.write(f'Готово {total} карточек — весь каталог ({len(files) - 1} партий + пилот)'
                + (f'; еще {removed} книг удалены по решению редакции (fixes/removed.csv)' if removed else '') + '.\n\n')
        f.write('| Откуда текст | Карточек |\n|---|---|\n')
        for k, v in sources.most_common():
            f.write(f'| {SOURCE.get(k, k)} | {v} |\n')
        f.write(f'\nПредложен другой возраст: {sum(1 for r in rows if r["age_suggested"])}. '
                'Все пометки для редакции — в [review.csv](review.csv).\n')
    print(f'карточек: {total}; {dict(sources)}; строк в review.csv: {len(rows)}')


if __name__ == '__main__':
    main()
