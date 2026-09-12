<?php
/* =========================================================
   Посредник между программой проверки и Телеграмом.

   ЗАЧЕМ. api.telegram.org у российских провайдеров закрыт, и
   программа на компьютере менеджера до него не достаёт. Хостинг
   достаёт: заявки с форм сайта уходят в того же бота и приходят.
   Значит, пусть программа обращается к своему же сайту, а сайт
   разговаривает с Телеграмом.

   Программа --> https://prompter-ai.moscow/tg.php --> api.telegram.org

   ЧТО СДЕЛАТЬ. В config.php добавить строку с длинным придуманным
   паролем и такой же вписать в config.ini программы:

       define('TG_RELAY_KEY', 'придумайте-строку-подлиннее');

   Пароль нужен, чтобы посредником не пользовался кто попало: без
   него любой, кто узнает адрес, смог бы читать ваши заявки и писать
   от имени бота. Токен при этом остаётся на хостинге и на компьютер
   менеджера не попадает вовсе.
   ========================================================= */

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
function otpravit($url, $post_telo, $post_tip, $popytok = 3, $svyaz = 8, $vsego = 120) {
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

    echo "Проверка связи с Телеграмом с этого хостинга\n";
    echo str_repeat('=', 44) . "\n\n";

    $adresa = @gethostbynamel('api.telegram.org');
    if (!$adresa) {
        echo "Имя api.telegram.org не разрешается в адрес.\n";
        echo "Это уже не блокировка, а настройки DNS у хостинга.\n";
        exit;
    }
    echo "Адреса api.telegram.org: " . implode(', ', $adresa) . "\n\n";

    foreach ($adresa as $ip) {
        $t = microtime(true);
        $ch = curl_init('https://api.telegram.org/bot' . TG_TOKEN . '/getMe');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 8);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_RESOLVE, array('api.telegram.org:443:' . $ip));
        $r = curl_exec($ch);
        $err = curl_error($ch);
        curl_close($ch);
        $sek = round(microtime(true) - $t, 1);

        if ($r === false) {
            echo sprintf("  %-16s НЕ ОТВЕЧАЕТ (%s сек): %s\n", $ip, $sek, $err);
        } else {
            $ok = (strpos($r, '"ok":true') !== false) ? 'работает' : 'ответил, но с отказом';
            echo sprintf("  %-16s %s (%s сек)\n", $ip, $ok, $sek);
        }
    }

    echo "\nОбычная отправка, как её делает посредник:\n";
    $r = otpravit('https://api.telegram.org/bot' . TG_TOKEN . '/getMe', null, '');
    if ($r['ok']) {
        echo "  получилось с попытки " . $r['popytka'] . ", адрес " . $r['ip'] . "\n";
    } else {
        echo "  не получилось за " . $r['popytka'] . " попытки: " . $r['oshibka'] . "\n";
    }

    echo "\nЕсли хотя бы один адрес работает — посредник справится.\n";
    echo "Если ни один — с этого хостинга до Телеграма хода нет,\n";
    echo "и заявки с форм уходят через какой-то другой путь.\n";
    exit;
}

$url = 'https://api.telegram.org/bot' . TG_TOKEN . '/' . $metod;

$parametry = $_GET;
unset($parametry['k'], $parametry['m']);
if ($parametry) {
    $url .= '?' . http_build_query($parametry);
}

/* getUpdates висит на линии, пока не придёт сообщение. Стандартные
   30 секунд PHP на такое не рассчитаны, поэтому снимаем ограничение
   и просим не обрывать работу, если программа отключилась. */
@set_time_limit(0);
ignore_user_abort(true);

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

$r = otpravit($url, $telo, $tip);

if (!$r['ok']) {
    otkaz(502, 'Хостинг не достучался до Телеграма за 3 попытки: ' . $r['oshibka']
             . '. Откройте этот же адрес с m=proverka вместо m=' . $metod
             . ' — покажет, какие адреса Телеграма отсюда отвечают.');
}

$otvet = $r['telo'];
$kod   = $r['kod'];

http_response_code($kod ? $kod : 200);
echo $otvet;
