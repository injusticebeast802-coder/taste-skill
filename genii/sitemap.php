<?php
/* =========================================================
   Карта сайта. Собирается на лету, чтобы каждая новая статья
   попадала в неё сама: их выходит по две в неделю, и править
   файл руками пришлось бы каждый раз.

   Адрес /sitemap.xml перенаправлен сюда правилом в .htaccess —
   для поисковиков ничего не меняется.
   ========================================================= */
header('Content-Type: application/xml; charset=UTF-8');

$SITE = 'https://genii-ai.ru';
$DIR  = __DIR__ . '/stati';

/* Постоянные страницы. Политика и страница заявки сюда не идут:
   у них стоит запрет на индексирование. */
$urls = array(
  array('loc' => $SITE . '/',      'freq' => 'monthly', 'pri' => '1.0',
        'mod' => date('Y-m-d', @filemtime(__DIR__ . '/index.html') ?: time())),
  array('loc' => $SITE . '/stati', 'freq' => 'weekly',  'pri' => '0.8', 'mod' => date('Y-m-d')),
);

$newest = '';
if (is_dir($DIR)) {
  foreach (scandir($DIR) as $file) {
    if ($file[0] === '.' || $file[0] === '_') continue;
    if (substr($file, -5) !== '.html') continue;

    $html = file_get_contents($DIR . '/' . $file);
    $date = '';
    if ($html !== false && preg_match('~<meta\s+name="date"\s+content="([0-9]{4}-[0-9]{2}-[0-9]{2})"~i', $html, $m)) {
      $date = $m[1];
    }
    if ($date === '') $date = date('Y-m-d', filemtime($DIR . '/' . $file));
    if ($date > $newest) $newest = $date;

    $urls[] = array(
      'loc'  => $SITE . '/stati/' . rawurlencode(substr($file, 0, -5)),
      'freq' => 'yearly',
      'pri'  => '0.6',
      'mod'  => $date
    );
  }
}

/* У раздела статей дата — по самой свежей статье в нём. */
if ($newest !== '') $urls[1]['mod'] = $newest;

echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
foreach ($urls as $u) {
  echo "  <url>\n";
  echo '    <loc>' . htmlspecialchars($u['loc'], ENT_QUOTES, 'UTF-8') . "</loc>\n";
  echo '    <lastmod>' . $u['mod'] . "</lastmod>\n";
  echo '    <changefreq>' . $u['freq'] . "</changefreq>\n";
  echo '    <priority>' . $u['pri'] . "</priority>\n";
  echo "  </url>\n";
}
echo '</urlset>' . "\n";
