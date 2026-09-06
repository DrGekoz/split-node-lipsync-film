import argparse,base64,json,subprocess
from pathlib import Path
from PIL import Image

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--refs',required=True); ap.add_argument('--worker',required=True); ap.add_argument('--python',required=True); ap.add_argument('--cache',default='cache/interpolation'); a=ap.parse_args()
 refs=Path(a.refs).resolve(); cache=Path(a.cache).resolve(); cache.mkdir(parents=True,exist_ok=True)
 states=sorted({p.stem.split('_M_',1)[1] for p in refs.glob('*_M_*.png')}); refs_by={s:next(refs.glob(f'*_M_{s}.png')) for s in states}; positions=(.25,.5,.75)
 proc=subprocess.Popen([a.python,a.worker],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
 done=0; total=len(states)*(len(states)-1)*len(positions)
 try:
  for src in states:
   for dst in states:
    if src==dst: continue
    for pos in positions:
     out=cache/f'{src}__to__{dst}'/f'{pos:.2f}.png'; out.parent.mkdir(parents=True,exist_ok=True)
     if out.exists(): done+=1; continue
     proc.stdin.write(json.dumps({'frame1':str(refs_by[src]),'frame2':str(refs_by[dst]),'time':pos})+'\n'); proc.stdin.flush()
     line=proc.stdout.readline()
     if not line: raise RuntimeError('FILM worker exited before response')
     result=json.loads(line)
     if not result.get('ok'): raise RuntimeError(result)
     out.write_bytes(base64.b64decode(result['png_base64']));
     with Image.open(out) as im:
      if im.size!=(2560,1440): raise RuntimeError(f'bad cache frame {out}: {im.size}')
     done+=1; print(f'{done}/{total} {src}->{dst} {pos:.2f}',flush=True)
 finally:
  try: proc.stdin.close()
  except OSError: pass
  proc.terminate(); proc.wait(timeout=10)
 manifest={'states':states,'positions':positions,'frames':done,'expected':total,'resolution':[2560,1440]}
 (cache/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(json.dumps(manifest))
if __name__=='__main__': main()
