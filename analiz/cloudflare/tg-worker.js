/* =========================================================
   Посредник между программой проверки и Телеграмом,
   работающий на Cloudflare.

   ЗАЧЕМ. До api.telegram.org не достают ни компьютер менеджера, ни
   хостинг сайта: в России адрес закрыт. Cloudflare достаёт — их сеть
   стоит по всему миру, и запрос уходит наружу.

   Программа --> этот работник --> api.telegram.org

   Бесплатно: 100 000 запросов в сутки, нам нужно около тысячи.

   ЧТО ЗАВЕСТИ в настройках работника (Settings -> Variables), все
   строки — как Secret, чтобы не отображались:
       TG_TOKEN        токен бота отчётов, вида 1234567890:AAG...
       TG_RELAY_KEY    тот же пароль, что в config.ini программы
       TG_TOKEN_PRIYOM токен бота-приёмщика заявок — если он тоже
                       ходит через работника
   ========================================================= */

/* getMe только называет имя бота и ничего не меняет. Нужен, чтобы
   программа при запуске сказала, за кого её принимает телеграм: без
   этого перепутанный токен выглядит как полная тишина. */
// editMessageText нужен, чтобы бот писал ход проверки в одно
// сообщение и правил его, а не сыпал десяток отдельных.
// getChatMember, getChatAdministrators и answerCallbackQuery нужны
// боту-приёмщику: он спрашивает телеграм, подписан ли человек на
// канал, и снимает кружок ожидания с нажатой кнопки.
const MOZHNO = ['getUpdates', 'sendMessage', 'editMessageText',
                'sendPhoto', 'getMe', 'getChatMember',
                'getChatAdministrators', 'answerCallbackQuery'];

export default {
  async fetch(request, env) {
    const otkaz = (kod, text) =>
      new Response(JSON.stringify({ ok: false, description: text }), {
        status: kod,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      });

    if (!env.TG_TOKEN || !env.TG_RELAY_KEY) {
      return otkaz(503, 'В настройках работника нет TG_TOKEN или TG_RELAY_KEY.');
    }

    const adres = new URL(request.url);
    const klyuch = adres.searchParams.get('k') || '';

    /* Сверяем пароль по времени постоянной длины: обычное сравнение
       отвечает тем быстрее, чем раньше расходятся строки, и по этой
       разнице пароль подбирают по одному знаку. */
    const a = new TextEncoder().encode(klyuch);
    const b = new TextEncoder().encode(env.TG_RELAY_KEY);
    let raznica = a.length ^ b.length;
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      raznica |= (a[i] || 0) ^ (b[i] || 0);
    }
    if (raznica !== 0) return otkaz(403, 'Неверный пароль посредника.');

    const metod = adres.searchParams.get('m') || '';
    if (!MOZHNO.includes(metod)) {
      return otkaz(404, 'Команда не разрешена: ' + metod);
    }

    /* Чей токен подставить. Ботов два: один считает отчёты, другой
       принимает заявки от клиентов. Работник у них общий, токены
       разные, и перепутать их нельзя: человек спросит у одного бота,
       а ответит ему другой. Без b= берём бота отчётов — так было до
       появления второго, и старые настройки менять не нужно. */
    const bot = adres.searchParams.get('b') || '';
    let token = env.TG_TOKEN;
    if (bot === 'priyom') {
      if (!env.TG_TOKEN_PRIYOM) {
        return otkaz(503, 'В настройках работника нет TG_TOKEN_PRIYOM — '
                        + 'токена бота-приёмщика.');
      }
      token = env.TG_TOKEN_PRIYOM;
    } else if (bot !== '' && bot !== 'otchet') {
      return otkaz(404, 'Неизвестный бот: ' + bot);
    }

    /* Остальные параметры передаём Телеграму как есть: в них
       номер последнего сообщения и время ожидания. */
    const hvost = new URLSearchParams(adres.searchParams);
    hvost.delete('k');
    hvost.delete('m');
    hvost.delete('b');
    const stroka = hvost.toString();

    let cel = 'https://api.telegram.org/bot' + token + '/' + metod;
    if (stroka) cel += '?' + stroka;

    /* Тело и его тип передаём нетронутыми. Картинка отчёта идёт
       многочастной посылкой, и разбирать её здесь незачем: граница
       между частями описана в заголовке, который мы и пересылаем. */
    const nastrojki = { method: request.method };
    if (request.method === 'POST') {
      /* Тело читаем целиком, а не передаём ручейком. Ручеёк тут
         ничего не выигрывает — картинка отчёта весит около сотни
         килобайт, — зато требует особой оговорки при пересылке и
         разваливается на ней. */
      nastrojki.body = await request.arrayBuffer();
      const tip = request.headers.get('Content-Type');
      if (tip) nastrojki.headers = { 'Content-Type': tip };
    }

    try {
      const otvet = await fetch(cel, nastrojki);
      return new Response(otvet.body, {
        status: otvet.status,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      });
    } catch (e) {
      return otkaz(502, 'Работник не достучался до Телеграма: ' + e.message);
    }
  },
};
