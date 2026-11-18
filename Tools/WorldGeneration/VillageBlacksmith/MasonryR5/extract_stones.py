"""Prepare a reusable bank of actual house stones, retaining their authored UVs."""
import bpy,bmesh,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/MasonryR5'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.fbx(filepath=str(OUT/'HouseWallDonor.fbx'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
source=max(objects,key=lambda o:len(o.data.polygons))
info={'objects':[dict(name=o.name,polygons=len(o.data.polygons),size=list(o.dimensions)) for o in objects]}
for o in list(bpy.context.scene.objects):
 if o!=source:bpy.data.objects.remove(o,do_unlink=True)
bpy.context.view_layer.objects.active=source;source.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(source.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002)
bm.to_mesh(source.data);bm.free()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
stones=[]
for o in list(bpy.context.scene.objects):
 if o.type!='MESH' or len(o.data.polygons)<12 or min(o.dimensions)<.025 or max(o.dimensions)>1.4:
  bpy.data.objects.remove(o,do_unlink=True);continue
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='BOUNDS')
 o.name='HouseStone_'+str(len(stones)).zfill(3)
 stones.append(dict(name=o.name,polygons=len(o.data.polygons),size=list(o.dimensions)))
info['stones']=stones
(OUT/'stone-bank.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HouseStoneBank.blend'))
print('HOUSE_STONES_PREPARED',len(stones),info['objects'])
