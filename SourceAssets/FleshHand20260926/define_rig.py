"""Write a custom five-digit hand skeleton from the generated surface landmarks."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'LocalRig'
p=json.loads((OUT/'surface_landmarks.json').read_text())
bones=[]
def add(name,head,tail,parent,region='body',deform=True):
    bones.append(dict(name=name,head=head,tail=tail,parent=parent,region=region,deform=deform))
add('root',[.025,-.00027,0],[.025,-.00027,.06],None,deform=False)
add('wrist',p['wrist_base'],p['wrist_top'],'root')
add('palm',p['wrist_top'],p['palm_center'],'wrist')
for digit in ('index','middle','ring','little'):
    mcp=p[digit+'_mcp']
    start=[p['wrist_top'][0]*.68+mcp[0]*.32,
           p['wrist_top'][1]*.75+mcp[1]*.25,.265]
    add(digit+'_metacarpal',start,mcp,'palm',digit)
    names=['mcp','pip','dip','tip']
    parent=digit+'_metacarpal'
    for i in range(3):
        name=digit+'_%02d'%(i+1)
        add(name,p[digit+'_'+names[i]],p[digit+'_'+names[i+1]],parent,digit)
        parent=name
for i,(first,last) in enumerate(zip(('cmc','mcp','ip'),('mcp','ip','tip'))):
    add('thumb_%02d'%(i+1),p['thumb_'+first],p['thumb_'+last],
        'palm' if i==0 else 'thumb_%02d'%i,'thumb')
definition={'authoring_height_m':1.0,'palm_outward_axis':[0,1,0],
    'finger_isolation_cut':.64,'finger_tip_min_z':.70,
    'thumb_isolation_plane':[-1,-.32,.01],'bones':bones,
    'input':'surface_landmarks.json; coordinates fitted on the actual candidate01 quad surface',
    'scope':'custom hand bind and weights only; no animation or physics bodies'}
(OUT/'rig_definition.json').write_text(json.dumps(definition,indent=2),encoding='utf-8')
print('Custom hand skeleton definition saved: %d bones'%len(bones))
