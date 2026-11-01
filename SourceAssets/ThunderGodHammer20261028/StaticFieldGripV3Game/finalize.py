"""Package only the retopologized game mesh, with freshly baked leather maps."""
import bpy, json, hashlib
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).resolve().parent
receipt=json.loads((P/'bake_receipt.json').read_text())
if not receipt['complete']:raise RuntimeError('Leather baking is not complete')
bpy.ops.wm.open_mainfile(filepath=str(P/'StaticField_Design.blend'))
bpy.context.preferences.filepaths.save_version=0
parts=list(bpy.data.collections['StaticField_EditableParts'].objects)
for mat in bpy.data.materials:
    if mat.name!='M_StaticField_Leather':continue
    for node in mat.node_tree.nodes:
        if node.type!='TEX_IMAGE' or not node.image:continue
        for kind in ('BaseColor','ORM','Normal'):
            if '_'+kind not in node.image.name:continue
            node.image=bpy.data.images.load(str(P/'Textures'/('T_StaticField_Leather_'+kind+'.png')),check_existing=False)
            node.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'StaticField_Design.blend'))
counts=[];copies=[]
for ob in parts:
    ob.hide_render=False;ob.hide_set(False)
    ob.data.calc_loop_triangles()
    counts.append(dict(part=ob.name,triangles=len(ob.data.loop_triangles)))
    copy=ob.copy();copy.data=ob.data.copy()
    bpy.context.scene.collection.objects.link(copy);copies.append(copy)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0]
bpy.ops.object.join();joined=bpy.context.object
joined.name='SM_ThunderGodHammer_grip_static_field_V3Game'
joined.data.transform(Matrix.Translation((0,0,-.405)));joined.location=(0,0,0)
joined.data.calc_loop_triangles()
triangles=len(joined.data.loop_triangles)
fbx=P/'Export'/(joined.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.export_scene.gltf(filepath=str(P/'Export/StaticFieldGripGame.glb'),export_format='GLB',use_selection=True,export_apply=True)
joined.hide_render=True;joined.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StaticField_Editable.blend'))
manifest=dict(revision='StaticFieldGripV3Game',mesh=joined.name,fbx=str(fbx),fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
    triangles=triangles,high_source_triangles=1960020,parts=counts,material_slots=len(joined.data.materials),
    materials=json.loads((P/'material_manifest.json').read_text()),interface='thunder_god_hammer_modular_v1',location_cm=[0,0,40.5],
    source='StaticField_Editable.blend',high_source='../StaticFieldGripV2/StaticField_Editable.blend',
    geometry='Structured quad retopology: 128x256 seam-adaptive leather, lower sample-count closed metal sweeps and seals; exact V2 native interface meshes and corner normals.',
    baked_detail='Original V2 two-ply stitch geometry and leather shading transferred with selected-to-active tangent normals, base color and packed ORM.',
    textures='Leather 4096x8192 bake; existing metal 4096x4096 materials reused; streamed, no POM.',
    nanite=True,fallback_fraction=.15,runtime_tested=False)
(P/'runtime_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('STATIC_FIELD_GAME_EXPORTED',triangles,'triangles',len(joined.data.materials),'materials',flush=True)
