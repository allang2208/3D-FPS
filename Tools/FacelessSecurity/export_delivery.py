"""Export editable clothing separately and consolidated skeletal render meshes."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V01.blend'))
rig=bpy.data.objects['root'];body=bpy.data.objects['Security_CompleteBody'];display=bpy.data.objects['Security_OutfitBody']
clothes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in [body,display]]
def select(objects,active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=active or rig
def fbx(name,meshes):
    select([rig]+meshes)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery'/name),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
        use_armature_deform_only=False,mesh_smooth_type='FACE',use_mesh_modifiers=False)
def combined(objects,name):
    copies=[]
    for o in objects:
        d=o.copy();d.data=o.data.copy();bpy.context.collection.objects.link(d);copies.append(d)
    select(copies,copies[0]);bpy.ops.object.join();merged=bpy.context.object;merged.name=name
    return merged
for name,meshes in [('FacelessSecurity_V01.glb',[display]+clothes),('FacelessSecurity_Clothing_V01.glb',clothes),('FacelessSecurity_Body_V01.glb',[body])]:
    select([rig]+meshes)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'Delivery'/name),export_format='GLB',use_selection=True,
        export_animations=False,export_skins=True,export_all_influences=True)
fbx('SK_FacelessSecurity_Body_V01.fbx',[body])
cloth=combined(clothes,'Security_Clothing_V01');fbx('SK_FacelessSecurity_Clothing_V01.fbx',[cloth]);bpy.data.objects.remove(cloth,do_unlink=True)
outfit=combined([display]+clothes,'Security_RenderMesh_V01');fbx('SK_FacelessSecurity_V01.fbx',[outfit])
report={'stage':'exported','outfit_triangles':sum(len(p.vertices)-2 for p in outfit.data.polygons),
    'complete_body_triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'bone_count':len(rig.data.bones)+1,
    'clothing_parts':len(clothes),'materials':[m.name for m in outfit.data.materials],
    'rendered':False,'runtime_tested':False}
(ROOT/'export_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_EXPORT_SAVED '+json.dumps(report),flush=True)
