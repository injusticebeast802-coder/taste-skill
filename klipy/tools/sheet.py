import json, subprocess, sys
slug = sys.argv[1]
s = json.load(open(f"{slug}.json"))
beats = s.get("beats", [])
dur = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f"out/{slug}.mp4"]).decode())
ts = []
for i,b in enumerate(beats):
    nxt = beats[i+1]["t"] if i+1 < len(beats) else dur-4
    ts.append(min(b["t"] + max(1.6, (nxt-b["t"])*0.8), nxt-0.1))
ts.append(dur-1.5)
files=[]
for i,t in enumerate(ts):
    f=f"qa/{slug}_{i}.png"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{t:.2f}","-i",f"out/{slug}.mp4","-frames:v","1","-vf","scale=360:640",f],check=True)
    files.append(f)
n=len(files); cols=min(n,4)
inp=sum([["-i",f] for f in files],[])
rows=(n+cols-1)//cols
lay="|".join(f"{(i%cols)*360}_{(i//cols)*640}" for i in range(n))
subprocess.run(["ffmpeg","-v","error","-y",*inp,"-filter_complex",f"xstack=inputs={n}:layout={lay}:fill=black" if n>1 else "null",f"qa/{slug}_sheet.png"],check=True)
print(f"{slug} dur={dur:.1f} times={[round(t,1) for t in ts]}")
