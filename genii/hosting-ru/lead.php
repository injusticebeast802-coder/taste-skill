<?php
/* =========================================================
   Приём заявки и отправка её в Телеграм.

   Замена файлу api/lead.js, который работал на серверных
   функциях Vercel. Логика повторена один в один: проверка
   источника запроса, ограничение частоты, очистка полей,
   отправка в Телеграм и дублирование на почту.

   Токен бота и номер чата лежат в config.php рядом с этим
   файлом. В браузер они не попадают: этот код выполняется
   на сервере, а сам config.php закрыт правилом в .htaccess.
   ========================================================= */

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function reply($code, $data) {
  http_response_code($code);
  echo json_encode($data, JSON_UNESCAPED_UNICODE);
  exit;
}

$configPath = __DIR__ . '/config.php';
if (!file_exists($configPath)) {
  error_log('Нет файла config.php рядом с lead.php');
  reply(500, array('ok' => false, 'error' => 'not_configured'));
}
require $configPath;

/* ---------- только POST ---------- */
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  header('Allow: POST');
  reply(405, array('ok' => false, 'error' => 'method_not_allowed'));
}

/* ---------- источник запроса ---------- */
function isAllowedOrigin($origin, $allowed) {
  if (!$origin) return false;

  $host = parse_url($origin, PHP_URL_HOST);
  if (!$host) return false;

  if (in_array($host, $allowed, true)) return true;

  // Локальная проверка на своём компьютере.
  if ($host === 'localhost' || $host === '127.0.0.1') return true;

  return false;
}

$origin = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
if (!isAllowedOrigin($origin, $ALLOWED_HOSTS)) {
  reply(403, array('ok' => false, 'error' => 'forbidden_origin'));
}

/* ---------- не больше трёх заявок в минуту с одного адреса ----------
   Счётчик хранится во временных файлах сервера: на обычном хостинге
   память между запросами не сохраняется, в отличие от Vercel. */
define('RATE_MAX', 3);
define('RATE_WINDOW', 60);

function clientIp() {
  if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
    $parts = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']);
    return trim($parts[0]);
  }
  if (!empty($_SERVER['HTTP_X_REAL_IP'])) return trim($_SERVER['HTTP_X_REAL_IP']);
  return isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
}

function rateLimited($ip) {
  $dir = sys_get_temp_dir() . '/genii-rate';
  if (!is_dir($dir)) @mkdir($dir, 0700, true);
  if (!is_dir($dir)) return false;   // не смогли создать — не блокируем заявку

  $file = $dir . '/' . sha1($ip) . '.txt';
  $now = time();

  $times = array();
  if (is_file($file)) {
    $raw = @file_get_contents($file);
    foreach (explode("\n", (string)$raw) as $line) {
      $t = (int)trim($line);
      if ($t && $now - $t < RATE_WINDOW) $times[] = $t;
    }
  }

  if (count($times) >= RATE_MAX) return true;

  $times[] = $now;
  @file_put_contents($file, implode("\n", $times), LOCK_EX);

  // Изредка подчищаем старые файлы, чтобы папка не разрасталась.
  if (mt_rand(1, 50) === 1) {
    foreach (glob($dir . '/*.txt') as $old) {
      if ($now - @filemtime($old) > 3600) @unlink($old);
    }
  }

  return false;
}

if (rateLimited(clientIp())) {
  reply(429, array('ok' => false, 'error' => 'too_many_requests'));
}

/* ---------- проверка настроек ----------
   Многоточие — то, что стоит в config.example.php вместо значений.
   Если его не заменили, Телеграм отвечает «неверный токен», и на сайте
   это выглядит как непонятный сбой отправки. Ловим случай сразу: так
   в журнале ошибок видно настоящую причину. */
$tokenSet  = defined('TG_TOKEN') && TG_TOKEN && TG_TOKEN !== '...';
$chatIdSet = defined('TG_CHAT_ID') && TG_CHAT_ID && TG_CHAT_ID !== '...';

