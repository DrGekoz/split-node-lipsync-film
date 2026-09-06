import React from 'react';
import {AbsoluteFill,Audio,Img,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
export const LipSyncTest=({audio, cues, refs, quotePng, requireQuote=false})=>{
 const f=useCurrentFrame(), {fps}=useVideoConfig(), t=f/fps;
 if(requireQuote && !quotePng) throw new Error('Quote pipeline requires quotePng');
 let mouth='X'; for(const c of cues){if(t>=c.start&&t<c.end){mouth=c.value;break;}}
 const ref=refs[mouth]||refs.X;
 return <AbsoluteFill style={{background:'#111',justifyContent:'center',alignItems:'center'}}>
  <Img src={staticFile(ref)} style={{width:'100%',height:'100%',objectFit:'contain'}}/>
  {quotePng&&<Img src={staticFile(quotePng)} style={{position:'absolute',left:70,bottom:70,width:700,maxHeight:480,objectFit:'contain'}}/>}
  <Audio src={staticFile(audio)}/>
 </AbsoluteFill>;
};
