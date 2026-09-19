import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const receipt=JSON.parse(fs.readFileSync(path.join(root,'reference_stock_high_submitted.json')));
const ws=new WebSocket('ws://192.168.3.142:8188/ws?clientId=ReferenceStock20260912');
let lastPrint=0;
ws.onmessage=event=>{
 if(typeof event.data!=='string')return;
 const value=JSON.parse(event.data),data=value.data??{};
 if(data.prompt_id && data.prompt_id!==receipt.prompt_id)return;
 if(!['executing','progress','execution_error','execution_success','progress_state'].includes(value.type))return;
 fs.appendFileSync(path.join(root,'progress.jsonl'),JSON.stringify({time:new Date().toISOString(),...value})+'\n');
 if(value.type!=='progress_state' && (Date.now()-lastPrint>12000 || value.type!=='progress')){
  console.log(JSON.stringify(value));lastPrint=Date.now();
 }
};
ws.onerror=e=>console.log('WebSocket connection error',e.message);
setTimeout(()=>ws.close(),45000);
