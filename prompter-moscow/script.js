/* =========================================================
   Prompter Moscow — script.js
   Без зависимостей. Скролл-эффекты только на IntersectionObserver,
   слушателей события scroll нет ни одного.
   ========================================================= */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Год в футере ---------- */
  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  /* ---------- Мобильное меню ---------- */
  var burger = document.getElementById('burger');
  var nav = document.getElementById('nav');

  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    });

    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        nav.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
        burger.setAttribute('aria-label', 'Открыть меню');
      }
    });
  }

  /* ---------- Появление секций при скролле ---------- */
  var revealEls = document.querySelectorAll('.reveal');

  if (reduceMotion || !('IntersectionObserver' in window)) {
    // Без анимации показываем всё сразу, чтобы контент не остался невидимым.
    Array.prototype.forEach.call(revealEls, function (el) { el.classList.add('is-in'); });
  } else {
    var revealIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        revealIO.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

    Array.prototype.forEach.call(revealEls, function (el) { revealIO.observe(el); });
  }

  /* ---------- Счётчики ---------- */
  var numsBlock = document.getElementById('nums');

  function runCounters() {
    var counters = numsBlock.querySelectorAll('[data-count]');

    Array.prototype.forEach.call(counters, function (el) {
      var target = parseInt(el.getAttribute('data-count'), 10) || 0;

      if (reduceMotion) {
        el.textContent = target + '+';
        return;
      }

      var duration = 2700;   // в полтора раза медленнее прежних 1800 мс
      var started = null;

      function tick(now) {
        if (started === null) started = now;
        var p = Math.min((now - started) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
        el.textContent = Math.round(target * eased) + '+';
        if (p < 1) requestAnimationFrame(tick);
      }

      requestAnimationFrame(tick);
    });
  }

  if (numsBlock) {
    if (!('IntersectionObserver' in window)) {
      runCounters();
    } else {
      var numsIO = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          runCounters();
          numsIO.disconnect(); // запускаем ровно один раз
        });
      }, { threshold: 0.35 });

      numsIO.observe(numsBlock);
    }
  }

  /* ---------- Кнопка «наверх» ---------- */
  var toTop = document.getElementById('totop');
  var sentinel = document.getElementById('top-sentinel');

  if (toTop && sentinel && 'IntersectionObserver' in window) {
    toTop.hidden = false;

    var topIO = new IntersectionObserver(function (entries) {
      // Сенсор виден — мы у самого верха, кнопку прячем.
      toTop.classList.toggle('is-on', !entries[0].isIntersecting);
    }, { rootMargin: '600px 0px 0px 0px' });

    topIO.observe(sentinel);

    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  }
})();
