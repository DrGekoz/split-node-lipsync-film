import json,subprocess
from pathlib import Path
FPS=24
def main():
 root=Path(__file__).resolve().parents[1]; audio=Path(r'F:/aaaaaVIBECODING/System Breakers/voice_tests/joe_pockettts_results/joe_williams_personal_intro.wav'); cues=json.loads(Path(r'F:/aaaaaVIBECODING/System Breakers/allosaurus_mouth_cues.json').read_text())['mouthCues']; duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(audio)],text=True));
 for name,refs in [('narration',Path(r'F:/aaaaaVIBECODING/System Breakers/rhubarb-lip-sync/split node narrator lip sync refs/narration lip sync')),('quote',Path(r'F:/aaaaaVIBECODING/System Breakers/rhubarb-lip-sync/split node narrator lip sync refs/narration quote lip sync'))]:
  out=root/'timeline diagnostic'/name; out.mkdir(parents=True,exist_ok=True); files=[]
  for n in range(round(duration*FPS)):
   t=n/FPS; state='M_idle'
   for c in cues:
    if t>=c['start']: state=c['state']
    else: break
   p=next(refs.glob(f'*_M_{state[2:]}.png')); files.append(p)
  manifest=out/'frames.txt'; lines=[]
  for p in files: lines += [f"file '{str(p).replace(chr(92),'/')}'",'duration 0.041666667']
  lines += [f"file '{str(files[-1]).replace(chr(92),'/')}'"]; manifest.write_text('\n'.join(lines)); temp=out/'timeline.mp4'; subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(manifest),'-r','24','-c:v','libx264','-pix_fmt','yuv420p',str(temp)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(name,len(files),temp)
if __name__=='__main__': main()
