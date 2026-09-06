import json,sys,subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent
FILM=ROOT/'film-pytorch-port/models/film_net_fp16.pt'
ALLO=ROOT/'allosaurus_mouth_cues.py'
STATES='M_idle M_closed_pressed M_neutral_consonant M_smile_ee M_small_open_eh M_wide_open_ae M_wide_open_aa M_rounded_oh M_puckered_oo M_fv M_th_voiced M_th_unvoiced M_sh M_ch M_l M_r M_nasal M_back M_teeth M_breath'.split()

def fail(msg): raise SystemExit('[FAIL] '+msg)
def check_audio(p):
 if not p.exists(): fail(f'missing audio: {p}')
 r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,sample_rate,channels','-of','json',str(p)],capture_output=True,text=True)
 if r.returncode: fail('ffprobe failed for audio')
 d=json.loads(r.stdout); s=d['streams'][0]
 if s.get('codec_name') not in ('pcm_s16le','pcm_s24le','pcm_f32le'): fail('audio must be WAV PCM')
 if s.get('channels')!=1: fail('audio must be mono')
 return float(d['format']['duration'])
def main():
 if len(sys.argv)!=2: fail('usage: validate_lipsync_pipeline.py AUDIO.wav')
 audio=Path(sys.argv[1]); dur=check_audio(audio)
 if not FILM.exists(): fail(f'missing FILM model: {FILM}')
 if not ALLO.exists(): fail('missing Allosaurus adapter')
 refroot=ROOT/'rhubarb-lip-sync/split node narrator lip sync refs'
 folders=[refroot/'narration lip sync',refroot/'narration quote lip sync']
 for folder in folders:
  if not folder.exists(): fail(f'missing refs folder: {folder}')
  canonical=[]
  for state in ['A','B','C','D','E','F','G','H','X']+STATES:
   matches=[p for p in folder.glob(f'*_{state}.png') if not p.name.endswith('_generated.png')]
   if not matches: fail(f'missing state {state} in {folder.name}')
   canonical.append(matches[0])
  for p in canonical:
   try:
    with Image.open(p) as im:
     if im.size!=(2560,1440): fail(f'wrong dimensions: {p.name} {im.size}')
     if im.mode not in ('RGB','RGBA'): fail(f'wrong image mode: {p.name}')
   except Exception as e: fail(f'invalid image {p}: {e}')
 manifest={'audio':str(audio.resolve()),'duration':dur,'detector':'allosaurus','model':'eng2102','film_model':str(FILM.resolve()),'film_backend':'torchscript-pytorch','device_required':'cuda','output_width':2560,'output_height':1440,'output_fps':24,'interpolation':'on-demand transition frames only','grain':'after FILM, in Remotion','ref_folders':[str(x.resolve()) for x in folders]}
 out=ROOT/'lipsync_pipeline_manifest.json'; out.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(json.dumps({'ok':True,'duration':dur,'folders':2,'states_per_folder':len(STATES),'manifest':str(out)}))
if __name__=='__main__': main()
