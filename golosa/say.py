"""Озвучка текста русскими голосами с эффектами.

  python3 say.py "Привет, я андроид." --voice denis --fx android -o out.mp3
  python3 say.py --list

Голоса:
  Piper:  denis, dmitri (лицензия CC0, можно в рекламу), irina (лицензия не указана),
          ruslan (только некоммерческое использование).
  Silero: aidar, baya, kseniya, xenia, eugene (только некоммерческое использование).
Модели лежат в models/; скачать заново: bash download_models.sh
"""
import argparse, os, subprocess, sys, tempfile, wave

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = f"{HERE}/models"
PIPER = ["denis", "dmitri", "irina", "ruslan"]
SILERO = ["aidar", "baya", "kseniya", "xenia", "eugene"]

# Эффекты ffmpeg. rate = во сколько раз поднять тон (через частоту дискретизации)
FX = {
    "clean":    "Чистый голос",
    "android":  "Андроид: металл, лёгкий флэнжер",
    "robot":    "Робот: жёсткий металл, монотонно",
    "villain":  "Злодей: низкий тон, зал",
    "cartoon":  "Мультяшный: высокий тон, быстрее",
    "giant":    "Великан: очень низкий, медленный",
    "radio":    "Рация: узкая полоса, перегруз",
    "phone":    "Телефон: как по старой линии",
    "whisper":  "Шёпот в пещере: тихо и эхо",
    "announcer": "Диктор: плотный, громкий, с компрессией",
}


def fx_chain(name, sr):
    pitch = lambda r: f"asetrate={int(sr * r)},aresample={sr},atempo={1 / r:.4f}"
    return {
        "clean": "anull",
        "android": f"{pitch(1.03)},flanger=delay=2:depth=2:speed=0.3:width=60,"
                   "aecho=0.8:0.6:12:0.35,equalizer=f=3000:t=q:w=1:g=3",
        "robot": "afftfilt=real='hypot(re,im)*cos(0)':imag='hypot(re,im)*sin(0)':win_size=512:overlap=0.75,"
                 "aecho=0.8:0.7:8:0.5,highpass=f=150",
        "villain": f"{pitch(0.82)},aecho=0.8:0.8:60|120:0.35|0.25,bass=g=4",
        "cartoon": f"{pitch(1.35)},atempo=1.08",
        "giant": f"{pitch(0.68)},atempo=0.92,aecho=0.8:0.85:90:0.3",
        "radio": "highpass=f=400,lowpass=f=3200,acrusher=bits=8:mix=0.25,volume=2,alimiter",
        "phone": "highpass=f=300,lowpass=f=3400,equalizer=f=1000:t=q:w=1:g=4",
        "whisper": "volume=0.7,aecho=0.8:0.9:200|400|650:0.5|0.35|0.2,highpass=f=200",
        "announcer": "equalizer=f=120:t=q:w=1:g=3,equalizer=f=3500:t=q:w=1:g=3,"
                     "acompressor=threshold=-22dB:ratio=4:makeup=4,alimiter",
    }[name]


def synth_piper(text, voice, path):
    from piper import PiperVoice
    v = PiperVoice.load(f"{MODELS}/ru_RU-{voice}-medium.onnx")
    with wave.open(path, "wb") as w:
        v.synthesize_wav(text, w)
    return v.config.sample_rate


def synth_silero(text, voice, path):
    import torch
    model = torch.package.PackageImporter(f"{MODELS}/silero_v4_ru.pt").load_pickle("tts_models", "model")
    audio = model.apply_tts(text=text, speaker=voice, sample_rate=48000, put_accent=True, put_yo=True)
    import numpy as np
    pcm = (audio.numpy() * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000); w.writeframes(pcm.tobytes())
    return 48000


def say(text, voice, fx, out):
    with tempfile.TemporaryDirectory() as td:
        raw = f"{td}/raw.wav"
        sr = synth_piper(text, voice, raw) if voice in PIPER else synth_silero(text, voice, raw)
        af = fx_chain(fx, sr) + ",loudnorm=I=-16:TP=-1.5"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ar", "48000", out], check=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?")
    ap.add_argument("--voice", default="denis", choices=PIPER + SILERO)
    ap.add_argument("--fx", default="clean", choices=list(FX))
    ap.add_argument("-o", "--out", default="out.mp3")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.text:
        print("Голоса:", ", ".join(PIPER + SILERO))
        for k, v in FX.items():
            print(f"  {k:10} {v}")
        sys.exit(0)
    print(say(a.text, a.voice, a.fx, a.out))
