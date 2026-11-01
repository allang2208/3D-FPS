"""Bounded readback of the explicitly requested finger correction."""
import json,math,bisect,ast
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O/'install.py').read_text())
for name in ('qlerp','sample'):
 exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
before=json.loads((O/'ue_before.json').read_text())['profiles'];after=json.loads((O/'ue_after_profiles.json').read_text());patch=json.loads((O/'rotation_patch.json').read_text())
owned={r['bone'] for p in patch.values() for r in p['rotations']};paths={p['base'] for p in patch.values()}
R={'unowned_changed':[],'max_translation_scale_delta':0.,'max_saved_rotation_error_deg':0.,'samples':0,'saved_profiles':2,'runtime_tested':False}
def angle(a,b):
 d=abs(sum(x*y for x,y in zip(a,b)))/math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
 return math.degrees(2*math.acos(min(1,max(0,d))))
for family,cs in before.items():
 current={c['base']:c for c in after[family]['clips']}
 for clip in cs:
  dst=current[clip['base']];at={t['bone']:t for t in dst['tracks']}
  for t in clip['tracks']:
   nt=at[t['bone']]
   if clip['base'] not in paths or t['bone'] not in owned:
    if t!=nt:R['unowned_changed'].append(family+'/'+clip['base']+'/'+t['bone'])
   else:
    for time in sorted(set(t['times']+nt['times'])):
     a=sample(t,time,10,'values');b=sample(nt,time,10,'values')
     R['max_translation_scale_delta']=max(R['max_translation_scale_delta'],max(abs(a[i]-b[i]) for i in (0,1,2,7,8,9)))
for role,p in patch.items():
 family='mag10' if role.endswith('_mag10') else 'base';dst=next(c for c in after[family]['clips'] if c['base']==p['base']);at={t['bone']:t for t in dst['tracks']}
 for t in p['rotations']:
  for i,time in enumerate(t['times']):
   actual=sample(at[t['bone']],time,10,'values')[3:7];expected=t['quaternions'][4*i:4*i+4]
   R['max_saved_rotation_error_deg']=max(R['max_saved_rotation_error_deg'],angle(actual,expected));R['samples']+=1
(O/'saved_readback.json').write_text(json.dumps(R,indent=2));print(json.dumps(R,indent=2))
