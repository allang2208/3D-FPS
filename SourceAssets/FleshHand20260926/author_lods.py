"""Create skinned distance meshes from the hand authoring file; no render/test."""
from pathlib import Path
import json
import bpy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'LocalRig'
LOD_DIR=OUT/'LODs'
LOD_DIR.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'FleshHand_Green_LocalRigV1.blend'))
scene=bpy.context.scene
source=next(o for o in scene.objects if o.type=='MESH')
rig=next(o for o in scene.objects if o.type=='ARMATURE')
source.data.calc_loop_triangles()
base_triangles=len(source.data.loop_triangles)
records=[]
for level,ratio in ((1,.50),(2,.20)):
    mesh=source.copy()
    mesh.data=source.data.copy()
    scene.collection.objects.link(mesh)
    mesh.name='SK_FleshHand_Green_LOD%d'%level
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    reduction=mesh.modifiers.new('Distance surface reduction','DECIMATE')
    reduction.decimate_type='COLLAPSE'
    reduction.ratio=ratio
    reduction.use_collapse_triangulate=True
    # Apply topology reduction in bind coordinates before skin deformation.
    bpy.ops.object.modifier_move_up(modifier=reduction.name)
    bpy.ops.object.modifier_apply(modifier=reduction.name)
    for vertex in mesh.data.vertices:
        influences=sorted([(g.group,g.weight) for g in vertex.groups if g.weight>1e-6],
                          key=lambda pair:pair[1],reverse=True)[:4]
        total=sum(weight for _,weight in influences)
        if total<=0:
            raise RuntimeError('LOD vertex has no skin influence; authoring must be repaired.')
        for group in list(vertex.groups):
            mesh.vertex_groups[group.group].remove([vertex.index])
        for group,weight in influences:
            mesh.vertex_groups[group].add([vertex.index],weight/total,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    fbx=LOD_DIR/(mesh.name+'.fbx')
    glb=LOD_DIR/(mesh.name+'.glb')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,
        object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,
        use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
        use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='COPY',embed_textures=True)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_animations=False,export_skins=True,export_all_influences=False,
        export_def_bones=True,export_yup=True,export_normals=True,export_tangents=True,
        export_morph=False,export_materials='EXPORT',export_extras=True)
    mesh.data.calc_loop_triangles()
    records.append({'level':level,'ratio':ratio,'triangles':len(mesh.data.loop_triangles),
                    'vertices':len(mesh.data.vertices),'max_influences':4,
                    'fbx':str(fbx.relative_to(ROOT)),'glb':str(glb.relative_to(ROOT))})
    mesh.hide_set(True)
    mesh.hide_render=True
source.hide_set(False)
bpy.ops.object.select_all(action='DESELECT')
source.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FleshHand_Green_WithLODs.blend'))
receipt={'base_triangles':base_triangles,'lods':records,'shared_skeleton':True,
         'material_slots':1,'ue_lod_switching_configured':False,'rendered':False,'tested':False}
(LOD_DIR/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FLESHHAND_LODS_SAVED '+json.dumps(receipt),flush=True)