if (!$tokenSet || !$chatIdSet) {
  error_log('TG_TOKEN или TG_CHAT_ID не заданы в config.php');
  reply(500, array('ok' => false, 'error' => 'not_configured'));
}

/* ---------- разбор тела запроса ---------- */
$raw = file_get_contents('php://input');
$body = json_decode($raw, true);
if (!is_array($body)) $body = array();

/* Убираем управляющие символы и переносы строк, схлопываем пробелы,
   режем по длине. Так в сообщение бота не попадёт мусор или разметка. */
function clean($value, $maxLen) {
  if (!is_string($value)) return '';
  $v = preg_replace('/[\x00-\x1F\x7F]/u', ' ', $value);
  $v = preg_replace('/\s+/u', ' ', $v);
  $v = trim($v);
  if (function_exists('mb_substr')) return mb_substr($v, 0, $maxLen, 'UTF-8');
  return substr($v, 0, $maxLen);
}

function field($body, $key) {
  return isset($body[$key]) ? $body[$key] : '';
}

$name    = clean(field($body, 'name'), 60);
$phone   = clean(field($body, 'phone'), 25);
$email   = clean(field($body, 'email'), 80);
$company = clean(field($body, 'company'), 80);
$fieldOf = clean(field($body, 'field'), 90);
$dm      = clean(field($body, 'dm'), 10);
$dm      = function_exists('mb_strtolower') ? mb_strtolower($dm, 'UTF-8') : strtolower($dm);
/* Откуда пришла заявка: с главной поле пустое, с отдельной страницы
   /zayavka приходит «zayavka».
   Поле необязательное, на проверку заявки не влияет. */
$source  = clean(field($body, 'source'), 40);

$digits = preg_replace('/\D/', '', $phone);
$nameLen = function_exists('mb_strlen') ? mb_strlen($name, 'UTF-8') : strlen($name);
$compLen = function_exists('mb_strlen') ? mb_strlen($company, 'UTF-8') : strlen($company);
$fieldLen = function_exists('mb_strlen') ? mb_strlen($fieldOf, 'UTF-8') : strlen($fieldOf);

if ($nameLen < 2)                                   reply(400, array('ok' => false, 'error' => 'bad_name'));
if (strlen($digits) < 10 || strlen($digits) > 12)   reply(400, array('ok' => false, 'error' => 'bad_phone'));
if (!preg_match('/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/u', $email)) reply(400, array('ok' => false, 'error' => 'bad_email'));
if ($compLen < 2)                                   reply(400, array('ok' => false, 'error' => 'bad_company'));
if ($fieldLen < 2)                                  reply(400, array('ok' => false, 'error' => 'bad_field'));
if ($dm !== 'да' && $dm !== 'нет')                  reply(400, array('ok' => false, 'error' => 'bad_dm'));

/* ---------- время по Москве ---------- */
function moscowTime() {
  try {
    $d = new DateTime('now', new DateTimeZone('Europe/Moscow'));
    return $d->format('d.m.Y, H:i') . ' МСК';
  } catch (Exception $e) {
    return gmdate('c');
  }
}
$stamp = moscowTime();
$emailPretty = prettyEmail($email);

/* Известные источники переводим на человеческий язык, незнакомые
   показываем как есть — они уже очищены функцией clean. */
function sourceLabel($value) {
  if ($value === '') return 'сайт';
  $known = array(
    'zayavka'  => 'страница заявки',
    'site'     => 'сайт',
    'email'    => 'письмо',
    'telegram' => 'телеграм',
  );
  $key = function_exists('mb_strtolower') ? mb_strtolower($value, 'UTF-8') : strtolower($value);
  return isset($known[$key]) ? $known[$key] : $value;
}
$sourcePretty = sourceLabel($source);

/* ---------- читаемый вид кириллического адреса ----------
   Поле с типом email заставляет браузер переписывать нелатинский домен
   в служебный вид: «абоба.рф» приходит как «xn--80aaca8d.xn--p1ai».
   Адрес рабочий, письмо по нему дойдёт, но менеджеру такое читать
   невозможно. Возвращаем домену человеческий вид.

   Сначала пробуем системную функцию, а если её нет — раскодируем сами.
   Расширение intl есть не на всяком хостинге, и заявка не должна
   зависеть от его наличия. */

