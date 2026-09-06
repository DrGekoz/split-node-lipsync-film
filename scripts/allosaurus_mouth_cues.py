import argparse,json
from pathlib import Path
from allosaurus.app import read_recognizer
from argparse import Namespace

MAP={
 'p':'M_closed_pressed','b':'M_closed_pressed','m':'M_closed_pressed',
 't':'M_teeth','d':'M_teeth','k':'M_back','g':'M_back','ɡ':'M_back',
 'n':'M_nasal','ŋ':'M_nasal','ɲ':'M_nasal',
 'i':'M_smile_ee','iː':'M_smile_ee','ɪ':'M_smile_ee','e':'M_smile_ee','eː':'M_smile_ee',
 'ɛ':'M_small_open_eh','ə':'M_small_open_eh','ɐ':'M_small_open_eh','ʌ':'M_small_open_eh',
 'æ':'M_wide_open_ae','ɑ':'M_wide_open_aa','ɑː':'M_wide_open_aa','ɒ':'M_wide_open_aa',
 'ɔ':'M_rounded_oh','o':'M_rounded_oh','oː':'M_rounded_oh',
 'ʊ':'M_puckered_oo','u':'M_puckered_oo','uː':'M_puckered_oo','w':'M_puckered_oo',
 'f':'M_fv','v':'M_fv','θ':'M_th_unvoiced','ð':'M_th_voiced',
 'ʃ':'M_sh','ʒ':'M_sh','tʃ':'M_ch','dʒ':'M_ch','d͡ʒ':'M_ch',
 'l':'M_l','ɹ':'M_r','r':'M_r','h':'M_breath','j':'M_neutral_consonant',
 's':'M_teeth','z':'M_teeth','x':'M_back','ɣ':'M_back',
}

def parse(lines):
 out=[]
 for line in lines:
  q=line.strip().split(maxsplit=2)
  if len(q)==3:
   try: out.append((float(q[0]),float(q[1]),q[2]))
   except ValueError: pass
 return out

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('audio'); ap.add_argument('-o','--output',required=True); ap.add_argument('--device',type=int,default=0)
 a=ap.parse_args(); rec=read_recognizer(Namespace(model='eng2102',device_id=a.device,lang='ipa',approximate=False,prior=None))
 raw=rec.recognize(a.audio,'eng',timestamp=True)
 phones=parse(raw.splitlines() if isinstance(raw,str) else raw)
 cues=[]
 for start,dur,phone in phones:
  state=MAP.get(phone, 'M_neutral_consonant')
  end=start+dur
  if cues and cues[-1]['state']==state and start <= cues[-1]['end']+0.06:
   cues[-1]['end']=max(cues[-1]['end'],end); cues[-1]['phones'].append(phone)
  else: cues.append({'start':start,'end':end,'state':state,'phones':[phone]})
 result={'detector':'allosaurus','model':'eng2102','language':'eng','audio':str(a.audio),'mouthCues':cues}
 Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'ok':True,'phones':len(phones),'mouthCues':len(cues),'output':a.output},ensure_ascii=False))
if __name__=='__main__': main()
