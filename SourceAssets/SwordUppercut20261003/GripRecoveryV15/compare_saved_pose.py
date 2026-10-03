"""Compare the requested saved recovery/grip samples against this authoring."""
from pathlib import Path
P=Path(__file__).resolve().parent
exec(compile((P/'author_common.py').read_text('utf-8'),str(P/'author_common.py'),'exec'))
def rigid(m):return mat(m.translation,m.to_quaternion())
readback=json.loads((P/'current_pose_after.json').read_text('utf-8'))
report={}
for variant,d in readback.items():
    author=json.loads((P/variant/'editable_keys.json').read_text('utf-8'))
    errors=[]
    for source,compressed in zip(d['samples']['SOURCE'],d['samples']['COMPRESSED']):
        world={n:canonical(m) for n,m in globalize({n:native(k) for n,k in sample_keys(author['samples'],source['t']).items()}).items()}
        for bone,r in source['world'].items():
            errors.append({'t':source['t'],'bone':bone,'author_source_cm':(world[bone].translation-canonical(native(r)).translation).length*100,
                'source_compressed_cm':(Vector(r['p'])-Vector(compressed['world'][bone]['p'])).length})
    end=d['samples']['COMPRESSED'][-1]['world'];start=d['samples']['COMPRESSED'][0]['world']
    report[variant]={'revision':d['revision'],'seconds':d['seconds'],
        'max_author_to_source':max(errors,key=lambda x:x['author_source_cm']),
        'max_source_to_compressed':max(errors,key=lambda x:x['source_compressed_cm']),
        'idle_endpoint_position_cm':max((Vector(start[b]['p'])-Vector(end[b]['p'])).length for b in start),
        'scope':'Specified grip/recovery bone samples only; not live gameplay or animation compression acceptance'}
(P/'saved_pose_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
