<?php
/* =========================================================
   Полезные статьи — список.

   Файл лежит внутри папки stati и называется index.php, поэтому
   адрес /stati/ отдаёт именно его — без правил переадресации.
   Раньше страница лежала в корне под именем stati.php, а рядом была
   папка stati с тем же именем. Apache видел папку, дописывал к
   адресу косую черту, и все относительные ссылки съезжали на
   уровень вниз: стили, шрифты и картинки переставали находиться,
   страница открывалась голой разметкой.

   Страница собирается сама: она читает свою папку и берёт из
   каждого файла название и дату. Чтобы добавить статью, достаточно
   положить туда один файл — правок здесь не нужно.

   Файлы, имя которых начинается с подчёркивания, пропускаются:
   так лежит образец _shablon.html.

   Почему не простой html: список нужен поисковикам и нейросетям
   в готовом виде, а не собранным скриптом уже в браузере. PHP на
   хостинге и так работает — на нём принимаются заявки.
   ========================================================= */

$DIR = __DIR__;
$articles = array();

if (is_dir($DIR)) {
  foreach (scandir($DIR) as $file) {
    if ($file[0] === '.' || $file[0] === '_') continue;
    if (substr($file, -5) !== '.html') continue;

    $html = file_get_contents($DIR . '/' . $file);
    if ($html === false) continue;

    /* Название берём из <title>, отрезая хвост « — ГенИИ». */
    $title = '';
    if (preg_match('~<title>(.*?)</title>~is', $html, $m)) {
      $title = trim(preg_replace('~\s*[—-]\s*ГенИИ\s*$~u', '', html_entity_decode($m[1], ENT_QUOTES, 'UTF-8')));
    }
    if ($title === '') $title = $file;

    /* Дата — из <meta name="date" content="2026-09-15">. */
    $date = '';
    if (preg_match('~<meta\s+name="date"\s+content="([0-9]{4}-[0-9]{2}-[0-9]{2})"~i', $html, $m)) {
      $date = $m[1];
    }

    /* Краткое описание — из обычного meta description. */
    $lead = '';
    if (preg_match('~<meta\s+name="description"\s+content="(.*?)"~is', $html, $m)) {
      $lead = trim(html_entity_decode($m[1], ENT_QUOTES, 'UTF-8'));
    }

    $articles[] = array('file' => $file, 'title' => $title, 'date' => $date, 'lead' => $lead);
  }
}

/* Сначала свежие. Статьи без даты уходят вниз. */
usort($articles, function ($a, $b) {
  if ($a['date'] === $b['date']) return strcmp($a['title'], $b['title']);
  return strcmp($b['date'], $a['date']);
});

function ruDate($iso) {
  if ($iso === '') return '';
  $months = array(1=>'января','февраля','марта','апреля','мая','июня',
                  'июля','августа','сентября','октября','ноября','декабря');
  $t = strtotime($iso);
  if ($t === false) return $iso;
  return (int)date('j', $t) . ' ' . $months[(int)date('n', $t)] . ' ' . date('Y', $t);
}

function e($s) { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }

$count = count($articles);
?><!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Полезные статьи — ГенИИ</title>
<meta name="description" content="Статьи «ГенИИ» о продвижении бизнеса в нейровыдаче и поиске: как работает GEO, почему нейросети называют одни компании и не называют другие. Две статьи в неделю.">
<link rel="canonical" href="https://genii-ai.ru/stati/">
<meta name="theme-color" content="#0A0A0C">
<meta name="color-scheme" content="dark">

<meta property="og:type" content="website">
<meta property="og:site_name" content="ГенИИ">
<meta property="og:url" content="https://genii-ai.ru/stati/">
<meta property="og:title" content="Полезные статьи — ГенИИ">
<meta property="og:description" content="О продвижении бизнеса в нейровыдаче и поиске. Две статьи в неделю.">
<meta property="og:locale" content="ru_RU">
<meta property="og:image" content="https://genii-ai.ru/assets/og.png?v=1">

