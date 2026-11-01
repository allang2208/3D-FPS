"""Change only the two M24 duration values, retaining the shared JSON text."""
import json,re,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;p=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
text=p.read_text(encoding='utf-8-sig');decoder=json.JSONDecoder()
match=re.search(r'"weapons"\s*:\s*\[',text)
if not match:raise RuntimeError('Weapon list missing')
i=match.end();start=end=None;weapon=None
while i<len(text):
 while text[i].isspace() or text[i]==',':i+=1
 if text[i]==']':break
 item,used=decoder.raw_decode(text[i:])
 if item.get('id')=='ue_m24':start,end,weapon=i,i+used,item;break
 i+=used
if weapon is None:raise RuntimeError('M24 definition missing')
block=text[start:end];base=re.search(r'"base"\s*:\s*\{',block)
if not base:raise RuntimeError('M24 base data missing')
base_start=base.end()-1;_,used=decoder.raw_decode(block[base_start:]);base_end=base_start+used
newbase=block[base_start:base_end];before={k:weapon['base'][k] for k in ('reload_time','empty_reload_time')};after={'reload_time':126/30,'empty_reload_time':176/30}
for key,value in after.items():
 newbase,count=re.subn(r'("'+key+r'"\s*:\s*)-?\d+(?:\.\d+)?',lambda m:m[1]+repr(value),newbase)
 if count!=1:raise RuntimeError('Unexpected M24 timing field '+key)
out=text[:start]+block[:base_start]+newbase+block[base_end:]+text[end:]
backup=O/'Backups';backup.mkdir(exist_ok=True)
if not (backup/'gunsmith.json').exists():(backup/'gunsmith.json').write_text(text,encoding='utf-8')
if p.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Concurrent gunsmith edit retained; rerun merge')
p.write_text(out,encoding='utf-8')
(O/'timing_receipt.json').write_text(json.dumps({'before':before,'after':after,'scope':'M24 base reload_time and empty_reload_time only','sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
print('M24_RELOAD_DURATIONS_SAVED',json.dumps(after),flush=True)
