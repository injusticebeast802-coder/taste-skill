/* =========================================================
   ГенИИ — form.js
   Форма заявки: маска телефона, проверка полей, отправка на /api/lead.

   Один и тот же файл обслуживает две страницы:
   • index.html — форма живёт в модальном окне и открывается кнопками
     [data-open-form];
   • zayavka.html — та же форма открыта сразу, модального окна на
     странице нет. Все действия с окном в этом случае просто ничего
     не делают, потому что элемента #modal там не существует.

   Из-за этого файл подключается и там, и там: разметка формы, правила
   проверки и адрес отправки не расходятся между страницами.
   ========================================================= */
(function () {
  'use strict';

  /* ---------- Элементы формы ---------- */
  var modal = document.getElementById('modal');
  var modalBody = document.getElementById('modal-body');
  var modalDone = document.getElementById('modal-done');
  var form = document.getElementById('frm');
  var submitBtn = document.getElementById('frm-submit');
  var failMsg = document.getElementById('frm-fail');

  var lastFocused = null;
  var lastSubmitAt = 0;
  var sending = false;

  var fName = document.getElementById('f-name');
  var fPhone = document.getElementById('f-phone');
  var fEmail = document.getElementById('f-email');
  var fCompany = document.getElementById('f-company');
  var fField = document.getElementById('f-field');
  var fHoney = document.getElementById('f-website');
  var fAgree1 = document.getElementById('f-agree1');
  var fAgree2 = document.getElementById('f-agree2');

  function dmValue() {
    var picked = form ? form.querySelector('input[name="dm"]:checked') : null;
    return picked ? picked.value : '';
  }

  /* ---------- Откуда пришла заявка ----------
     В сообщение боту добавляется строка «Источник». Так видно, пришёл
     человек с сайта или нажал кнопку в презентации: ссылка в
     презентации ведёт на /zayavka?from=presentation.

     Источник берём из адреса страницы (?from=… или ?utm_source=…),
     а если его там нет — из атрибута data-source у формы. Значение
     режем по длине и оставляем только безопасные символы: оно
     попадает в текст сообщения. */
  function leadSource() {
    var raw = '';

    try {
      var params = new URLSearchParams(window.location.search);
      raw = params.get('from') || params.get('utm_source') || '';
    } catch (e) {
      raw = '';
    }

    if (!raw && form) raw = form.getAttribute('data-source') || '';

    return String(raw).replace(/[^a-zA-Zа-яёА-ЯЁ0-9 _.\-]/g, '').trim().slice(0, 40);
  }

  function openModal() {
    if (!modal) return;
    lastFocused = document.activeElement;
    modal.hidden = false;
    document.body.classList.add('is-locked');
    if (fName) setTimeout(function () { fName.focus(); }, 30);
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove('is-locked');
    if (lastFocused && lastFocused.focus) lastFocused.focus();
  }

  document.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-open-form]');
    if (opener) { e.preventDefault(); openModal(); return; }

    var closer = e.target.closest('[data-close-form]');
    if (closer) { e.preventDefault(); closeModal(); }
  });

  /* Ссылка вида genii-ai.ru/#zayavka открывает форму сразу.
     Так на неё можно вести из письма, презентации или мессенджера,
     не заводя отдельную страницу. */
  function openByHash() {
    var h = window.location.hash.toLowerCase();
    if (h === '#zayavka' || h === '#form') openModal();
  }

  if (modal) {
    openByHash();
    window.addEventListener('hashchange', openByHash);
  }

  document.addEventListener('keydown', function (e) {
    if (!modal || modal.hidden) return;

    if (e.key === 'Escape') { closeModal(); return; }

    // Держим фокус внутри окна, пока оно открыто.
    if (e.key !== 'Tab') return;

    var focusables = modal.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
    );
    var visible = Array.prototype.filter.call(focusables, function (el) {
      return el.offsetParent !== null;
    });
    if (!visible.length) return;

    var first = visible[0];
    var last = visible[visible.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  /* ---------- Маска телефона +7 (___) ___-__-__ ---------- */
  function maskPhone(raw) {
    var digits = raw.replace(/\D/g, '');

    // Пользователь мог начать с 8 или с 7 — приводим к единому виду.
    if (digits[0] === '8' || digits[0] === '7') digits = digits.slice(1);
    digits = digits.slice(0, 10);

    if (!digits) return '';

    var out = '+7 (' + digits.slice(0, 3);
    if (digits.length >= 4) out += ') ' + digits.slice(3, 6);
    if (digits.length >= 7) out += '-' + digits.slice(6, 8);
    if (digits.length >= 9) out += '-' + digits.slice(8, 10);
    return out;
  }

  function phoneDigits(value) {
    var d = value.replace(/\D/g, '');
    if (d[0] === '8' || d[0] === '7') d = d.slice(1);
    return d;
  }

  if (fPhone) {
    fPhone.addEventListener('input', function () {
      fPhone.value = maskPhone(fPhone.value);
    });

    fPhone.addEventListener('focus', function () {
      if (!fPhone.value) fPhone.value = '+7 (';
    });

    fPhone.addEventListener('blur', function () {
      if (phoneDigits(fPhone.value).length === 0) fPhone.value = '';
    });

    // Backspace на пустой группе не должен «залипать» на скобках.
    fPhone.addEventListener('keydown', function (e) {
      if (e.key === 'Backspace' && phoneDigits(fPhone.value).length === 0) {
        e.preventDefault();
        fPhone.value = '';
      }
    });
  }

  /* ---------- Валидация ---------- */
  function setError(input, errKey, on) {
    var msg = form.querySelector('[data-err="' + errKey + '"]');
    if (msg) msg.hidden = !on;
    if (input) input.classList.toggle('is-bad', on);
  }

  function validName() {
    var ok = fName.value.trim().length >= 2;
    setError(fName, 'name', !ok);
    return ok;
  }

  function validPhone() {
    var ok = phoneDigits(fPhone.value).length === 10;
    setError(fPhone, 'phone', !ok);
    return ok;
  }

  /* Самая частая ошибка в этом поле — не опечатка, а незамеченная
     русская раскладка: «gmail.сщm» вместо «gmail.com». Выглядит почти
     правильно, и человек не понимает, что от него хотят.

     Такой адрес и раньше не проходил, но по неочевидной причине:
     поле с типом email заставляет браузер переписывать нелатинский
     домен в служебный вид, и «gmail.сщm» превращается в
     «gmail.xn--m-6tby». Дефисы и цифры в этой записи не проходят
     проверку — адрес отбивается, а человек видит бесполезное
     «проверьте адрес почты» и не понимает, что не так.

     Ловим признак такого превращения и подсказываем прямо. */
  /* Кириллические доменные зоны. Браузер переписывает их в служебный
     вид, поэтому сверяемся именно с ним: «.рф» приходит как «xn--p1ai».
     Список закрытый и короткий — так адрес на реальной российской зоне
     проходит, а «gmail.сщm» (это «xn--m-6tby») по-прежнему нет:
     набранная не в той раскладке ерунда никогда не совпадёт
     с настоящей зоной. */
  var IDN_ZONES = [
    'xn--p1ai',       // .рф
    'xn--p1acf',      // .рус
    'xn--80adxhks',   // .москва
    'xn--80aswg',     // .сайт
    'xn--80asehdb',   // .онлайн
    'xn--c1avg',      // .орг
    'xn--j1aef',      // .ком
    'xn--d1acj3b',    // .дети
    'xn--90ais',      // .бел
    'xn--j1amh',      // .укр
    'xn--80ao21a'     // .қаз
  ];

  function emailZone(v) {
    var at = v.lastIndexOf('@');
    if (at < 1) return '';
    var domain = v.slice(at + 1);
    var dot = domain.lastIndexOf('.');
    if (dot < 1) return '';
    return domain.slice(dot + 1).toLowerCase();
  }

  function validEmail() {
    var v = fEmail.value.trim();
    var msg = form.querySelector('[data-err="email"]');

    var zone = emailZone(v);
    var shapeOk = /^[^\s@]+@[^\s@]+\.[^\s@.]{2,}$/.test(v);
    // Обычная латинская зона любой длины: ru, com, agency, digital.
    var zoneOk = /^[a-z]{2,}$/.test(zone) || IDN_ZONES.indexOf(zone) !== -1;
    var ok = shapeOk && zoneOk;

    // Домен переписан браузером либо кириллица осталась как есть
    // (в браузерах, которые не переписывают).
    var wrongLayout = /(^|[@.])xn--/i.test(v) || /[а-яё]/i.test(v);

    if (msg) {
      msg.textContent = (!ok && wrongLayout)
        ? 'Похоже, адрес набран в русской раскладке'
        : 'Проверьте адрес почты';
    }

    setError(fEmail, 'email', !ok);
    return ok;
  }

  function validCompany() {
    var ok = fCompany.value.trim().length >= 2;
    setError(fCompany, 'company', !ok);
    return ok;
  }

  function validField() {
    var ok = fField.value.trim().length >= 2;
    setError(fField, 'field', !ok);
    return ok;
  }

  function validDm() {
    var ok = dmValue() !== '';
    var msg = form.querySelector('[data-err="dm"]');
    if (msg) msg.hidden = ok;
    var group = form.querySelector('.radios');
    if (group) group.classList.toggle('is-bad', !ok);
    return ok;
  }

  function validAgree() {
    var ok = fAgree1.checked && fAgree2.checked;
    var msg = form.querySelector('[data-err="agree"]');
    if (msg) msg.hidden = ok;
    fAgree1.closest('.chk').classList.toggle('is-bad', !fAgree1.checked);
    fAgree2.closest('.chk').classList.toggle('is-bad', !fAgree2.checked);
    return ok;
  }

  if (form) {
    /* Пустое поле, в которое человек ещё ничего не вводил, не ругаем при
       потере фокуса: подсветить ошибку до того, как посетитель начал
       заполнять форму, — значит отпугнуть его. После первой попытки
       отправки проверяем всё. */
    function onBlur(el, check) {
      return function () {
        if (el.value.trim() === '' && !form.classList.contains('is-validated')) return;
        check();
      };
    }

    fName.addEventListener('blur', onBlur(fName, validName));
    fPhone.addEventListener('blur', onBlur(fPhone, validPhone));
    fEmail.addEventListener('blur', onBlur(fEmail, validEmail));
    fCompany.addEventListener('blur', onBlur(fCompany, validCompany));
    fField.addEventListener('blur', onBlur(fField, validField));
    fAgree1.addEventListener('change', validAgree);
    fAgree2.addEventListener('change', validAgree);

    Array.prototype.forEach.call(form.querySelectorAll('input[name="dm"]'), function (r) {
      r.addEventListener('change', validDm);
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (sending) return;

      failMsg.hidden = true;

      // Защита от повторной отправки: не чаще одного раза в 3 секунды.
      var now = Date.now();
      if (now - lastSubmitAt < 3000) return;

      // Honeypot: поле скрыто, значит заполнить его мог только бот.
      // Показываем «успех», но ничего не отправляем.
      if (fHoney && fHoney.value.trim() !== '') {
        showDone();
        return;
      }

      // С этого момента место под сообщения об ошибках зарезервировано,
      // и форма перестаёт прыгать при их появлении и исчезновении.
      form.classList.add('is-validated');

      // Проверяем все поля разом, чтобы подсветить сразу каждое незаполненное.
      var okName = validName();
      var okPhone = validPhone();
      var okEmail = validEmail();
      var okCompany = validCompany();
      var okField = validField();
      var okDm = validDm();
      var okAgree = validAgree();

      if (!(okName && okPhone && okEmail && okCompany && okField && okDm && okAgree)) {
        var firstBad = form.querySelector('.is-bad');
        if (firstBad && firstBad.focus) firstBad.focus();
        return;
      }

      lastSubmitAt = now;
      sending = true;
      submitBtn.disabled = true;
      submitBtn.textContent = 'Отправляем…';

      sendLead({
        name: fName.value.trim(),
        phone: fPhone.value.trim(),
        email: fEmail.value.trim(),
        company: fCompany.value.trim(),
        field: fField.value.trim(),
        dm: dmValue(),
        source: leadSource()
      })
        .then(function (res) {
          if (!res.ok) {
            var err = new Error('lead ' + res.status);
            err.status = res.status;
            err.reason = res.data && res.data.error;
            throw err;
          }
          showDone();
        })
        .catch(function (err) {
          showFail(err);
        })
        .then(function () {
          sending = false;
          submitBtn.disabled = false;
          submitBtn.textContent = 'ОСТАВИТЬ ЗАЯВКУ';
        });
    });
  }

  /* ---------- Отправка заявки ----------
     Основной адрес — /api/lead: так было на Vercel, где заявку
     принимала серверная функция. На обычном хостинге этот адрес
     ведёт к файлу lead.php правилом из .htaccess.

     Правило может не сработать: на части тарифов переписывание
     адресов выключено, да и сам .htaccess легко потерять при ручной
     заливке файлов. Тогда сервер отвечает на /api/lead своей
     страницей «не найдено», и заявка пропадает, хотя lead.php лежит
     на месте. Поэтому на 404 и 405 пробуем файл напрямую. */
  var LEAD_URLS = ['/api/lead', '/lead.php'];

  function postLead(url, payload) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      // Ответ бывает и не JSON — например, страница ошибки хостинга.
      return res.json()
        .catch(function () { return {}; })
        .then(function (data) {
          return { ok: res.ok, status: res.status, data: data, url: url };
        });
    });
  }

  function sendLead(payload) {
    return postLead(LEAD_URLS[0], payload).then(function (res) {
      if (res.status !== 404 && res.status !== 405) return res;

      if (window.console && console.warn) {
        console.warn('Адрес ' + LEAD_URLS[0] + ' ответил ' + res.status + ', пробуем ' + LEAD_URLS[1]);
      }
      return postLead(LEAD_URLS[1], payload);
    });
  }

  /* ---------- Отправить не удалось ----------
     Раньше на любую неудачу выводилось одно и то же «попробуйте ещё
     раз». Человек повторял отправку, получал то же самое и уходил,
     а понять причину можно было только через панель разработчика.

     Теперь на понятные случаи есть понятный ответ: при слишком
     частой отправке сервер отвечает 429, и правильный совет —
     подождать минуту, а не жать кнопку снова. Остальные сбои —
     не вина посетителя, ему незачем знать их устройство: показываем
     общую фразу и телефон, а технический код пишем в консоль, чтобы
     разбираться было по чему. */
  var FAIL_TEXT = {
    too_many_requests: 'Заявки уходят слишком часто. Подождите минуту и отправьте ещё раз',
    bad_name: 'Проверьте имя',
    bad_phone: 'Проверьте номер телефона',
    bad_email: 'Проверьте адрес почты',
    bad_company: 'Проверьте название компании',
    bad_field: 'Проверьте род деятельности',
    bad_dm: 'Отметьте, принимаете ли вы решения'
  };

  var FAIL_DEFAULT = 'Не получилось отправить. Попробуйте ещё раз или позвоните: +7 906 758-77-77';

  function showFail(err) {
    var reason = err && err.reason;

    if (window.console && console.error) {
      console.error('Заявка не отправлена:', (err && err.status) || 'сеть', reason || (err && err.message));
    }

    failMsg.textContent = (reason && FAIL_TEXT[reason]) || FAIL_DEFAULT;
    failMsg.hidden = false;
  }

  function showDone() {
    if (!modalBody || !modalDone) return;
    modalBody.hidden = true;
    modalDone.hidden = false;
    form.reset();
    var closeBtn = modalDone.querySelector('[data-close-form]');
    if (closeBtn) closeBtn.focus();

    // Возвращаем форму в исходное состояние при следующем открытии.
    setTimeout(function () {
      if (modal && modal.hidden) {
        modalBody.hidden = false;
        modalDone.hidden = true;
      }
    }, 400);
  }

  // Сбрасываем экран «отправлено» каждый раз, когда окно закрывают.
  if (modal) {
    var resetObserver = new MutationObserver(function () {
      if (modal.hidden && modalBody && modalDone) {
        modalBody.hidden = false;
        modalDone.hidden = true;
        failMsg.hidden = true;
        // Снимаем подсветку ошибок, чтобы форма открылась чистой.
        Array.prototype.forEach.call(form.querySelectorAll('.is-bad'), function (el) {
          el.classList.remove('is-bad');
        });
        Array.prototype.forEach.call(form.querySelectorAll('.frm__e'), function (el) {
          el.hidden = true;
        });
      }
    });
    resetObserver.observe(modal, { attributes: true, attributeFilter: ['hidden'] });
  }

})();
