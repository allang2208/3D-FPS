"""Derive static poses from the delivered V3 FBX only; never save the 5.2 blend."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'input/TreasureChest_v3/exports/TreasureChest_v3.fbx'
OUT=ROOT/'derived';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SRC),use_anim=True)
sc=bpy.context.scene
meshes=[o for o in sc.objects if o.type=='MESH']
rig=next(o for o in sc.objects if o.type=='ARMATURE')
report={'source':str(SRC),'blender':bpy.app.version_string,'source_blend_saved':False,'poses':[]}
for name,frame in [('SM_TreasureChest_Closed',1),('SM_TreasureChest_Open',31)]:
    sc.frame_set(frame);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    bpy.ops.object.select_all(action='DESELECT');copies=[];points=[];count=0
    for ob in meshes:
        ev=ob.evaluated_get(dg)
        me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
        new=bpy.data.objects.new(name,me);sc.collection.objects.link(new)
        new.matrix_world=ev.matrix_world.copy();new.select_set(True);copies.append(new)
        me.calc_loop_triangles();count+=len(me.loop_triangles)
        points.extend(new.matrix_world@v.co for v in me.vertices)
    assert count==158044, count
    bpy.context.view_layer.objects.active=copies[0]
    path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        use_mesh_modifiers=False,mesh_smooth_type='FACE',use_tspace=True,
        add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
    report['poses'].append({'name':name,'frame':frame,'triangles':count,'file':str(path),
        'bounds_m':[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]],
        'lid_rotation':list(rig.pose.bones['Lid'].rotation_quaternion)})
    for ob in copies:bpy.data.objects.remove(ob,do_unlink=True)
(OUT/'provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
