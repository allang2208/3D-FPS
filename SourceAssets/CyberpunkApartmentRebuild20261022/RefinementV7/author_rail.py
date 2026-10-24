"""Preserve balcony span and privacy caps; lower only the front guardrail."""
import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parent
with bpy.data.libraries.load(str(R.parent/'RefinementV4/CyberpunkApartment_Rebuild.blend'),link=False) as (source,target):target.objects=['SM_AP_BalconyRail']
ob=target.objects[0];bpy.context.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False;ob.location=(0,0,0);ob.rotation_euler=(0,0,0);ob.scale=(1,1,1)
for v in ob.data.vertices:
 if v.co.z<1.3:v.co.z*=2/3
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;ob.name='SM_AP7_BalconyRail'
file=R/'Meshes'/f'{ob.name}.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'BalconyRail_Source.blend'))
manifest=json.loads((R/'detail-assembly.json').read_text());manifest['meshes']=[x for x in manifest['meshes'] if x['key']!='BalconyRail']
manifest['meshes'].append(dict(key='BalconyRail',name=ob.name,fbx=str(file),asset='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Meshes/'+ob.name,nanite=False,collision=False,triangles=sum(len(p.vertices)-2 for p in ob.data.polygons)))
(R/'detail-assembly.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('AP7_RAIL_AUTHORED')
