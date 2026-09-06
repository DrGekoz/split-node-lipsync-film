import argparse,base64,json,subprocess,sys
from pathlib import Path
from PIL import Image
FPS=24

def run(cmd):
 r=subprocess.run(cmd,capture_output=True,text=True)
 if r.returncode: raise RuntimeError(r.stderr[-2000:])
 return r.stdout

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--audio',required=True); ap.add_argument('--cues',required=True); ap.add_argument('--refs',required=True); ap.add_argument('--worker',required=True); ap.add_argument('--python',default=sys.executable); ap.add_argument('--out',required=True); ap.add_argument('--chunks',default='interpolation chunks'); a=ap.parse_args()
 audio=Path(a.audio).resolve(); cues=json.loads(Path(a.cues).read_text(encoding='utf-8'))['mouthCues']; refs=Path(a.refs).resolve(); chunks=Path(a.chunks).resolve(); chunks.mkdir(parents=True,exist_ok=True)
 duration=float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(audio)]).strip())
 proc=subprocess.Popen([a.python,a.worker],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
 concat=[]; total=0
 try:
  for i,c in enumerate(cues):
   start=float(c['start']); end=float(cues[i+1]['start']) if i+1<len(cues) else duration; state=c['state']; nxt=cues[i+1]['state'] if i+1<len(cues) else state; frames=max(1,round((end-start)*FPS)); folder=chunks/f'{i:05d}_{start:.3f}_{end:.3f}'; folder.mkdir(exist_ok=True); paths=[]
   def ref(s):
    p=next(refs.glob(f'*_M_{s[2:]}*.png'),None) if s.startswith('M_') else next(refs.glob(f'*_{s}.png'),None)
    if not p: raise RuntimeError(f'missing ref {s}')
    return p
   for f in range(frames):
    t=f/frames; target=folder/f'{f:05d}.png'
    if not target.exists():
     if f==0: Image.open(ref(state)).convert('RGB').save(target)
     elif state==nxt and f==frames-1: Image.open(ref(state)).convert('RGB').save(target)
     else:
      q={'frame1':str(ref(state)),'frame2':str(ref(nxt)),'time':t}; proc.stdin.write(json.dumps(q)+'\n'); proc.stdin.flush(); d=json.loads(proc.stdout.readline());
      if not d.get('ok'): raise RuntimeError(d)
      target.write_bytes(base64.b64decode(d['png_base64']))
    paths.append(target); total+=1
   listfile=folder/'frames.txt'; listfile.write_text('\n'.join("file '"+str(p).replace('\\','/')+"'" for p in paths),encoding='utf-8'); concat.append(listfile)
 finally:
  try: proc.stdin.close()
  except OSError: pass
  proc.terminate()
  try: proc.wait(timeout=10)
  except subprocess.TimeoutExpired: proc.kill()
 manifest=chunks/'manifest.json'; manifest.write_text(json.dumps({'fps':FPS,'audio':str(audio),'cue_count':len(cues),'chunks':[str(x) for x in concat],'frames':total},indent=2),encoding='utf-8')
 allframes=chunks/'all_frames.txt'; allframes.write_text('\n'.join("file '"+str(p).replace('\\','/')+"'" for lf in concat for p in [Path(x.strip().split("'",2)[1]) for x in lf.read_text().splitlines()]),encoding='utf-8')
 out=Path(a.out).resolve(); temp=out.with_suffix('.tmp.mp4')
 run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(allframes),'-r',str(FPS),'-c:v','libx264','-pix_fmt','yuv420p',str(temp)])
 run(['ffmpeg','-y','-i',str(temp),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-shortest',str(out)])
 temp.unlink(missing_ok=True)
 print(json.dumps({'ok':True,'chunks':len(concat),'frames':total,'manifest':str(manifest),'output':str(out)}))
if __name__=='__main__': main()
