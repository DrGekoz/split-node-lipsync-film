import React from 'react';
import {Composition,AbsoluteFill,Audio,Img,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import data from '../test_props.json';
const App=({audio,cues,refs})=>{const f=useCurrentFrame(),{fps}=useVideoConfig();let t=f/fps,m='X';for(const c of cues){if(t>=c.start&&t<c.end){m=c.value;break;}}return <AbsoluteFill><Img src={staticFile(refs[m]||refs.X)} style={{width:'100%',height:'100%',objectFit:'contain'}}/><Audio src={staticFile(audio)}/></AbsoluteFill>};
export const RemotionRoot=()=> <Composition id="SplitNodeHeadTurnTest" component={App} durationInFrames={Math.ceil(data.duration*24)} fps={24} width={2560} height={1440} defaultProps={data.props}/>;
