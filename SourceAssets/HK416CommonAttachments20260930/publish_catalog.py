"""Only extend the current HK416 entry with existing canonical common options."""
import json,copy,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];file=P/'Content/ColdSteelData/gunsmith.json'
text=file.read_text(encoding='utf-8-sig');catalog=json.loads(text);donor=next(w for w in catalog['weapons'] if w['id']=='ue_m4a1');w=copy.deepcopy(next(w for w in catalog['weapons'] if w['id']=='ue_hk416'))
adds={'optic':['panoramic_red_dot','prism_scope_2x','lpvo_1_6x'],'muzzle':['tactical_suppressor','brake'],
 'underbarrel':['canted_foregrip','tactical_vertical_foregrip','prism_handstop','angled_foregrip'],
 'stock':['false','skeleton','core_stock','qr_performance','tactical_telescopic'],
 'reargrip':['false','phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'],
 'magazine':['false','ext_mag','large_drum']}
for slot,ids in adds.items():
 if slot not in w['allowed']:w['allowed'].append(slot)
 options=w['options'].setdefault(slot,[])
 for id in ids:
  if not any(o['id']==id for o in options):options.append(copy.deepcopy(next(o for o in donor['options'][slot] if o['id']==id)))
w['traits']=[{'icon':'mechanic','text':'全自动射击，按住扳机连续开火'},
 {'icon':'neutral','text':'支持通用瞄具、枪口、前握把、枪托、后握把及战术挂件'},
 {'icon':'neutral','text':'原装、扩容弹匣与弹鼓可选；前握把与弹鼓使用对应握持及换弹动作'}]
decoder=json.JSONDecoder();pos=text.index('[',text.index('"weapons"'))+1
while pos<len(text):
 while text[pos].isspace() or text[pos]==',':pos+=1
 entry,n=decoder.raw_decode(text[pos:])
 if entry['id']=='ue_hk416':break
 pos+=n
before=O/'CodeBefore/gunsmith.json'
if not before.exists():shutil.copy2(file,before)
if file.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed during publication')
file.write_text(text[:pos]+json.dumps(w,ensure_ascii=False,indent=2)+text[pos+n:],encoding='utf-8')
(O/'catalog_publication.json').write_text(json.dumps({'added':adds,'weapon':w,'excluded':'titanium_brake, per user instruction','runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('HK416_COMMON_OPTIONS_PUBLISHED')
