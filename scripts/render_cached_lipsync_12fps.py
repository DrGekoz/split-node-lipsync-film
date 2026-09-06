import argparse,base64,json,subprocess,sys
from pathlib import Path
from PIL import Image
FPS=12

def run(c):
 r=subprocess.run(c,capture_output=True,text=True)
 if r.returncode: raise RuntimeError(r.stderr[-2000:])
 return r.stdout

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--audio',required=True); ap.add_argument('--cues',required=True); ap.add_argument('--refs',required=True); ap.add_argument('--worker',required=True); ap.add_argument('--python',required=True); ap.add_argument('--cache',required=True); ap.add_argument('--out',required=True); ap.add_argument('--chunks',required=True); a=ap.parse_args()
 audio=Path(a.audio).resolve(); cues=json.loads(Path(a.cues).read_text())['mouthCues']; refs=Path(a.refs).resolve(); cache=Path(a.cache).resolve(); chunks=Path(a.chunks).resolve(); chunks.mkdir(parents=True,exist_ok=True)
 duration=float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(audio)]).strip()); states={p.stem.split('_M_',1)[1]:p for p in refs.glob('*_M_*.png')}; proc=subprocess.Popen([a.python,a.worker],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True); frames=[]; cache_hits=film_hits=0
 try:
  for i,c in enumerate(cues):
   start=float(c['start']); end=float(cues[i+1]['start']) if i+1<len(cues) else duration; src=c['state']; dst=cues[i+1]['state'] if i+1<len(cues) else src; n=max(1,round((end-start)*FPS)); folder=chunks/f'{i:05d}_{start:.3f}_{end:.3f}'; folder.mkdir(exist_ok=True)
   for f in range(n):
    out=folder/f'{f:05d}.png'; pos=f/n
    if not out.exists():
     if f==0 or src==dst: Image.open(states[src]).convert('RGB').save(out)
     else:
      # Quantized cache positions; FILM fallback for timing not represented by cache.
      qpos=min((.25,.5,.75),key=lambda x:abs(x-pos)); cached=cache/f'{src[2:]}__to__{dst[2:]}'/f'{qpos:.2f}.png'
      if cached.exists(): Image.open(cached).convert('RGB').save(out); cache_hits+=1
      else:
       proc.stdin.write(json.dumps({'frame1':str(states[src]),'frame2':str(states[dst]),'time':pos})+'\n'); proc.stdin.flush(); d=json.loads(proc.stdout.readline());
       if not d.get('ok'): raise RuntimeError(d)
       out.write_bytes(base64.b64decode(d['png_base64'])); film_hits+=1
    frames.append(out)
 finally:
  try: proc.stdin.close()
  except OSError: pass
  proc.terminate(); proc.wait(timeout=10)
 allframes=chunks/'all_frames.txt'; allframes.write_text('\n'.join("file '"+str(p).replace('\\','/')+"'" for p in frames))
 temp=Path(a.out).with_suffix('.video.tmp.mp4'); run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(allframes),'-framerate',str(FPS),'-r',str(FPS),'-c:v','libx264','-pix_fmt','yuv420p',str(temp)])
 run(['ffmpeg','-y','-i',str(temp),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-shortest',a.out]); temp.unlink(missing_ok=True)
 print(json.dumps({'fps':FPS,'frames':len(frames),'cache_hits':cache_hits,'film_fallbacks':film_hits,'output':a.out}))
if __name__=='__main__': main()
