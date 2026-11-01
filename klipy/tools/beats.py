"""Смысловые кадры (инфографика) в карточке клипа. Всё рисуется ASS-разметкой.

Карточка: x 40..1040, y 524..1086 (1000x562), центр (540, 805).
Виды кадров:
  word  — фраза: {"text"}
  count — счётчик 0→N: {"num", "suffix", "prefix", "cap"}
  dots  — сетка точек, часть подсвечена: {"total", "hi", "cols", "cap"}
  bars  — полосы-сравнение: {"title", "rows": [{"label", "val" 0..100, "txt", "hi"}]}
  flow  — цепочка шагов со стрелками: {"steps": [{"w", "t"}], "cap", "break": индекс шага, который перехватывают}
  list  — нумерованный список: {"title", "items": [{"w", "t"}]}
"""
import math

ORANGE = "&H1A7AFF&"
WHITE = "&HFFFFFF&"
GRAY = "&H5A5A5A&"
CX, CY = 540, 805
LEFT, TOP, RIGHT, BOTTOM = 100, 584, 980, 1036


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ease(p):
    return 1 - (1 - p) ** 3


def circle(r):
    k = 0.5523 * r
    return (f"m {r} 0 b {r + k} 0 {2 * r} {r - k} {2 * r} {r} b {2 * r} {r + k} {r + k} {2 * r} {r} {2 * r} "
            f"b {r - k} {2 * r} 0 {r + k} 0 {r} b 0 {r - k} {r - k} 0 {r} 0")


def rect(w, h, rad=0):
    if not rad:
        return f"m 0 0 l {w} 0 {w} {h} 0 {h}"
    k = 0.5523 * rad
    return (f"m {rad} 0 l {w - rad} 0 b {w - rad + k} 0 {w} {rad - k} {w} {rad} l {w} {h - rad} "
            f"b {w} {h - rad + k} {w - rad + k} {h} {w - rad} {h} l {rad} {h} b {rad - k} {h} 0 {h - rad + k} 0 {h - rad} "
            f"l 0 {rad} b 0 {rad - k} {rad - k} 0 {rad} 0")


def shape(t0, t1, x, y, path, color, alpha="&H00&", extra="", layer=2):
    return (f"Dialogue: {layer},{ts(t0)},{ts(t1)},Shape,,0,0,0,,{{\\an7\\pos({x},{y})\\bord0\\shad0"
            f"\\1c{color}\\1a{alpha}{extra}\\p1}}{path}{{\\p0}}")


def text(t0, t1, style, an, x, y, body, extra="", layer=3):
    return f"Dialogue: {layer},{ts(t0)},{ts(t1)},{style},,0,0,0,,{{\\an{an}\\pos({x},{y}){extra}}}{body}"


def pop(d=0):
    """Появление: прозрачность и лёгкий рост масштаба, без сдвига (плавнее, чем \\move)."""
    return f"\\fad(200,150)\\fscx92\\fscy92\\t({d},{d + 260},0.6,\\fscx100\\fscy100)"


