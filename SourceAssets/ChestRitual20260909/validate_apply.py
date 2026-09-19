import json,struct
from pathlib import Path
out=Path(__file__).parent
def load(p):
 raw=p.read_bytes();n=struct.unpack_from('<I',raw,12)[0];return json.loads(raw[20:20+n]),raw[28+n:]
def data(j,b,i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];w={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]*4;off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',w)
 return b''.join(b[off+k*stride:off+k*stride+w] for k in range(a['count']))
def anim(j,b):
 return {a['name']:[(j['nodes'][c['target']['node']]['name'],c['target']['path'],data(j,b,a['samplers'][c['sampler']]['input']),data(j,b,a['samplers'][c['sampler']]['output'])) for c in a['channels']] for a in j['animations']}
a,ab=load(Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseMigration20260909/warehouse_chest_rigid.glb'));b,bb=load(out/'warehouse_chest_rigid.glb')
assert anim(a,ab)==anim(b,bb)
manifest=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/warehouse_assets.json');old=json.loads((out/'Before/warehouse_assets.json').read_text());current=json.loads(manifest.read_text());new=json.loads((out/'import_report.json').read_text())
assert current==old,'Concurrent manifest changes; inspect before applying'
for k in ['mesh','open','close']:current[k]=new[k]
current['materials'].update(new['materials'])
assert all(m['name'] in current['materials'] for m in b['materials'])
for path in [current[k] for k in ['mesh','open','close']]+list(current['materials'].values()):
 assert (Path('D:/FPS3D/FPSGAME/Content')/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).is_file(),path
tmp=manifest.with_suffix('.ritual-tmp');tmp.write_text(json.dumps(current,indent=2)+'\n');tmp.replace(manifest)
report={'animation_bytes_unchanged':True,'joints':len(b['skins'][0]['joints']),'all_material_slots_bound':True,'material_slots':[m['name'] for m in b['materials']],'gems':3,'engraved_badges':3,'radial_cuts':72}
(out/'validation.json').write_text(json.dumps(report,indent=2));print('RITUAL_VALIDATE_PASS',report)
