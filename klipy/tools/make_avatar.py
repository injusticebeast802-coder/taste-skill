import sys
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from rembg import remove, new_session
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
sess = new_session("u2net_human_seg")
cut = remove(im, session=sess)                      # RGBA, фон прозрачный
# кадр: голова и плечи
x, y, s = 330, 0, 430
cut = cut.crop((x, y, x + s, y + s)).resize((560, 560), Image.LANCZOS)
rgb = cut.convert("RGB")
rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
rgb = ImageEnhance.Color(rgb).enhance(0.9)
rgb = ImageEnhance.Sharpness(rgb).enhance(1.3)
r, g, b = rgb.split()
r = r.point(lambda v: min(255, int(v * 1.04))); b = b.point(lambda v: int(v * 0.95))
rgb = Image.merge("RGB", (r, g, b)); cut = Image.merge("RGBA", (*rgb.split(), cut.split()[3]))
N = 560
# фон круга: тёмный с оранжевым свечением снизу-справа
bg = Image.new("RGB", (N, N), (22, 16, 12))
glow = Image.new("L", (N, N), 0); ImageDraw.Draw(glow).ellipse((N*0.35, N*0.3, N*1.2, N*1.15), fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(90))
bg = Image.composite(Image.new("RGB", (N, N), (255, 122, 26)), bg, glow.point(lambda v: int(v * 0.55)))
bg.paste(cut, (0, 0), cut)
mask = Image.new("L", (N, N), 0); ImageDraw.Draw(mask).ellipse((10, 10, N - 10, N - 10), fill=255)
res = Image.new("RGBA", (N, N), (0, 0, 0, 0)); res.paste(bg, (0, 0), mask)
d = ImageDraw.Draw(res); d.ellipse((5, 5, N - 5, N - 5), outline=(255, 122, 26, 255), width=10)
res.resize((280, 280), Image.LANCZOS).save(out)