def render(beats, dur, acc):
    ev = []
    for i, b in enumerate(beats or []):
        t0 = b["t"]
        t1 = beats[i + 1]["t"] if i + 1 < len(beats) else dur
        k = b["kind"]
        if k == "word":
            ev.append(text(t0, t1, "BWord", 5, CX, CY, acc(b["text"]), pop()))
        elif k == "count":
            n = b["num"]; pre = b.get("prefix", ""); suf = b.get("suffix", "")
            steps, span = 18, 0.75
            longest = len(f"{pre}{n}{suf}")
            fs = min(200, int(860 / (longest * 0.48)))
            for s in range(steps + 1):
                a = t0 + span * s / steps
                z = t0 + span * (s + 1) / steps if s < steps else t1
                val = round(n * ease(s / steps))
                ev.append(text(a, z, "BNum", 5, CX, CY - 60, f"{pre}{val}{suf}",
                               f"\\fs{fs}" + ("\\fad(150,150)" if s in (0, steps) else "")))
            ev.append(text(t0 + 0.3, t1, "BCap", 5, CX, CY + 105, acc(b["cap"]), pop()))
        elif k == "dots":
            total, hi, cols = b["total"], b["hi"], b.get("cols", 10)
            rows = math.ceil(total / cols)
            area_w, area_h = 820, 300
            step = min(area_w / cols, area_h / rows)
            r = step * 0.34
            x0 = CX - step * cols / 2
            block_h = rows * step + 26 + 100
            y0 = max(TOP + 10, CY - block_h / 2)
            for d in range(total):
                cx = x0 + (d % cols) * step + step / 2 - r
                cy = y0 + (d // cols) * step + step / 2 - r
                a = t0 + 0.012 * d if total > 30 else t0 + 0.09 * d
                col = ORANGE if d < hi else GRAY
                ev.append(shape(a, t1, round(cx, 1), round(cy, 1), circle(round(r, 1)), col,
                                extra="\\fad(160,150)"))
            ev.append(text(t0 + 0.4, t1, "BCap", 8, CX, y0 + rows * step + 26, acc(b["cap"]), pop()))
        elif k == "bars":
            ev.append(text(t0, t1, "BTitle", 7, LEFT, TOP, acc(b.get("title", "")), pop()))
            maxw = RIGHT - LEFT
            for j, row in enumerate(b["rows"]):
                y = TOP + 80 + j * 165
                a = t0 + 0.25 + 0.45 * j
                w = max(8, round(maxw * row["val"] / 100))
                col = ORANGE if row.get("hi") else "&HB4B4B4&"
                ev.append(text(a, t1, "BLabel", 7, LEFT, y, row["label"], "\\fad(180,150)"))
                ev.append(shape(a, t1, LEFT, y + 52, rect(maxw, 38, 19), "&H303030&", extra="\\fad(180,150)"))
                ev.append(shape(a, t1, LEFT, y + 52, rect(w, 38, 19), col,
                                extra=f"\\fad(180,150)\\clip({LEFT},{y + 52},{LEFT},{y + 90})"
                                      f"\\t(0,700,0.5,\\clip({LEFT},{y + 52},{LEFT + w},{y + 90}))"))
                ev.append(text(a + 0.5, t1, "BValHi" if row.get("hi") else "BVal", 7, LEFT, y + 102, acc(row["txt"]),
                               "\\fad(200,150)"))
        elif k == "flow":
            steps = b["steps"]; n = len(steps)
            gap = 60
            bw = min(300, (RIGHT - LEFT - (n - 1) * gap) // n)
            bh = 140 if n <= 2 else 120
            total_w = n * bw + (n - 1) * gap
            x = CX - total_w // 2
            y = CY - bh // 2 - 40
            brk = b.get("break")
            for j, st in enumerate(steps):
                a = max(st.get("t", t0 + 0.4 * j), t0)
                bx = x + j * (bw + gap)
                col = ORANGE if j == brk else "&H2A2A2A&"
                ev.append(shape(a, t1, bx, y, rect(bw, bh, 22), col, extra="\\fad(180,150)"))
                ev.append(text(a, t1, "BStep", 5, bx + bw // 2, y + bh // 2, st["w"],
                               "\\fad(180,150)" + ("\\fs40" if n <= 2 else "")))
                if j:
                    ax = bx - gap + 10
                    ev.append(shape(a - 0.1, t1, ax, y + bh // 2 - 3, rect(gap - 32, 6), "&H8C8C8C&", extra="\\fad(150,150)"))
                    ev.append(shape(a - 0.1, t1, ax + gap - 34, y + bh // 2 - 13, "m 0 0 l 20 13 0 26", "&H8C8C8C&",
                                    extra="\\fad(150,150)"))
            if b.get("cap"):
                cap_t = b.get("cap_t", t0 + 0.4 * n)
                ev.append(text(max(cap_t, t0), t1, "BCap", 8, CX, y + bh + 50, acc(b["cap"]), pop()))
        elif k == "list":
            ev.append(text(t0, t1, "BTitle", 7, LEFT, TOP, acc(b.get("title", "")), pop()))
            for j, it in enumerate(b["items"]):
                a = max(it.get("t", t0 + 0.3 * (j + 1)), t0)
                y = TOP + 72 + j * 88
                ev.append(shape(a, t1, LEFT, y, circle(26), ORANGE, extra="\\fad(180,150)"))
                ev.append(text(a, t1, "BNumS", 5, LEFT + 26, y + 26, str(j + 1), "\\fad(180,150)"))
                ev.append(text(a, t1, "BList", 4, LEFT + 78, y + 26, acc(it["w"]), "\\fad(180,150)"))
    return ev


STYLES = """Style: Shape,Inter,20,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: BNum,Unbounded,200,&H1A7AFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,-4,0,1,0,0,5,0,0,0,1
Style: BCap,Inter,46,&HE6E6E6&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,5,110,110,0,1
Style: BWord,Unbounded,74,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,5,110,110,0,1
Style: BList,Unbounded,50,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1
Style: BNumS,Unbounded,30,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: BTitle,Inter,40,&HB4B4B4&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: BLabel,Unbounded,40,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: BVal,Inter,36,&HB4B4B4&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: BValHi,Inter,36,&H1A7AFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: BStep,Unbounded,34,&HFFFFFF&,&HFFFFFF&,&H000000&,&H00000000&,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
"""
