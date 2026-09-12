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
$mozhno = array('getUpdates', 'sendMessage', 'sendPhoto');
$metod  = isset($_GET['m']) ? $_GET['m'] : '';
if (!in_array($metod, $mozhno, true)) {
    otkaz(404, 'Команда не разрешена: ' . $metod);
}

if (!defined('TG_TOKEN') || TG_TOKEN === '' || TG_TOKEN === '...') {
    otkaz(503, 'В config.php не заполнен TG_TOKEN.');
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

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 180);
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 20);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $tip = isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : '';

    if (stripos($tip, 'multipart/form-data') === 0) {
        /* Картинка отчёта. PHP такие запросы разбирает сам, и
           php://input к этому моменту уже пуст — поэтому собираем
           отправку заново из разобранных частей. */
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
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $telo);
    } else {
        $telo = file_get_contents('php://input');
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $telo);
        if ($tip) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: ' . $tip));
        }
    }
}

$otvet = curl_exec($ch);
if ($otvet === false) {
    $oshibka = curl_error($ch);
    curl_close($ch);
    otkaz(502, 'Хостинг не достучался до Телеграма: ' . $oshibka);
}

$kod = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

http_response_code($kod ? $kod : 200);
echo $otvet;
