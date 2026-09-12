<?php
/* =========================================================
   Посредник между программой проверки и Телеграмом.

   ЗАЧЕМ. api.telegram.org у российских провайдеров закрыт, и
   программа на компьютере менеджера до него не достаёт. Хостинг
   достаёт: заявки с форм сайта уходят в того же бота и приходят.
   Значит, пусть программа обращается к своему же сайту, а сайт
   разговаривает с Телеграмом.

   Программа --> https://genii-ai.ru/tg.php --> api.telegram.org

   ЧТО СДЕЛАТЬ. В config.php добавить строку с длинным придуманным
   паролем и такой же вписать в config.ini программы:

       define('TG_RELAY_KEY', 'придумайте-строку-подлиннее');

   Пароль нужен, чтобы посредником не пользовался кто попало: без
   него любой, кто узнает адрес, смог бы читать ваши заявки и писать
   от имени бота. Токен при этом остаётся на хостинге и на компьютер
   менеджера не попадает вовсе.
   ========================================================= */

/* Снимаем ограничение по времени первой же строкой. getUpdates висит
   на линии, пока не придёт сообщение, да и самопроверка перебирает
   адреса по очереди — в стандартные 30 секунд PHP это не влезает.
   Раньше строка стояла ниже самопроверки, и ту обрывало до первой
   напечатанной буквы: страница просто не открывалась. */
@set_time_limit(0);
ignore_user_abort(true);

require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function otkaz($code, $text) {
    http_response_code($code);
    echo json_encode(array('ok' => false, 'description' => $text),
                     JSON_UNESCAPED_UNICODE);
    exit;
}

if (!defined('TG_RELAY_KEY') || strlen(TG_RELAY_KEY) < 20) {
    otkaz(503, 'В config.php нет строки TG_RELAY_KEY или пароль короче 20 знаков. '
             . 'Добавьте её и впишите такой же пароль в config.ini программы.');
}

/* Пароль сверяем по времени постоянной длины: обычное сравнение
   отвечает тем быстрее, чем раньше расходятся строки, и по этой
   разнице пароль подбирают по одному знаку. */
$klyuch = isset($_GET['k']) ? $_GET['k'] : '';
if (!hash_equals(TG_RELAY_KEY, $klyuch)) {
    otkaz(403, 'Неверный пароль посредника.');
}

/* Только те три команды, которыми пользуется программа. Открывать
   весь Телеграм наружу незачем: с полным доступом чужой человек
   сможет и переписку бота вычитать, и рассылку с него сделать. */
$mozhno = array('getUpdates', 'sendMessage', 'sendPhoto', 'proverka');
$metod  = isset($_GET['m']) ? $_GET['m'] : '';
if (!in_array($metod, $mozhno, true)) {
    otkaz(404, 'Команда не разрешена: ' . $metod);
}

if (!defined('TG_TOKEN') || TG_TOKEN === '' || TG_TOKEN === '...') {
    otkaz(503, 'В config.php не заполнен TG_TOKEN.');
}

/* Отправка с повторами.

   api.telegram.org отвечает несколькими адресами, и с хостинга часть
   из них закрыта, а часть нет: заявки с форм уходят, а соседний
   запрос в ту же минуту не проходит. Одна попытка тут — как монетку
   бросить, поэтому пробуем по очереди и заново разрешаем имя каждый
   раз: curl берёт следующий адрес из списка.

   Только IPv4: на хостингах шестая версия часто объявлена, но наружу
   не работает, и попытка по ней съедает всё отведённое время. */
function otpravit($url, $post_telo, $post_tip, $popytok = 3, $svyaz = 25, $vsego = 150) {
    $posledn = '';
    for ($i = 1; $i <= $popytok; $i++) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, $svyaz);
        curl_setopt($ch, CURLOPT_TIMEOUT, $vsego);
        curl_setopt($ch, CURLOPT_FRESH_CONNECT, true);
        if (defined('CURL_IPRESOLVE_V4')) {
            curl_setopt($ch, CURLOPT_IPRESOLVE, CURL_IPRESOLVE_V4);
        }
        if ($post_telo !== null) {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $post_telo);
            if ($post_tip) {
                curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: ' . $post_tip));
            }
        }
        $otvet = curl_exec($ch);
        $kod   = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $adres = curl_getinfo($ch, CURLINFO_PRIMARY_IP);
        $oshibka = curl_error($ch);
        curl_close($ch);

        if ($otvet !== false) {
            return array('ok' => true, 'telo' => $otvet, 'kod' => $kod,
                         'ip' => $adres, 'popytka' => $i);
        }
        $posledn = $oshibka;
    }
    return array('ok' => false, 'oshibka' => $posledn, 'popytka' => $popytok);
}

/* ---------- Самопроверка ----------
   Открывается в браузере и показывает, какие адреса Телеграма с
   этого хостинга отвечают, а какие нет. Нужна, когда заявки уходят,
   а посредник говорит, что не достучался. */
