"""Readback of saved profiles and immutable source asset hashes."""
from pathlib import Path
import unreal as u
import json,gzip,pickle,hashlib,struct
r=Path(__file__).resolve().parent;project=r.parents[2];d=pickle.load(open(r/'current.pkl','rb'));inputs=json.loads((r/'inputs.json').read_text());receipt=json.loads((r/'install_receipt.json').read_text())
extra=json.loads((r/'extra_inputs.json').read_text());d['profiles']['bipod']=extra['bipod'];inputs['hashes'].update(extra['hashes'])
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
report={}
for family,p in d['profiles'].items():
    a=u.load_asset(p['asset']);saved=[]
    for c in a.get_editor_property('clips'):
        v=c.get_editor_property;retained=v('retained')
        saved.append(dict(base=v('base').get_path_name(),duration=v('duration'),retained=retained.get_path_name() if retained else None,tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in v('tracks')]))
    target=json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips']
    if len(saved)!=len(target):raise RuntimeError('Clip count '+family)
    for src,dst in zip(target,saved):
        if src['base']!=dst['base'] or src['duration']!=dst['duration']:raise RuntimeError('Clock changed')
        if len(src['tracks'])!=len(dst['tracks']):raise RuntimeError('Track count changed')
        for x,y in zip(src['tracks'],dst['tracks']):
            if x['bone']!=y['bone'] or list(map(f32,x['times']))!=y['times'] or list(map(f32,x['values']))!=y['values']:raise RuntimeError('Track mismatch '+family+'/'+x['bone'])
    report[family]=dict(clips=len(saved),saved_values_match=True)
for path,sha in inputs['hashes'].items():
    actual=hashlib.sha256((project/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
    if actual!=receipt['saved'].get(path,sha):raise RuntimeError('Unexpected source mutation '+path)
(r/'saved_review.json').write_text(json.dumps(dict(profiles=report,base_animations_and_mesh_unchanged=True),indent=2));print('WRIST33_SAVED_READBACK_OK',flush=True)
