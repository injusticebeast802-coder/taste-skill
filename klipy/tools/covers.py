"""Обложки для VK Клипов: заголовок клипа + Руслан в полный рост на фирменном фоне."""
import glob, json, os, re, subprocess
from PIL import Image, ImageDraw, ImageFilter
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "/home/user/taste-skill"
W, H = 1080, 1920
bg = Image.open(f"{REPO}/prompter-moscow/presentation/konferenciya/fon.jpg").convert("RGB")
sc = H / bg.height * 1.08
bg = bg.resize((int(bg.width * sc), int(bg.height * sc)))
bg = bg.crop(((bg.width - W) // 2, 0, (bg.width - W) // 2 + W, H)).point(lambda v: int(v * 0.85))
glow = Image.new("L", (W, H), 0)
ImageDraw.Draw(glow).ellipse((140, 1050, 940, 1850), fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(160)).point(lambda v: int(v * 0.5))
base = Image.composite(Image.new("RGB", (W, H), (255, 122, 26)), bg, glow)
cut = Image.open(f"{S}/assets/ruslan_cut.png")
base.paste(cut, ((W - cut.width) // 2, H - cut.height), cut)
grad = Image.new("L", (1, 420)); [grad.putpixel((0, y), int(255 * (y / 420) ** 1.6)) for y in range(420)]
grad = grad.resize((W, 420))
base.paste(Image.new("RGB", (W, 420), (8, 6, 5)), (0, H - 420), grad)
for path, x, h in [(f"{REPO}/prompter-moscow/assets/logo.png", 70, 72), (f"{REPO}/genii/assets/mark.png", None, 72)]:
    lg = Image.open(path).convert("RGBA"); lg = lg.resize((int(lg.width * h / lg.height), h), Image.LANCZOS)
    base.paste(lg, (x if x is not None else W - 70 - lg.width, 102), lg)
base.save(f"{S}/clips/covers/_base.png")

OR = "&H1A7AFF&"
def acc(t):
    return re.sub(r"\*(.+?)\*", lambda m: "{\\1c" + OR + "}" + m.group(1) + "{\\1c&HFFFFFF&}", t)
head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brand,Unbounded,40,&HFFFFFF&,&HFFFFFF&,&H000000&,&H80000000&,1,0,0,0,100,100,4,0,1,0,0,7,0,0,0,1
Style: Hook,Unbounded,104,&HFFFFFF&,&HFFFFFF&,&H000000&,&H64000000&,1,0,0,0,100,100,-1,0,1,0,6,7,70,70,0,1
Style: Name,Inter,50,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,2,0,0,0,1
Style: Role,Inter,36,&HC8C8C8&,&HFFFFFF&,&H000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,2,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for spec in sorted(glob.glob(f"{S}/clips/[01][0-9]_*.json")):
    j = json.load(open(spec)); slug = os.path.basename(spec)[:-5]
    ev = [
        "Dialogue: 0,0:00:00.00,0:00:05.00,Brand,,0,0,0,,{\\pos(165,118)}ПРОМПТЕР",
        "Dialogue: 0,0:00:00.00,0:00:05.00,Brand,,0,0,0,,{\\an9\\pos(916,118)}ГенИИ",
        f"Dialogue: 0,0:00:00.00,0:00:05.00,Hook,,0,0,0,,{{\\pos(70,300)}}{acc(j['hook'])}",
        "Dialogue: 0,0:00:00.00,0:00:05.00,Name,,0,0,0,,{\\pos(540,1800)}Руслан Демин",
        "Dialogue: 0,0:00:00.00,0:00:05.00,Role,,0,0,0,,{\\pos(540,1856)}управляющий партнёр «Промптер»",
    ]
    ass = f"{S}/clips/covers/{slug}.ass"
    open(ass, "w").write(head + "\n".join(ev) + "\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{S}/clips/covers/_base.png",
                    "-vf", f"ass={ass}:fontsdir={S}/fonts", "-frames:v", "1",
                    f"{S}/clips/covers/{slug}.jpg"], check=True)
    os.remove(ass); print(slug)
