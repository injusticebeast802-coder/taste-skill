"""Нарезка вертикального клипа 1080x1920 из записи Телемоста.

python3 render_clip.py <spec.json>
spec: {"src", "start", "end", "hook", "slug", "out_dir", "panel": "slide"|"banner",
       "words": optional path to cached word timings}
Хук: слова в *звёздочках* подсвечиваются оранжевым.
"""
import json, os, re, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beats as beatmod

S = "/tmp/claude-0/-home-user-taste-skill/ecd0e54a-8901-5d7e-bf23-b18c5b5b9442/scratchpad"
REPO = "/home/user/taste-skill"
FONTS = f"{S}/fonts"
W, H, FPS = 1080, 1920, 30
ORANGE_ASS = "&H1A7AFF&"   # BGR для #FF7A1A
ORANGE_HEX = "0xFF7A1A"
CTA_LEN = 4.0


def run(cmd):
    subprocess.run(cmd, check=True)


def prep_assets():
    os.makedirs(FONTS, exist_ok=True)
    for f in ["Inter-Bold.ttf", "Inter-SemiBold.ttf", "Inter-Medium.ttf", "Unbounded-Bold.ttf"]:
        dst = f"{FONTS}/{f}"
        if not os.path.exists(dst):
            run(["cp", f"{REPO}/analiz/shrifty/{f}", dst])
    av = f"{S}/assets/avatar.png"
    if not os.path.exists(av):
        os.makedirs(f"{S}/assets", exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-i", f"{REPO}/prompter-moscow/img/director.jpg",
             "-vf", "crop=150:150:310:72,scale=240:240,format=rgba,"
             "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-120,Y-120),118),255,0)'",
             av])
    return av


def words_for(spec, dur):
    cache = spec.get("words") or f"{spec['out_dir']}/{spec['slug']}.words.json"
    if os.path.exists(cache):
        return json.load(open(cache))
    wav = f"{spec['out_dir']}/{spec['slug']}.wav"
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(spec["start"]), "-t", str(dur), "-i", spec["src"],
         "-vn", "-ac", "1", "-ar", "16000", wav])
    from faster_whisper import WhisperModel
    w = wave.open(wav)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    m = WhisperModel(spec.get("model", "medium"), device="cpu", compute_type="int8", cpu_threads=4)
    segs, _ = m.transcribe(a, language="ru", beam_size=5, word_timestamps=True, vad_filter=False,
                           initial_prompt="Руслан Демин, Промптер, ГенИИ, нейровыдача, SMM, GEO, SEO, Яндекс Дзен.")
    out = []
    for s in segs:
        for x in s.words:
            out.append({"w": x.word.strip(), "s": round(x.start, 2), "e": round(x.end, 2)})
    merged = []
    for x in out:
        if merged and x["w"].startswith("-"):
            merged[-1]["w"] += x["w"]; merged[-1]["e"] = x["e"]
        else:
            merged.append(x)
    out = merged
    json.dump(out, open(cache, "w"), ensure_ascii=False, indent=0)
    return out


def chunk(words, max_chars=17):
    chunks, cur = [], []
    for i, x in enumerate(words):
        txt = " ".join(y["w"] for y in cur + [x])
        gap = x["s"] - cur[-1]["e"] if cur else 0
        if cur and (len(txt) > max_chars or gap > 0.45 or len(cur) >= 3):
            chunks.append(cur); cur = []
        cur.append(x)
        if re.search(r"[.!?…]$", x["w"]):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def esc(t):
    return t.replace("{", "(").replace("}", ")")


def build_ass(spec, words, dur, path):
    hook = esc(spec["hook"])
    hook = re.sub(r"\*(.+?)\*", lambda m: "{\\c" + ORANGE_ASS + "}" + m.group(1) + "{\\c&HFFFFFF&}", hook)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brand,Unbounded,40,&HFFFFFF&,&HFFFFFF&,&H000000&,&H80000000&,1,0,0,0,100,100,4,0,1,0,0,7,0,0,0,1
