import hashlib,json,subprocess,sys,time,tempfile
from pathlib import Path
from PIL import Image
PYTHON=Path(r'F:/ComfyUI_windows_portable/python_embeded/python.exe')
ROOT=Path(__file__).resolve().parent
STATES='M_idle M_closed_pressed M_neutral_consonant M_smile_ee M_small_open_eh M_wide_open_ae M_wide_open_aa M_rounded_oh M_puckered_oo M_fv M_th_voiced M_th_unvoiced M_sh M_ch M_l M_r M_nasal M_back M_teeth M_breath'.split()
CANON=['A','B','C','D','E','F','G','H','X']+STATES
_ASSET_CACHE={}
def cached_sha2(p):
 k=str(p.resolve()); st=p.stat(); old=_ASSET_CACHE.get(k)
 if old and old[:2]==(st.st_size,st.st_mtime_ns): return old[2]
 value=sha(p); _ASSET_CACHE[k]=(st.st_size,st.st_mtime_ns,value); return value

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def audio_duration(p):
 r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],capture_output=True,text=True)
 if r.returncode: raise SystemExit('[FAIL] ffprobe audio duration')
 return float(r.stdout.strip())

def main():
 if len(sys.argv)!=2: raise SystemExit('usage: harden_lipsync.py AUDIO.wav')
 audio=Path(sys.argv[1]).resolve(); t=time.perf_counter()
 if not audio.exists(): raise SystemExit('[FAIL] missing audio')
 audio_sha=sha(audio); duration=audio_duration(audio)
 adapter=ROOT/'allosaurus_mouth_cues.py'; film=ROOT/'film-pytorch-port/models/film_net_fp16.pt'
 refs=ROOT/'rhubarb-lip-sync/split node narrator lip sync refs'
 assets={}
 for folder in [refs/'narration lip sync',refs/'narration quote lip sync']:
  assets[str(folder)]=[]
  for state in CANON:
   found=[p for p in folder.glob(f'*_{state}.png') if not p.name.endswith('_generated.png')]
   if not found: raise SystemExit(f'[FAIL] missing {state} in {folder}')
   p=found[0]
   with Image.open(p) as im:
    if im.size!=(2560,1440): raise SystemExit(f'[FAIL] dimensions {p}')
   assets[str(folder)].append({'state':state,'path':str(p.resolve()),'sha256':cached_sha2(p),'bytes':p.stat().st_size})
 cache=ROOT/'.cache'/'allosaurus'; cache.mkdir(parents=True,exist_ok=True)
 asset_cache_path=ROOT/'.cache'/'asset_hashes.json'
 try: asset_cache=json.loads(asset_cache_path.read_text(encoding='utf-8'))
 except Exception: asset_cache={}
 asset_hits=asset_misses=0
 key=hashlib.sha256((audio_sha+sha(adapter)).encode()).hexdigest()[:24]
 def cached_sha(p):
  global asset_hits,asset_misses
  k=str(p.resolve()); st=p.stat(); old=asset_cache.get(k)
  if old and old.get('size')==st.st_size and old.get('mtime_ns')==st.st_mtime_ns:
   asset_hits+=1; return old['sha256']
  value=sha(p); asset_cache[k]={'size':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':value}; asset_misses+=1; return value
 cue=cache/f'{key}.json'
 def valid_cache(p):
  try:
   d=json.loads(p.read_text(encoding='utf-8'))
   return d.get('detector')=='allosaurus' and d.get('model')=='eng2102' and isinstance(d.get('mouthCues'),list) and len(d['mouthCues'])>0
  except Exception: return False
 if not valid_cache(cue):
  tmp=cue.with_suffix('.tmp')
  cmd=[str(PYTHON),str(adapter),str(audio),'-o',str(tmp),'--device','0']
  r=subprocess.run(cmd,capture_output=True,text=True)
  if r.returncode or not valid_cache(tmp): raise SystemExit('[FAIL] Allosaurus output invalid: '+r.stdout[-1000:]+r.stderr[-1000:])
  tmp.replace(cue); cache_status='miss'
 else: cache_status='hit'
 manifest={'version':2,'audio':str(audio),'audio_sha256':audio_sha,'audio_duration':duration,'detector':{'name':'allosaurus','model':'eng2102','cue_file':str(cue.resolve()),'cache_key':key},'film':{'model':str(film.resolve()),'sha256':sha(film),'backend':'torchscript-pytorch','device':'cuda'},'output':{'width':2560,'height':1440,'fps':24,'interpolation':'on-demand','grain':'post-FILM'},'assets':assets,'cache':{'allosaurus':cache_status},'preflight_seconds':round(time.perf_counter()-t,3)}
 out=ROOT/'lipsync_pipeline_manifest.json'; out.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(json.dumps({'ok':True,'cache':cache_status,'cue_file':str(cue),'assets':sum(map(len,assets.values())),'manifest':str(out)}))
if __name__=='__main__': main()
