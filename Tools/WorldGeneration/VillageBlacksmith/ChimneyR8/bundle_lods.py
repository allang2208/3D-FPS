"""Package all three authored LODs in a single FBX LOD group for atomic editor import."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ChimneyR8'
AUTH=OUT/'Authored'
bpy.ops.wm.open_mainfile(filepath=str(AUTH/'VillageBlacksmith_ChimneyR8.blend'))
manifest=json.loads((OUT/'model-manifest.json').read_text())
for row in manifest['assets']:
 source=bpy.data.objects[row['name']]
 group=bpy.data.objects.new(row['name']+'_LODs',None);bpy.context.collection.objects.link(group)
 group['fbx_type']='LodGroup'
 children=[]
 for level,ratio in ((0,1.),(1,.5),(2,.22)):
  o=source.copy();o.data=source.data.copy();bpy.context.collection.objects.link(o)
  o.matrix_world=Matrix.Identity(4);o.parent=group;o.name=row['name']+'_LOD'+str(level)
  bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
  if level:
   mod=o.modifiers.new('Authored distance detail','DECIMATE');mod.ratio=ratio;mod.delimit={'MATERIAL','UV'}
   bpy.ops.object.modifier_apply(modifier=mod.name)
  children.append(o)
 bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
 for o in children:o.select_set(True)
 path=AUTH/(row['name']+'_LODs.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False,use_custom_props=True)
 row['lod_bundle']=str(path)
 for o in children:bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.objects.remove(group,do_unlink=True)
(OUT/'model-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('SMITH_CHIMNEY_R7_LOD_BUNDLES_EXPORTED',len(manifest['assets']))
