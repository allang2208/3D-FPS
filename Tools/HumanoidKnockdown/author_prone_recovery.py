"""Add a body-axis roll before the fitted supine rise; keep every frame grounded."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HumanoidKnockdown20260926/fitted')
meta=json.loads((ROOT/'authored_clips.json').read_text())
FPS=60
ROLL=48
for role,clips in meta.items():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/(role+'_Recovery.blend')))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
    source=bpy.data.actions['A_'+role+'_LayToIdle']
    rig.animation_data.action=source
    if source.slots:rig.animation_data.action_slot=source.slots[0]
    scene=bpy.context.scene
    samples=[]
    for i in range(round(clips[source.name]['seconds']*FPS)+1):
        scene.frame_set(i)
        samples.append({b.name:b.matrix_basis.copy() for b in rig.pose.bones})
    scene.frame_set(0)
    pelvis='Hips' if role in ['FatZombie','Mutant3'] else 'pelvis'
    head='Head' if pelvis=='Hips' else 'head'
    initial=rig.pose.bones[pelvis].matrix.copy()
    axis=(rig.pose.bones[head].matrix.translation-initial.translation).normalized()
    name='A_'+role+'_ProneToIdle'
    action=bpy.data.actions.new(name);action.use_fake_user=True
    rig.animation_data.action=action
    scene.frame_start=0;scene.frame_end=ROLL+len(samples)-1
    previous={}
    for f in range(scene.frame_end+1):
        scene.frame_set(f)
        for b in rig.pose.bones:b.matrix_basis=samples[max(0,f-ROLL)][b.name]
        bpy.context.view_layer.update()
        if f<ROLL:
            t=f/ROLL;weight=t*t*(3-2*t)
            roll=Quaternion(axis,math.pi*(1-weight))
            # Rotate the body as a unit around its long axis. Snapshot blending
            # only joins the physical limbs to this authored prone start pose.
            rig.pose.bones[pelvis].matrix=Matrix.LocRotScale(initial.translation,roll@initial.to_quaternion(),Vector((1,1,1)))
            bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get();low=float('inf')
            for mesh in meshes:
                ob=mesh.evaluated_get(deps);skin=ob.to_mesh()
                low=min(low,min((ob.matrix_world@v.co).z for v in skin.vertices));ob.to_mesh_clear()
            m=rig.pose.bones[pelvis].matrix.copy()
            m.translation+=rig.matrix_world.inverted().to_3x3()@Vector((0,0,.003-low))
            rig.pose.bones[pelvis].matrix=m
            bpy.context.view_layer.update()
        for b in rig.pose.bones:
            q=b.rotation_quaternion.copy()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            b.rotation_quaternion=q;previous[b.name]=q.copy()
            for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f,group=b.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig]+meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(ROOT/(name+'.fbx')),use_selection=True,
        object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
    clips[name]={'file':str(ROOT/(name+'.fbx')),'seconds':scene.frame_end/FPS,'fps':FPS,
        'source':'LayToIdle with authored 0.8 second grounded prone-to-supine roll'}
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(role+'_Recovery.blend')))
(ROOT/'authored_clips.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print('PRONE_RECOVERY_AUTHORED',flush=True)