<link rel="icon" type="image/png" href="../assets/favicon-64.png">
<link rel="apple-touch-icon" href="../assets/icon-180.png">
<link rel="stylesheet" href="../style.css?v=1">
<?php if ($count): ?>
<script type="application/ld+json">
<?php
  $items = array();
  foreach ($articles as $i => $a) {
    $items[] = array(
      '@type' => 'ListItem',
      'position' => $i + 1,
      'url' => 'https://genii-ai.ru/stati/' . substr($a['file'], 0, -5),
      'name' => $a['title']
    );
  }
  echo json_encode(array(
    '@context' => 'https://schema.org',
    '@type' => 'ItemList',
    'name' => 'Полезные статьи «ГенИИ»',
    'itemListElement' => $items
  ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
?>
</script>
<?php endif; ?>
</head>
<body>

<header class="hdr">
  <div class="wrap hdr__in">
    <a class="logo" href="../index.html" aria-label="ГенИИ, на главную">
      <img class="logo__mark" src="../assets/mark.png" alt="" width="34" height="34">
      <span class="logo__txt">Ген<b>ИИ</b></span>
    </a>
    <a class="arts__back arts__back--hdr" href="../index.html">На главную</a>
  </div>
</header>

<main class="wrap arts">
  <h1 class="h2">Полезные статьи</h1>
  <p class="lead">Пишем о том, как бизнес попадает в ответы нейросетей и в поиск: что нейросети считывают, почему называют одни компании и не называют другие, что с этим делать. Две статьи в неделю. Они же выходят в нашем канале на Яндекс Дзене.</p>

<?php if ($count): ?>
  <ul class="arts__list">
<?php foreach ($articles as $a): ?>
    <li class="arts__item">
      <a class="arts__link" href="<?= e(substr($a['file'], 0, -5)) ?>">
        <span class="arts__t"><?= e($a['title']) ?></span>
<?php if ($a['date'] !== ''): ?>
        <time class="arts__date" datetime="<?= e($a['date']) ?>"><?= e(ruDate($a['date'])) ?></time>
<?php endif; ?>
      </a>
<?php if ($a['lead'] !== ''): ?>
      <p class="arts__lead"><?= e($a['lead']) ?></p>
<?php endif; ?>
    </li>
<?php endforeach; ?>
  </ul>
<?php else: ?>
  <div class="arts__soon">
    <svg class="ic ic--lg" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 6A1.5 1.5 0 0 1 5 4.5h11A1.5 1.5 0 0 1 17.5 6v11a1.5 1.5 0 0 0 1.5 1.5H5A1.5 1.5 0 0 1 3.5 17V6z"/><path d="M17.5 9H20a.5.5 0 0 1 .5.5V17a1.5 1.5 0 0 1-3 0"/><path d="M6.5 8h8M6.5 11.5h8M6.5 15h5"/></svg>
    <p class="arts__soon-t">Скоро здесь появятся статьи</p>
    <p class="arts__soon-d">Первые выйдут в ближайшие недели, дальше — по две в неделю. Названия и даты появятся на этой странице сами.</p>
  </div>
<?php endif; ?>

  <a class="arts__back" href="../index.html">Вернуться на главную</a>
</main>

<footer class="ftr">
  <div class="wrap ftr__in">
    <p class="ftr__c">
      <img class="ftr__mark" src="../assets/mark.png" alt="" width="24" height="24">
      © <span id="year">2026</span> ГенИИ
    </p>
    <a class="ftr__phone" href="tel:+79067587777">+7 906 758-77-77</a>
    <a class="ftr__mail" href="mailto:geniiai@mail.ru">geniiai@mail.ru</a>
    <a class="ftr__site" href="https://genii-ai.ru">genii-ai.ru</a>
    <p class="ftr__place">Moscow, Skolkovo</p>
    <a class="ftr__pp" href="../privacy.html">Политика обработки персональных данных</a>
  </div>
</footer>

<script src="../script.js?v=1"></script>
</body>
</html>
