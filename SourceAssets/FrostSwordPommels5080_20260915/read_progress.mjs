// Read only this client's live ComfyUI progress; never cancel or resubmit jobs.
const ws=new WebSocket('ws://192.168.3.142:8188/ws?clientId=FrostSwordPommels5080_20260915');
const timer=setTimeout(()=>ws.close(),30000);
ws.onmessage=({data})=>{if(typeof data!=='string')return;const msg=JSON.parse(data);if(['progress','executing','execution_error','execution_success','status'].includes(msg.type))console.log(JSON.stringify(msg));};
ws.onerror=()=>{console.log('progress socket closed');clearTimeout(timer);};
ws.onclose=()=>clearTimeout(timer);
