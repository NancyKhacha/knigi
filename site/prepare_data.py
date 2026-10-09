#!/usr/bin/env python3
"""Сборка site/data/books.json — единого файла данных для генератора.

  python3 site/prepare_data.py fixes/catalog-index.fixed.json <папка с books/*.json>

Берет исправленный каталог и добавляет из полных карточек то, чего нет в индексе:
аннотацию издательства с источником, переводчика, год, ISBN, чувствительные темы.
"""
import csv, json, os, sys

INDEX_FIELDS = ['slug', 'title', 'author', 'ageMin', 'ageMax', 'ageLabel', 'readingMode', 'genres', 'themes', 'moods',
                'suitableForBedtime', 'lengthCategory', 'pages', 'publisher', 'isbn13', 'seriesName', 'seriesNumber',
                'editionNote', 'editionContributors', 'originalTitle', 'shortDescription', 'whyRecommended']
DETAIL_FIELDS = ['translator', 'publicationYear', 'sensitiveTopics']


def main(index_path, books_dir, out='site/data/books.json'):
    books = []
    missing = 0
    removed_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fixes/removed.csv')
    removed = {r['slug'] for r in csv.DictReader(open(removed_path, encoding='utf-8-sig'))} if os.path.exists(removed_path) else set()
    for b in json.load(open(index_path, encoding='utf-8')):
        if b['slug'] in removed:          # убраны из каталога по решению редакции
            continue
        row = {k: b[k] for k in INDEX_FIELDS if b.get(k) not in (None, [], '')}
        row['cover'] = (b.get('cover') or {}).get('cachedPath')
        path = os.path.join(books_dir, b['slug'] + '.json')
        if os.path.exists(path):
            d = json.load(open(path, encoding='utf-8'))
            row.update({k: d[k] for k in DETAIL_FIELDS if d.get(k) not in (None, [], '')})
            if d.get('fullDescription'):
                row['annotation'] = d['fullDescription'].strip()
            src = d.get('annotationProvenance') or {}
            if src.get('source'):
                row['annotationSource'] = src['source']
        else:
            missing += 1
        books.append(row)
    json.dump(books, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'книг: {len(books)}, без полной карточки: {missing}, файл: {os.path.getsize(out) // 1024} КБ')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
