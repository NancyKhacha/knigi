#!/usr/bin/env python3
"""Нарезка каталога на партии для авторов карточек.

  python3 scripts/make_batches.py fixes/catalog-index.fixed.json <папка с books/*.json> work/in [размер]

Каждая партия — JSON-список книг со всем, что нужно для текста: исправленные название,
автор и возраст, жанры, темы, чувствительные темы, издание и аннотация издательства.
Книги из cards/pilot.json и уже готовых партий в cards/batches/ пропускаются.
Партия создается, только если для всех ее книг скачаны полные карточки.
"""
import glob, json, os, sys

FIELDS = ['slug', 'title', 'author', 'ageLabel', 'ageMin', 'ageMax', 'readingMode', 'genres', 'themes', 'moods',
          'suitableForBedtime', 'lengthCategory', 'pages', 'publisher', 'seriesName', 'seriesNumber', 'editionNote',
          'editionContributors', 'originalTitle', 'classicOrModern']
DETAIL = ['translator', 'publicationYear', 'sensitiveTopics', 'lifeSituations', 'emotionalStates']


def main(index_path, books_dir, out_dir, size=100):
    size = int(size)
    index = json.load(open(index_path, encoding='utf-8'))
    done = {c['slug'] for c in json.load(open('cards/pilot.json', encoding='utf-8'))}
    for f in glob.glob('cards/batches/*.json'):
        done |= {c['slug'] for c in json.load(open(f, encoding='utf-8'))}
    todo = [b for b in index if b['slug'] not in done]
    os.makedirs(out_dir, exist_ok=True)
    made = skipped = 0
    for n in range(0, len(todo), size):
        part = todo[n:n + size]
        name = os.path.join(out_dir, f'batch-{n // size + 1:03d}.json')
        if os.path.exists(name):
            continue
        rows = []
        for b in part:
            path = os.path.join(books_dir, b['slug'] + '.json')
            if not os.path.exists(path):
                break
            d = json.load(open(path, encoding='utf-8'))
            row = {k: b.get(k) for k in FIELDS if b.get(k) not in (None, [], '')}
            row.update({k: d.get(k) for k in DETAIL if d.get(k) not in (None, [], '')})
            row['annotation'] = (d.get('fullDescription') or d.get('shortDescription') or b.get('shortDescription') or '').strip()
            src = d.get('annotationProvenance') or {}
            if src.get('source'):
                row['annotationSource'] = src['source']
            rows.append(row)
        if len(rows) < len(part):
            skipped += 1
            continue
        json.dump(rows, open(name, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        made += 1
    print(f'книг без текста: {len(todo)}; партий создано: {made}; ждут докачки: {skipped}')


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    main(*sys.argv[1:])
