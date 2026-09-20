"""Read-only comparison of the gameplay idle mesh against the migrated source."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector

OUT=Path(__file__).parent
AUTHOR=OUT.parent
bpy.ops.wm.open_mainfile(filepath=str(AUTHOR/'M16_Manny_Editable.blend'),use_scripts=False)
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
idle=bpy.data.actions['M16_idle']
rig.animation_data.action=idle;rig.animation_data.action_slot=idle.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
receipt=json.loads((AUTHOR/'build.json').read_text())
fit=Matrix.Translation(Vector(receipt['fit_translation_m']))@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Scale(.01,4)
root=rig.pose.bones['WPN_root'].matrix.copy()
original={}
with bpy.data.libraries.load(str(AUTHOR.parent/'M16A2Migration20260919/M16A2_Mechanical_Editable.blend'),link=False) as (source,target):
    target.objects=[n for n in source.objects if n.startswith('M16A2_')]
for ob in target.objects:
    if ob.type=='MESH':original[ob.name.removesuffix('.001')]=ob.data
dg=bpy.context.evaluated_depsgraph_get()
results={}
for ob in bpy.context.scene.objects:
    if not ob.name.startswith('M16A2_') or ob.type!='MESH':continue
    source=original.get(ob.name) or original.get(ob.data.name.removesuffix('.001'))
    if source is None:
        results[ob.name]={'source_mesh_missing':True,'source_names':list(original)};continue
    ev=ob.evaluated_get(dg);mesh=ev.to_mesh()
    errors=[]
    for before,after in zip(source.vertices,mesh.vertices):
        expected=fit@before.co
        actual=root.inverted()@rig.matrix_world.inverted()@ev.matrix_world@after.co
        errors.append((actual-expected).length*100)
    bone=rig.data.bones[ob.vertex_groups[0].name]
    local=bone.parent.matrix_local.inverted()@bone.matrix_local
    results[ob.name]={'vertices':len(errors),'max_vertex_error_cm':max(errors),'mean_vertex_error_cm':sum(errors)/len(errors),
        'bone':bone.name,'parent':bone.parent.name,'rest_local_rotation_deg':[math.degrees(a) for a in local.to_euler()]}
    ev.to_mesh_clear()
tag=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
(OUT/f'part-binding-{tag}.json').write_text(json.dumps(results,indent=2))
print('M16_PART_BINDINGS '+json.dumps(results),flush=True)