Style: Hook,Unbounded,70,&HFFFFFF&,&HFFFFFF&,&H101010&,&HA0000000&,1,0,0,0,100,100,0,0,1,0,4,7,70,70,0,1
Style: Sub,Inter,80,&HFFFFFF&,&HFFFFFF&,&H000000&,&H96000000&,1,0,0,0,100,100,0,0,1,0,5,5,60,60,0,1
Style: Name,Inter,44,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Role,Inter,31,&HC8C8C8&,&HFFFFFF&,&H000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
{beatmod.STYLES}Style: Cta,Unbounded,40,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    ev.append(f"Dialogue: 2,{ts(0)},{ts(dur)},Brand,,0,0,0,,{{\\pos(165,118)\\fad(300,0)}}ПРОМПТЕР")
    ev.append(f"Dialogue: 2,{ts(0)},{ts(dur)},Brand,,0,0,0,,{{\\an9\\pos(916,118)\\fad(300,0)}}ГенИИ")
    ev.append(f"Dialogue: 2,{ts(0)},{ts(dur)},Hook,,0,0,0,,{{\\an7\\fad(350,0)\\move(70,238,70,212,0,500)}}{hook}")
    plate_end = dur - CTA_LEN
    ev.append(f"Dialogue: 4,{ts(0)},{ts(dur)},Name,,0,0,0,,{{\\an7\\pos(0,0)\\1c{ORANGE_ASS}\\bord0\\shad0\\clip(60,1478,60,1484)\\t(0,{int(dur*1000)},\\clip(60,1478,1020,1484))\\p1}}m 60 1478 l 1020 1478 1020 1484 60 1484{{\\p0}}")
    ev.append(f"Dialogue: 2,{ts(0.6)},{ts(plate_end)},Name,,0,0,0,,{{\\pos(234,1352)\\fad(300,200)"
              f"\\move(250,1352,220,1352,0,350)}}Руслан Демин")
    ev.append(f"Dialogue: 2,{ts(0.75)},{ts(plate_end)},Role,,0,0,0,,{{\\pos(234,1408)\\fad(300,200)"
              f"\\move(250,1408,220,1408,0,350)}}управляющий партнёр «Промптер»")
    ev.append(f"Dialogue: 3,{ts(plate_end)},{ts(dur)},Cta,,0,0,0,,{{\\an5\\pos(540,1385)\\fad(250,0)"
              f"\\t(0,300,\\fscx100\\fscy100)\\fscx85\\fscy85}}Бесплатный разбор:{{\\c{ORANGE_ASS}}}\\N"
              f"кого нейросети советуют{{\\c&HFFFFFF&}}\\Nвместо вас — ссылка в профиле")
    def acc(t):
        return re.sub(r"\*(.+?)\*", lambda m: "{\\c" + ORANGE_ASS + "}" + m.group(1) + "{\\c&HFFFFFF&}", esc(t))
    ev += beatmod.render(spec.get("beats"), dur, acc)
    chunks = chunk(words)
    for k, ch in enumerate(chunks):
        c_start, c_end = ch[0]["s"], ch[-1]["e"] + 0.12
        if k + 1 < len(chunks):
            c_end = min(c_end, chunks[k + 1][0]["s"])
        for i, x in enumerate(ch):
            st = x["s"] if i else c_start
            en = ch[i + 1]["s"] if i + 1 < len(ch) else c_end
            parts = []
            for j, y in enumerate(ch):
                wtxt = esc(y["w"])
                if j == i:
                    parts.append("{\\c" + ORANGE_ASS + "}" + wtxt + "{\\c&HFFFFFF&}")
                else:
                    parts.append(wtxt)
            intro = "\\fad(120,0)\\move(540,1222,540,1205,0,160)" if i == 0 else ""
            ev.append(f"Dialogue: 1,{ts(st)},{ts(en)},Sub,,0,0,0,,{{\\an5{intro}{'' if intro else chr(92)+'pos(540,1205)'}}}" + " ".join(parts))
    open(path, "w").write(head + "\n".join(ev) + "\n")


def apply_cuts(spec):
    """Вырезает куски [a, b] (абсолютное время) и собирает новый исходник."""
    keep, cur = [], spec["start"]
    for a, b in sorted(spec["cuts"]):
        keep.append((cur, a)); cur = b
    keep.append((cur, spec["end"] + 0.8))
    out = f"{spec['out_dir']}/{spec['slug']}.cut.mp4"
    fc, n = "", len(keep)
    for i, (a, b) in enumerate(keep):
        fc += f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}];"
    fc += "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    run(["ffmpeg", "-v", "error", "-y", "-i", spec["src"], "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-c:a", "aac", "-b:a", "192k", out])
    speech = sum(b - a for a, b in keep) - 0.8
    return dict(spec, src=out, start=0.0, end=round(speech, 2))