function utf8FromCodepoint($cp) {
  if ($cp < 0x80)    return chr($cp);
  if ($cp < 0x800)   return chr(0xC0 | ($cp >> 6))  . chr(0x80 | ($cp & 0x3F));
  if ($cp < 0x10000) return chr(0xE0 | ($cp >> 12)) . chr(0x80 | (($cp >> 6) & 0x3F)) . chr(0x80 | ($cp & 0x3F));
  return chr(0xF0 | ($cp >> 18)) . chr(0x80 | (($cp >> 12) & 0x3F)) . chr(0x80 | (($cp >> 6) & 0x3F)) . chr(0x80 | ($cp & 0x3F));
}

/* Раскодирование одной части домена по описанию алгоритма Punycode. */
function punycodeLabel($label) {
  if (stripos($label, 'xn--') !== 0) return $label;

  $input = substr($label, 4);
  $base = 36; $tmin = 1; $tmax = 26; $skew = 38; $damp = 700;
  $n = 128; $i = 0; $bias = 72;
  $output = array();

  $delim = strrpos($input, '-');
  if ($delim !== false) {
    for ($j = 0; $j < $delim; $j++) $output[] = ord($input[$j]);
    $input = substr($input, $delim + 1);
  }

  $len = strlen($input);
  for ($pos = 0; $pos < $len;) {
    $oldi = $i; $w = 1;
    for ($k = $base; ; $k += $base) {
      if ($pos >= $len) return false;
      $c = ord($input[$pos++]);
      if ($c >= 0x30 && $c <= 0x39)      $digit = $c - 0x30 + 26;
      elseif ($c >= 0x61 && $c <= 0x7A)  $digit = $c - 0x61;
      elseif ($c >= 0x41 && $c <= 0x5A)  $digit = $c - 0x41;
      else return false;

      $i += $digit * $w;
      if ($k <= $bias) $t = $tmin;
      elseif ($k >= $bias + $tmax) $t = $tmax;
      else $t = $k - $bias;

      if ($digit < $t) break;
      $w *= ($base - $t);
    }

    $outLen = count($output) + 1;
    $delta = ($oldi == 0) ? intval(($i - $oldi) / $damp) : intval(($i - $oldi) / 2);
    $delta += intval($delta / $outLen);
    $k2 = 0;
    while ($delta > intval((($base - $tmin) * $tmax) / 2)) {
      $delta = intval($delta / ($base - $tmin));
      $k2 += $base;
    }
    $bias = $k2 + intval((($base - $tmin + 1) * $delta) / ($delta + $skew));

    $n += intval($i / $outLen);
    $i = $i % $outLen;
    array_splice($output, $i, 0, array($n));
    $i++;
  }

  $s = '';
  foreach ($output as $cp) $s .= utf8FromCodepoint($cp);
  return $s;
}

function prettyEmail($email) {
  $at = strrpos($email, '@');
  if ($at === false) return $email;

  $local = substr($email, 0, $at);
  $host  = substr($email, $at + 1);
  if (stripos($host, 'xn--') === false) return $email;

  if (function_exists('idn_to_utf8')) {
    $utf = defined('INTL_IDNA_VARIANT_UTS46')
      ? @idn_to_utf8($host, 0, INTL_IDNA_VARIANT_UTS46)
      : @idn_to_utf8($host);
    if (is_string($utf) && $utf !== '') return $local . '@' . $utf;
  }

  $parts = explode('.', $host);
  foreach ($parts as $k => $part) {
    $decoded = punycodeLabel($part);
    if ($decoded === false) return $email;   // не разобрали — оставляем как есть
    $parts[$k] = $decoded;
  }
  return $local . '@' . implode('.', $parts);
}

