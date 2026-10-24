"""Reuse original far-city source as lit geometry, separate from the dynamic sky."""
import bpy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
source=PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/DetailedBay_Source.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));out=ROOT/'Meshes';out.mkdir(parents=True,exist_ok=True)
rows=[]
for key in ['FarCity','FarHeadland','FarTerrain']:
 original=bpy.data.objects[key];copy=original.copy();copy.data=original.data.copy();bpy.context.scene.collection.objects.link(copy)
 copy.name='SM_AP6_'+key
 for v in copy.data.vertices:v.co=(-v.co.x+10,-v.co.y,v.co.z-90)
 bpy.ops.object.select_all(action='DESELECT');copy.hide_set(False);copy.select_set(True);bpy.context.view_layer.objects.active=copy
 tri=copy.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 fbx=out/(copy.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False,use_tspace=True)
 rows.append(dict(key=key,name=copy.name,asset=BASE+'/Meshes/'+copy.name,fbx=str(fbx),triangles=len(copy.data.polygons),materials=[m.name for m in copy.data.materials],nanite=key!='FarTerrain'))
 bpy.data.objects.remove(copy,do_unlink=True)
(ROOT/'far-assembly.json').write_text(json.dumps(dict(meshes=rows,source=str(source),new_source_geometry=False,rendered=False),indent=2),encoding='utf8')
print('APARTMENT_V6_FAR_GEOMETRY_EXPORTED',sum(r['triangles'] for r in rows),flush=True)
