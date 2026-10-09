/* «Что почитать с детьми»: фильтры каталога, подбор книги, избранное.
   Страницы целиком собраны на сервере; без JavaScript всё читается и все ссылки работают. */
(function () {
  'use strict';
  var BASE = document.body.getAttribute('data-base') || '';
  var MODES = { together: 'читаем вместе', independent: 'читает сам', both: 'сам или вместе' };
  var FAV_KEY = 'nen-knigi-favorites';
  var indexPromise = null;

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(BASE + '/data/index.json').then(function (r) { return r.json(); });
    }
    return indexPromise;
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function plural(n, one, few, many) {
    if (n % 10 === 1 && n % 100 !== 11) return one;
    if ([2, 3, 4].indexOf(n % 10) >= 0 && [12, 13, 14].indexOf(n % 100) < 0) return few;
    return many;
  }

  // Индекс: [slug, title, author, ageMin, ageMax, mode, cover, bedtime, themes, genres, snippet, ageLabel, rank]
  function card(idx, b) {
    var tags = '<span class="tag tag-blue">' + esc(b[11]) + '</span>';
    if (MODES[b[5]]) tags += '<span class="tag tag-pink">' + esc(MODES[b[5]]) + '</span>';
    if (b[7]) tags += '<span class="tag tag-yellow">перед сном</span>';
    var cover = b[6]
      ? '<div class="cover"><img src="' + esc(idx.covers + b[6]) + '" alt="' + esc('Обложка книги «' + b[1] + '»') + '" width="240" height="320" loading="lazy" decoding="async"></div>'
      : '<div class="cover" aria-hidden="true"></div>';
    return '<article class="card book-card">' + cover +
      '<h3 class="title"><a href="' + BASE + '/kniga/' + esc(b[0]) + '/">' + esc(b[1]) + '</a></h3>' +
      '<p class="author">' + esc(b[2]) + '</p><p class="snippet">' + esc(b[10]) + '</p>' +
      '<div class="tags">' + tags + '</div></article>';
  }

  function grid(idx, list) {
    return '<div class="grid grid-4">' + list.map(function (b) { return card(idx, b); }).join('') + '</div>';
  }

  function norm(s) { return String(s || '').toLowerCase().replace(/ё/g, 'е'); }

  function filterBooks(idx, f) {
    var q = norm(f.q).trim();
    var theme = f.theme ? idx.themes.indexOf(f.theme) : -1;
    var genre = f.genre ? idx.genres.indexOf(f.genre) : -1;
    var themesAny = (f.themes || []).map(function (t) { return idx.themes.indexOf(t); }).filter(function (i) { return i >= 0; });
    return idx.books.filter(function (b) {
      if (f.age && !(b[3] <= f.age && f.age <= b[4])) return false;
      if (f.mode && b[5] !== f.mode && b[5] !== 'both') return false;
      if (f.bed && !b[7]) return false;
      if (theme >= 0 && b[8].indexOf(theme) < 0) return false;
      if (genre >= 0 && b[9].indexOf(genre) < 0) return false;
      if (themesAny.length && !themesAny.some(function (t) { return b[8].indexOf(t) >= 0; })) return false;
      if (q) {
        var hay = norm(b[1] + ' ' + b[2] + ' ' + b[10] + ' ' + b[8].map(function (i) { return idx.themes[i]; }).join(' '));
        if (q.split(/\s+/).some(function (w) { return hay.indexOf(w) < 0; })) return false;
      }
      return true;
    });
  }

  /* ── Каталог ── */
  function initCatalog() {
    var form = document.getElementById('catalog-filters');
    var box = document.getElementById('catalog-results');
    if (!form || !box) return;
    var serverList = Array.prototype.slice.call(document.querySelectorAll('.list-head ~ .results-meta, .list-head ~ .grid, .list-head ~ .pager'));
    var shown = 48;
    var state = { q: '', age: 0, theme: '', genre: '', mode: '', bed: false };
    var params = new URLSearchParams(location.search);
    state.q = params.get('q') || '';
    state.age = parseInt(params.get('age'), 10) || 0;
    state.theme = params.get('theme') || '';
    state.genre = params.get('genre') || '';
    state.mode = params.get('mode') || '';
    state.bed = params.get('bed') === '1';
    form.q.value = state.q;
    form.age.value = state.age || '';
    form.theme.value = state.theme;
    form.genre.value = state.genre;

    function active() { return state.q || state.age || state.theme || state.genre || state.mode || state.bed; }

    function syncChips() {
      form.querySelectorAll('[data-mode]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-mode') === state.mode)); });
      form.querySelectorAll('[data-bed]').forEach(function (b) { b.setAttribute('aria-pressed', String(state.bed)); });
    }

    function render() {
      syncChips();
      var p = new URLSearchParams();
      if (state.q) p.set('q', state.q);
      if (state.age) p.set('age', state.age);
      if (state.theme) p.set('theme', state.theme);
      if (state.genre) p.set('genre', state.genre);
      if (state.mode) p.set('mode', state.mode);
      if (state.bed) p.set('bed', '1');
      history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
      if (!active()) {
        box.hidden = true;
        serverList.forEach(function (el) { el.hidden = false; });
        return;
      }
      loadIndex().then(function (idx) {
        var list = filterBooks(idx, state);
        serverList.forEach(function (el) { el.hidden = true; });
        box.hidden = false;
        var n = list.length;
        var head = '<div class="results-meta"><span class="meta">' + (n ? 'Нашлось ' + n + ' ' + plural(n, 'книга', 'книги', 'книг') : '') + '</span></div>';
        if (!n) {
          box.innerHTML = head + '<p class="empty">Ничего не нашлось. Попробуйте убрать один из фильтров.</p>';
          return;
        }
        box.innerHTML = head + grid(idx, list.slice(0, shown)) +
          (n > shown ? '<div class="btn-row" style="margin-top:24px"><button class="btn btn-secondary" type="button" data-more>Показать еще</button></div>' : '');
      });
    }

    form.addEventListener('submit', function (ev) { ev.preventDefault(); });
    form.addEventListener('input', function (ev) {
      var t = ev.target;
      if (t.name === 'q') state.q = t.value;
      if (t.name === 'age') state.age = parseInt(t.value, 10) || 0;
      if (t.name === 'theme') state.theme = t.value;
      if (t.name === 'genre') state.genre = t.value;
      shown = 48;
      render();
    });
    form.addEventListener('click', function (ev) {
      var t = ev.target.closest('button');
      if (!t) return;
      if (t.hasAttribute('data-mode')) state.mode = state.mode === t.getAttribute('data-mode') ? '' : t.getAttribute('data-mode');
      if (t.hasAttribute('data-bed')) state.bed = !state.bed;
      shown = 48;
      render();
    });
    box.addEventListener('click', function (ev) {
      if (ev.target.hasAttribute('data-more')) { shown += 48; render(); }
    });
    if (active()) render(); else syncChips();
  }

  /* ── Подбор книги ── */
  function initQuiz() {
    var form = document.getElementById('quiz');
    var out = document.getElementById('quiz-results');
    if (!form) return;
    form.hidden = false;
    var age = 5, step = 1, themes = [], mode = '', bed = false;
    var ageOut = form.querySelector('output[name=age]');

    function word(n) { return plural(n, 'год', 'года', 'лет'); }
    function show() {
      form.querySelectorAll('.step').forEach(function (s) { s.classList.toggle('is-active', +s.getAttribute('data-step') === step); });
      ageOut.textContent = age + ' ' + word(age);
    }
    form.addEventListener('click', function (ev) {
      var t = ev.target.closest('button');
      if (!t) return;
      if (t.hasAttribute('data-age')) age = Math.max(1, Math.min(17, age + (+t.getAttribute('data-age'))));
      if (t.hasAttribute('data-next')) step = Math.min(3, step + 1);
      if (t.hasAttribute('data-prev')) step = Math.max(1, step - 1);
      if (t.hasAttribute('data-theme')) {
        var th = t.getAttribute('data-theme');
        var i = themes.indexOf(th);
        if (i >= 0) themes.splice(i, 1); else themes.push(th);
        t.setAttribute('aria-pressed', String(i < 0));
      }
      if (t.hasAttribute('data-mode')) {
        mode = mode === t.getAttribute('data-mode') ? '' : t.getAttribute('data-mode');
        form.querySelectorAll('[data-mode]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-mode') === mode)); });
      }
      if (t.hasAttribute('data-bed')) { bed = !bed; t.setAttribute('aria-pressed', String(bed)); }
      show();
    });
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      loadIndex().then(function (idx) {
        var list = filterBooks(idx, { age: age, themes: themes, mode: mode, bed: bed });
        list.sort(function (a, b) {
          var da = Math.abs((a[3] + a[4]) / 2 - age) + 0.2 * (a[4] - a[3]);
          var db = Math.abs((b[3] + b[4]) / 2 - age) + 0.2 * (b[4] - b[3]);
          return (a[12] - b[12]) || (da - db);
        });
        var n = list.length;
        var why = 'Подходят ребенку в ' + age + ' ' + word(age) +
          (themes.length ? ', темы: ' + themes.join(', ') : '') +
          (mode ? ', ' + MODES[mode] : '') + (bed ? ', для чтения перед сном' : '') + '.';
        out.innerHTML = n
          ? '<h2 class="h2">Нашлось ' + n + ' ' + plural(n, 'книга', 'книги', 'книг') + '</h2><p class="meta" style="margin:8px 0 20px">' + esc(why) + '</p>' + grid(idx, list.slice(0, 24))
          : '<p class="empty">Ничего не нашлось. Попробуйте выбрать меньше тем.</p>';
        out.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    show();
  }

  /* ── Избранное ── */
  function favs() {
    try { return JSON.parse(localStorage.getItem(FAV_KEY)) || []; } catch (e) { return []; }
  }
  function saveFavs(list) {
    try { localStorage.setItem(FAV_KEY, JSON.stringify(list)); } catch (e) { /* приватный режим */ }
  }
  function initFavs() {
    document.querySelectorAll('[data-fav]').forEach(function (btn) {
      var slug = btn.getAttribute('data-fav');
      function sync() {
        var on = favs().indexOf(slug) >= 0;
        btn.setAttribute('aria-pressed', String(on));
        btn.textContent = on ? 'В избранном' : 'Сохранить в избранное';
      }
      btn.addEventListener('click', function () {
        var list = favs();
        var i = list.indexOf(slug);
        if (i >= 0) list.splice(i, 1); else list.unshift(slug);
        saveFavs(list);
        sync();
      });
      sync();
    });
    var box = document.getElementById('favorites');
    if (!box) return;
    var list = favs();
    if (!list.length) return;
    loadIndex().then(function (idx) {
      var bySlug = {};
      idx.books.forEach(function (b) { bySlug[b[0]] = b; });
      var books = list.map(function (s) { return bySlug[s]; }).filter(Boolean);
      if (books.length) box.innerHTML = grid(idx, books);
    });
  }

  initCatalog();
  initQuiz();
  initFavs();
})();