if ($metod === 'proverka') {
    header('Content-Type: text/plain; charset=utf-8');

    /* Печатаем по ходу дела, а не в конце. Проверка идёт долго: на
       каждый закрытый адрес уходит несколько секунд ожидания. Если
       копить ответ в буфере, человек всё это время смотрит в пустое
       окно и решает, что страница не открылась. */
    @ini_set('output_buffering', 'off');
    @ini_set('zlib.output_compression', 'off');
    while (ob_get_level() > 0) { ob_end_flush(); }
    ob_implicit_flush(true);

    function stroka($t) { echo $t . "\n"; @flush(); }

    stroka('Проверка связи с Телеграмом с этого хостинга');
    stroka(str_repeat('=', 44));
    stroka('');

    $adresa = @gethostbynamel('api.telegram.org');
    if (!$adresa) {
        stroka('Имя api.telegram.org не разрешается в адрес.');
        stroka('Это уже не блокировка, а настройки DNS у хостинга.');
        exit;
    }
    stroka('Адреса api.telegram.org: ' . implode(', ', $adresa));
    stroka('');
    stroka('Пробуем каждый по отдельности, на каждый до 12 секунд:');

    $zhivye = 0;
    foreach ($adresa as $ip) {
        $t = microtime(true);
        $ch = curl_init('https://api.telegram.org/bot' . TG_TOKEN . '/getMe');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 12);
        curl_setopt($ch, CURLOPT_RESOLVE, array('api.telegram.org:443:' . $ip));
        $r = curl_exec($ch);
        $err = curl_error($ch);
        curl_close($ch);
        $sek = round(microtime(true) - $t, 1);

        if ($r === false) {
            stroka(sprintf('  %-16s НЕ ОТВЕЧАЕТ за %s сек: %s', $ip, $sek, $err));
        } else {
            $zhivye++;
            $ok = (strpos($r, '"ok":true') !== false)
                ? 'работает' : 'ответил, но Телеграм отказал (проверьте токен)';
            stroka(sprintf('  %-16s %s, за %s сек', $ip, $ok, $sek));
        }
    }

    /* Отправка ровно как у формы заявок: без отдельного срока на
       подключение, всего 15 секунд. Форма работает, посредник нет —
       значит разница именно в этих настройках, и её надо увидеть. */
    stroka('');
    stroka('Так отправляет форма заявок (15 секунд на всё):');
    $t = microtime(true);
    $ch = curl_init('https://api.telegram.org/bot' . TG_TOKEN . '/getMe');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    $r = curl_exec($ch);
    $err = curl_error($ch);
    $ip = curl_getinfo($ch, CURLINFO_PRIMARY_IP);
    curl_close($ch);
    $sek = round(microtime(true) - $t, 1);
    stroka($r === false
        ? sprintf('  не вышло за %s сек: %s', $sek, $err)
        : sprintf('  получилось за %s сек, адрес %s', $sek, $ip));

    stroka('');
    stroka('Так отправляет посредник (3 попытки, по 25 секунд):');
    $t = microtime(true);
    $r = otpravit('https://api.telegram.org/bot' . TG_TOKEN . '/getMe', null, '');
    $sek = round(microtime(true) - $t, 1);
    stroka($r['ok']
        ? sprintf('  получилось с попытки %d за %s сек, адрес %s',
                  $r['popytka'], $sek, $r['ip'])
        : sprintf('  не вышло за %s сек: %s', $sek, $r['oshibka']));

    stroka('');
    stroka('Итог: живых адресов ' . $zhivye . ' из ' . count($adresa) . '.');
    stroka('Если хоть один живой, а посредник не справился — дело в сроках,');
    stroka('поправлю. Если живых нет, а форма заявок при этом работает —');
    stroka('значит заявки уходят каким-то другим путём, буду искать каким.');
    exit;
}

$url = 'https://api.telegram.org/bot' . TG_TOKEN . '/' . $metod;

$parametry = $_GET;
unset($parametry['k'], $parametry['m']);
if ($parametry) {
    $url .= '?' . http_build_query($parametry);
}

$telo = null;
$tip  = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $tip = isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : '';

    if (stripos($tip, 'multipart/form-data') === 0) {
        /* Картинка отчёта. PHP такие запросы разбирает сам, и
           php://input к этому моменту уже пуст — поэтому собираем
           отправку заново из разобранных частей. Тип содержимого не
           передаём: curl поставит свой, с новой границей между
           частями. Со старой границей Телеграм не разберёт тело. */
        $telo = $_POST;
        foreach ($_FILES as $imya => $f) {
            if (isset($f['tmp_name']) && is_uploaded_file($f['tmp_name'])) {
                $telo[$imya] = new CURLFile(
                    $f['tmp_name'],
                    $f['type'] ? $f['type'] : 'application/octet-stream',
                    $f['name']
                );
            }
        }
        $tip = '';
    } else {
        $telo = file_get_contents('php://input');
    }
}

/* Сколько раз пробовать. Для getUpdates хватает одной попытки:
   программа опрашивает без конца, и неудача просто повторится через
   пару секунд. А вот отправку сообщения и картинки терять нельзя —
   там пробуем трижды.

   Считать надо не только удобство, но и терпение программы: она ждёт
   ответа ограниченное время, и три попытки по 25 секунд она уже не
   дожидается, бросая трубку раньше, чем мы успеваем ответить. */
$popytok = ($metod === 'getUpdates') ? 1 : 3;

$r = otpravit($url, $telo, $tip, $popytok);

if (!$r['ok']) {
    otkaz(502, 'Хостинг не достучался до Телеграма за ' . $popytok . ' поп.: ' . $r['oshibka']
             . '. Откройте этот же адрес с m=proverka вместо m=' . $metod
             . ' — покажет, какие адреса Телеграма отсюда отвечают.');
}

$otvet = $r['telo'];
$kod   = $r['kod'];

http_response_code($kod ? $kod : 200);
echo $otvet;
