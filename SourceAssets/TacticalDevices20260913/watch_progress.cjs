const fs=require('fs');
const ws=new WebSocket('ws://192.168.3.142:8188/ws?clientId=TacticalDevices20260913');
ws.onmessage=async e=>{if(typeof e.data!=='string')return;const v=JSON.parse(e.data); if(['executing','progress','execution_error','execution_success','progress_state'].includes(v.type)){ const s=JSON.stringify(v);fs.appendFileSync('D:/FPS3D/FPSGAME/SourceAssets/TacticalDevices20260913/progress.jsonl',s+'\n'); console.log(s.slice(0,1200));}};
ws.onerror=e=>console.log('websocket error');setTimeout(()=>{ws.close();},45000);
