import argparse,json,subprocess,tempfile,shutil
from pathlib import Path
from PIL import Image,ImageChops

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--video',required=True); ap.add_argument('--frames',required=True); ap.add_argument('--report',required=True); a=ap.parse_args(); video=Path(a.video); framefile=Path(a.frames)
 src_all=[Path(x.split("'",2)[1]) for x in framefile.read_text().splitlines() if x.startswith('file ')]; src=src_all[:-1] if len(src_all)>1 and src_all[-1]==src_all[-2] else src_all
 with tempfile.TemporaryDirectory() as td:
  out=Path(td); subprocess.run(['ffmpeg','-y','-i',str(video),'-vsync','0',str(out/'%05d.png')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  dec=sorted(out.glob('*.png')); mismatches=[]
  for i,(s,d) in enumerate(zip(src,dec)):
   a1=Image.open(s).convert('RGB').resize((320,180)); b=Image.open(d).convert('RGB').resize((320,180)); diff=ImageChops.difference(a1,b); bbox=diff.getbbox();
   if bbox and sum(sum(abs(v) for v in pixel) for pixel in diff.resize((1,1)).getdata())>12: mismatches.append({'index':i,'bbox':bbox})
  last=Image.open(dec[-1]).convert('RGB').resize((320,180)); prev=Image.open(dec[-2]).convert('RGB').resize((320,180)); rd=ImageChops.difference(last,prev).resize((1,1)); repeated=sum(sum(abs(v) for v in px) for px in rd.getdata())<12
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(video)],text=True)); ts=[float(x['best_effort_timestamp_time']) for x in probe['frames']]; steps=[round(ts[i+1]-ts[i],6) for i in range(len(ts)-1)]
  report={'source_frames':len(src),'decoded_frames':len(dec),'mismatches':mismatches[:20],'mismatch_count':len(mismatches),'final_frame_repeated':repeated,'timestamp_step_min':min(steps) if steps else None,'timestamp_step_max':max(steps) if steps else None,'pass':len(dec)==len(src)+1 and repeated and not mismatches and all(abs(x-1/24)<0.002 for x in steps)}
 Path(a.report).write_text(json.dumps(report,indent=2)); print(json.dumps(report))
if __name__=='__main__': main()