def render(spec):
    if spec.get("cuts"):
        spec = apply_cuts(spec)
    av = prep_assets()
    mask = f"{S}/assets/panel_mask.png"
    if not os.path.exists(mask):
        run(["ffmpeg","-v","error","-y","-f","lavfi","-i","color=black:s=1000x562,format=gray","-frames:v","1","-vf",
             "geq=lum='if(gt(hypot(max(0,abs(X-499.5)-475),max(0,abs(Y-280.5)-256)),24),0,255)'",mask])
    os.makedirs(spec["out_dir"], exist_ok=True)
    speech = spec["end"] - spec["start"]
    dur = round(speech + 0.6, 2)
    words = words_for(spec, speech + 0.3)
    ass = f"{spec['out_dir']}/{spec['slug']}.ass"
    build_ass(spec, words, dur, ass)
    out = f"{spec['out_dir']}/{spec['slug']}.mp4"
    panel = spec.get("panel", "slide")
    if panel == "slide":
        panel_in = ["-ss", str(spec["start"]), "-t", str(dur), "-i", spec["src"]]
        panel_f = f"[1:v]crop=1520:855:8:30,scale=w='1000*(1+0.05*t/{dur})':h=-2:eval=frame,crop=1000:562,setsar=1,fps=30"
    elif panel == "beats":
        fon = f"{REPO}/prompter-moscow/presentation/konferenciya/fon.jpg"
        panel_in = ["-loop", "1", "-t", str(dur), "-i", fon]
        panel_f = ("[1:v]crop=1000:562:900:420,"
                   "drawbox=x=0:y=0:w=1000:h=562:color=0x1E140E@0.62:t=fill,"
                   f"drawbox=x=0:y=0:w=8:h=562:color={ORANGE_HEX}:t=fill,setsar=1,fps=30")
    else:
        # panel = "still@<секунда>": стоп-кадр слайда из записи, когда в кадре нет презентации
        at = float(panel.split("@")[1])
        still = f"{spec['out_dir']}/{spec['slug']}.still.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", spec["src"], "-frames:v", "1", still])
        panel_in = ["-loop", "1", "-t", str(dur), "-i", still]
        panel_f = f"[1:v]crop=1520:855:8:30,scale=w='1000*(1+0.05*t/{dur})':h=-2:eval=frame,crop=1000:562,setsar=1,fps=30"
    fc = (
        f"[0:v]scale=-1:2074,crop=1080:1920,"
        f"eq=brightness=-0.06,fps=30,format=yuv420p[bg];"
        f"{panel_f},format=rgba[pr];[5:v]format=gray[pm];[pr][pm]alphamerge,fade=t=in:st=0.15:d=0.45:alpha=1[pn];"
        f"[2:v]scale=140:140[av];[3:v]scale=72:72[lg];"
        f"[bg][pn]overlay=40:524:shortest=1[a];"
        f"[6:v]scale=-1:72[gl];"
        f"[a][lg]overlay=70:102[a2];[a2][gl]overlay=W-70-w:102[b];"
        f"[b][av]overlay=70:1322:enable='between(t,0.6,{dur - CTA_LEN})'[c];"
        f"[c]drawbox=x=60:y=1478:w=960:h=6:color=white@0.18:t=fill,"
                f"ass={ass}:fontsdir={FONTS}[v];"
        f"[4:a]atrim=0:{dur},asetpts=N/SR/TB,afade=t=in:d=0.06,afade=t=out:st={dur - 0.5}:d=0.5,"
        f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[au]"
    )
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-loop", "1", "-t", str(dur), "-i", f"{REPO}/prompter-moscow/presentation/konferenciya/fon.jpg",
           *panel_in,
           "-loop", "1", "-t", str(dur), "-i", av,
           "-loop", "1", "-t", str(dur), "-i", f"{REPO}/prompter-moscow/assets/logo.png",
           "-ss", str(spec["start"]), "-t", str(dur), "-i", spec["src"],
           "-loop", "1", "-t", str(dur), "-i", mask,
           "-loop", "1", "-t", str(dur), "-i", f"{REPO}/genii/assets/mark.png",
           "-filter_complex", fc, "-map", "[v]", "-map", "[au]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", str(dur), out]
    run(cmd)
    return out


if __name__ == "__main__":
    print(render(json.load(open(sys.argv[1]))))