/* ---------- запрос к внешнему сервису ---------- */
function postJson($url, $payload, $headers = array()) {
  $ch = curl_init($url);
  curl_setopt_array($ch, array(
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => json_encode($payload, JSON_UNESCAPED_UNICODE),
    CURLOPT_HTTPHEADER     => array_merge(array('Content-Type: application/json'), $headers),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 15,
  ));
  $resp = curl_exec($ch);
  $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
  $err  = curl_error($ch);
  curl_close($ch);
  return array('code' => $code, 'body' => $resp, 'error' => $err);
}

/* ---------- Телеграм ---------- */
$text =
  "🆕 Новая заявка · genii-ai.ru\n" .
  "👤 Имя: $name\n" .
  "📞 Телефон: $phone\n" .
  "📧 Почта: $emailPretty\n" .
  "🏢 Компания: $company\n" .
  "📦 Род деятельности: $fieldOf\n" .
  "👔 ЛПР: $dm\n" .
  "📍 Источник: $sourcePretty\n" .
  "🕒 $stamp";

$tg = postJson(
  'https://api.telegram.org/bot' . TG_TOKEN . '/sendMessage',
  array(
    'chat_id' => TG_CHAT_ID,
    'text' => $text,
    'disable_web_page_preview' => true,
  )
);

if ($tg['error']) {
  error_log('Не удалось обратиться к Телеграму: ' . $tg['error']);
  reply(502, array('ok' => false, 'error' => 'telegram_unreachable'));
}
if ($tg['code'] < 200 || $tg['code'] >= 300) {
  error_log('Телеграм ответил ошибкой: ' . $tg['code'] . ' ' . $tg['body']);
  reply(502, array('ok' => false, 'error' => 'telegram_failed'));
}

/* ---------- дублирование на почту ----------
   Телеграм уже принял заявку, поэтому сбой почты не должен
   превращать принятую заявку в ошибку для посетителя. */
function sendMail($rows, $name, $company, $replyTo) {
  if (!defined('RESEND_API_KEY') || !RESEND_API_KEY) return null;
  if (!defined('MAIL_TO') || !MAIL_TO) return null;
  if (!defined('MAIL_FROM') || !MAIL_FROM) return null;

  $html = '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#111">'
        . '<h2 style="margin:0 0 16px">Новая заявка с сайта genii-ai.ru</h2>'
        . '<table cellpadding="6" style="border-collapse:collapse">';
  $plain = array();
  foreach ($rows as $label => $value) {
    $html .= '<tr>'
          .  '<td style="border:1px solid #ddd;background:#f6f6f6"><b>' . htmlspecialchars($label, ENT_QUOTES, 'UTF-8') . '</b></td>'
          .  '<td style="border:1px solid #ddd">' . htmlspecialchars($value, ENT_QUOTES, 'UTF-8') . '</td>'
          .  '</tr>';
    $plain[] = $label . ': ' . $value;
  }
  $html .= '</table></div>';

  $to = array();
  foreach (explode(',', MAIL_TO) as $addr) {
    $addr = trim($addr);
    if ($addr !== '') $to[] = $addr;
  }
  if (!$to) return null;

  $r = postJson(
    'https://api.resend.com/emails',
    array(
      'from'     => MAIL_FROM,
      'to'       => $to,
      'reply_to' => $replyTo,
      'subject'  => 'Заявка с genii-ai.ru: ' . $name . ', ' . $company,
      'text'     => implode("\n", $plain),
      'html'     => $html,
    ),
    array('Authorization: Bearer ' . RESEND_API_KEY)
  );

  if ($r['error']) {
    error_log('Не удалось обратиться к почтовому сервису: ' . $r['error']);
    return false;
  }
  if ($r['code'] < 200 || $r['code'] >= 300) {
    error_log('Письмо не отправлено: ' . $r['code'] . ' ' . $r['body']);
    return false;
  }
  return true;
}

$mailed = sendMail(
  array(
    'Имя'              => $name,
    'Телефон'          => $phone,
    'Почта'            => $emailPretty,
    'Компания'         => $company,
    'Род деятельности' => $fieldOf,
    'ЛПР'              => $dm,
    'Источник'         => $sourcePretty,
    'Время'            => $stamp,
  ),
  $name, $company, $email
);

reply(200, array('ok' => true, 'mailed' => $mailed));
