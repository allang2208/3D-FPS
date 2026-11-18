import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/DetailR6'
r={}
for f in ['SM_H_OldWall_Window_00A.fbx','SM_CoolingBarrel.fbx','../MasonryR5/HouseStoneBank.blend','../MasonryR5/Authored/VillageBlacksmith_MasonryR5.blend']:
 if f.endswith('.blend'):bpy.ops.wm.open_mainfile(filepath=str(OUT/f))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(OUT/f))
 rows=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  if 'StoneBank' in f and len(rows)>3:break
  coords=[v.co for v in o.data.vertices]
  rows.append(dict(name=o.name,dimensions=list(o.dimensions),location=list(o.location),scale=list(o.scale),rotation=list(o.rotation_euler),uv=[dict(name=l.name,min=[min(d.uv[i] for d in l.data) for i in range(2)],max=[max(d.uv[i] for d in l.data) for i in range(2)]) for l in o.data.uv_layers],colors=[dict(name=a.name,domain=a.domain,sample=[list(v.color) for v in list(a.data)[:2]]) for a in o.data.color_attributes]))
 r[f]=rows
(OUT/'blender-inputs.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('READ_R6_GEOMETRY_INPUTS',r)
