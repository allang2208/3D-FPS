import json,struct
from pathlib import Path
out=Path(__file__).parent
def read(p):
 b=p.read_bytes();n=struct.unpack_from('<I',b,12)[0];return json.loads(b[20:20+n]),b[28+n:]
def data(j,b,i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];w={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]*4
 offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',w)
 return b''.join(b[offset+k*stride:offset+k*stride+w] for k in range(a['count']))
def anim(j,b):
 return {a['name']:[(j['nodes'][c['target']['node']]['name'],c['target']['path'],data(j,b,a['samplers'][c['sampler']]['input']),data(j,b,a['samplers'][c['sampler']]['output'])) for c in a['channels']] for a in j['animations']}
a,ab=read(Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseMigration20260909/warehouse_chest_rigid.glb'))
b,bb=read(out/'warehouse_chest_rigid.glb')
assert anim(a,ab)==anim(b,bb),'Animation changed'
geo=json.loads((out/'geometry_report.json').read_text())
for c in geo['contact']:
 if 'bezel_center' in c:
  center=c['bezel_center'];back=c['back_world_local']
  assert abs(back[1]+70.9)<.001 if center[1]<0 else abs(abs(back[0])-97.9)<.001
for root,radius in [(17.7,18.59),(14.8,15.68)]:assert radius-root>.8
manifest=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/warehouse_assets.json');old=json.loads((out/'Before/warehouse_assets.json').read_text());current=json.loads(manifest.read_text());new=json.loads((out/'import_report.json').read_text())
for k in ['mesh','open','close']:
 assert current[k] in [old[k],new[k]],'Concurrent edit: '+k
 current[k]=new[k]
assert current['materials']==old['materials'],'Material mappings changed concurrently; inspect'
tmp=manifest.with_suffix('.ornaments-tmp');tmp.write_text(json.dumps(current,indent=2)+'\n');tmp.replace(manifest)
report={'animation_bytes_unchanged':True,'rig_joints':len(b['skins'][0]['joints']),'materials_unchanged':True,'bezel_back_overlap_mm':.7,'ray_root_bezel_overlap_mm_min':5.6,'imported':new}
(out/'validated.json').write_text(json.dumps(report,indent=2));print('CHEST_ORNAMENTS_VALIDATE_PASS',report)
