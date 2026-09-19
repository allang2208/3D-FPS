"""Read the supplied Meshy rig and prepare unchanged skin/native motion donors."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix

ROOT=Path(__file__).parent
OUT=ROOT/'prepared'; OUT.mkdir(exist_ok=True)
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
def activate(rig,action):
    rig.animation_data_create(); rig.animation_data.action=action
    if action and len(action.slots):rig.animation_data.action_slot=action.slots[0]
    for t in rig.animation_data.nla_tracks:t.mute=True
def export(path,rig,meshes,anim=False):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+meshes:ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=anim,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',mesh_smooth_type='FACE',path_mode='STRIP')
def meta(rig,meshes):
    return {'object_matrix':[list(r) for r in rig.matrix_world],
        'bones':{b.name:{'parent':b.parent.name if b.parent else None,
            'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local)} for b in rig.data.bones},
        'meshes':[{'name':m.name,'vertices':len(m.data.vertices),'triangles':sum(len(p.vertices)-2 for p in m.data.polygons),
            'bounds':[list(m.matrix_world@__import__('mathutils').Vector(v)) for v in m.bound_box]} for m in meshes]}

report={'meshy_clips':{},'donor_clips':{}}
for name in ['Running','RunFast','Walking']:
    clear();f=next((ROOT/'sources/meshy').rglob('*_Animation_'+name+'_frame_rate_60.fbx'))
    bpy.ops.import_scene.fbx(filepath=str(f),use_anim=True)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.name='Mutant3Root'
    meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
    action=rig.animation_data.action;fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    start,end=action.frame_range
    samples=[]
    for frame in [start,start+(end-start)*.25,start+(end-start)*.5,start+(end-start)*.75,end]:
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
        samples.append({b.name:list((rig.matrix_world@b.matrix).translation) for b in rig.pose.bones if b.name in ['Hips','Head','LeftFoot','RightFoot','LeftHand','RightHand']})
    report['meshy_clips'][name]={'file':str(f),'action':action.name,'frames':[start,end],'fps':fps,'seconds':(end-start)/fps,'samples':samples}
    bpy.context.scene.frame_start=round(start);bpy.context.scene.frame_end=round(end)
    export(OUT/('A_Mutant3_'+name+'.fbx'),rig,meshes,True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/('Meshy_'+name+'_Source.blend')))
    if name=='Running':
        activate(rig,None)
        for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
        bpy.context.view_layer.update();report['target']=meta(rig,meshes)
        export(OUT/'SK_Mutant3_Meshy.fbx',rig,meshes)
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_Meshy_Source.blend'))

for library,selection in [('human-base-animations.glb',{'Zombie_Scratch':'Scratch','Death_D':'Death','Hit_Knockback':'Stagger'}),
                          ('human-addon-animations.glb',{'Zombie_Idle_Crouch':'Idle','Zombie Yell':'Rage'})]:
    clear();bpy.context.scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'sources'/library))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.name='M2MRoot'
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    actions={a.name:a for a in bpy.data.actions}
    if library.startswith('human-base'):
        activate(rig,None)
        for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
        bpy.context.view_layer.update();report['donor']=meta(rig,meshes)
        export(OUT/'SK_M2M_Source.fbx',rig,meshes)
    for name,role in selection.items():
        a=actions[name];activate(rig,a);start,end=a.frame_range
        bpy.context.scene.frame_start=round(start);bpy.context.scene.frame_end=round(end)
        export(OUT/('A_M2M_'+role+'.fbx'),rig,[],True)
        report['donor_clips'][role]={'source':name,'library':library,'frames':[start,end],'fps':30,'seconds':(end-start)/30}
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/('M2M_'+library.replace('.glb','.blend'))))
(ROOT/'authoring_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MUTANT3_PREPARED '+json.dumps({'target':report['target'],'meshy_clips':report['meshy_clips'],'donors':report['donor_clips']}))
