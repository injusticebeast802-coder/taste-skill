import sys, json, time, wave, numpy as np
from faster_whisper import WhisperModel
audio, out, model_name = sys.argv[1], sys.argv[2], sys.argv[3]
t0=time.time()
m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4)
w=wave.open(audio); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768.0
off=float(sys.argv[4]) if len(sys.argv)>4 else 0.0
segs, info = m.transcribe(a, language="ru", vad_filter=True, beam_size=1, word_timestamps=False)
with open(out, "w") as f:
    for s in segs:
        f.write(json.dumps({"s": round(s.start+off,2), "e": round(s.end+off,2), "t": s.text.strip()}, ensure_ascii=False)+"\n"); f.flush()
print("done", round(time.time()-t0), "s")
