import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'handbrain_rig_complete.blend'))
rig=bpy.data.objects['SK_HandBrain'];scene=bpy.context.scene
scene.render.fps=30;scene.frame_start=1;scene.frame_end=61
# Flatten the material color adjustment to portable textures for FBX/GLB.
texture_dir=root/'textures';texture_dir.mkdir(exist_ok=True)
for obj in [o for o in scene.objects if o.type=='MESH']:
    for mat in obj.data.materials:
        nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        node=bs.inputs['Base Color'].links[0].from_node
        if node.type=='MIX_RGB':
            tex=node.inputs[1].links[0].from_node
            img=tex.image.copy();img.name=obj.name+'_BaseColor'
            data=np.empty(len(img.pixels),dtype=np.float32);img.pixels.foreach_get(data)
            data.reshape(-1,4)[:,:3]*=np.array(node.inputs[2].default_value[:3],dtype=np.float32)
            img.pixels.foreach_set(data);img.filepath_raw=str(texture_dir/(img.name+'.png'));img.file_format='PNG';img.save();img.pack()
            tex.image=img;nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
def rotate(n,axis,degrees):
    p=rig.pose.bones[n];q=p.bone.matrix_local.to_quaternion()
    p.rotation_mode='QUATERNION';p.rotation_quaternion=q.inverted()@Quaternion(axis,math.radians(degrees))@q
def translate(n,world):
    p=rig.pose.bones[n];p.location=p.bone.matrix_local.to_quaternion().inverted()@Vector(world)
def reset():
    for p in rig.pose.bones:p.location=(0,0,0);p.scale=(1,1,1);p.rotation_mode='QUATERNION';p.rotation_quaternion=(1,0,0,0)
    rig.pose.bones['arm_mount'].scale=(.055,)*3;rig.pose.bones['fan_mount'].scale=(.06,)*3
def interp(t,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:
            q=max(0,min(1,(t-a)/(b-a)));q=q*q*(3-2*q);return x+(y-x)*q
    return keys[-1][1]
def attack(t,contact_angle):
    spread=interp(t,[(0,0),(.2,0),(.55,1),(.95,1),(1.15,1),(1.8,0),(2,0)])
    extension=interp(t,[(0,.055),(.32,.055),(.60,.5),(.83,1),(1.18,1),(1.72,.055),(2,.055)])
    tilt=interp(t,[(0,0),(.45,-4),(.80,-3),(1,4),(1.14,3),(1.8,0),(2,0)])
    rotate('cranium',(0,1,0),tilt)
    rotate('neck',(0,1,0),tilt*.22)
    angle=interp(t,[(0,-38),(.55,-38),(.78,-27),(1,contact_angle),(1.08,contact_angle),(1.2,contact_angle-5),(1.65,-38),(2,-38)])
    rotate('arm_mount',(0,1,0),angle)
    rig.pose.bones['arm_mount'].scale=(extension,)*3
    rig.pose.bones['fan_mount'].scale=(.06+.94*spread,)*3
    for j in range(8):
        a=j*math.tau/8;axis=(-math.sin(a),math.cos(a),0)
        rotate(f'crown_{j:02}',axis,spread*5)
        rotate(f'fan_{j:02}',axis,spread*(5+2*math.sin(a)))
def arm_minz():
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();o=bpy.data.objects['HandBrain_AttackArm'];e=o.evaluated_get(deps)
    m=e.to_mesh();v=min((e.matrix_world@p.co).z for p in m.vertices);e.to_mesh_clear();return v
# Calibrate the impact pose to the same floor used by the body.
lo,hi=0.,35.
for _ in range(16):
    mid=(lo+hi)/2;reset();attack(1,mid)
    if arm_minz()>.012:lo=mid
    else:hi=mid
contact_angle=(lo+hi)/2
clips={};rig.animation_data_create()
for name,duration in [('Idle',2),('Move',1),('Attack_Slam',2)]:
    action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    total=round(duration*30)
    for k in range(total+1):
        t=k/30;reset()
        if name=='Idle':
            s=math.sin(math.tau*t/2)
            rotate('neck',(0,1,0),.45*s);rotate('cranium',(1,0,0),.35*math.sin(math.tau*t/2))
            rig.pose.bones['cranium'].scale=(1+.003*s,1+.005*s,1+.003*s)
            for j in range(8):
                a=j*math.tau/8;rotate(f'crown_{j:02}',(-math.sin(a),math.cos(a),0),.8*math.sin(math.tau*t/2+a))
        elif name=='Move':
            s=math.sin(math.tau*t)
            rotate('neck',(0,1,0),2.8*s);rotate('cranium',(0,1,0),-1.4*math.sin(math.tau*t-.65))
            rotate('cranium',(1,0,0),1.0*math.sin(math.tau*t+.4))
            translate('neck',(.026*s,0,0))
            for j in range(8):
                a=j*math.tau/8;rotate(f'crown_{j:02}',(-math.sin(a),math.cos(a),0),1.5*math.sin(math.tau*t+a))
        else:attack(t,contact_angle)
        for p in rig.pose.bones:
            p.keyframe_insert('location',frame=k+1);p.keyframe_insert('rotation_quaternion',frame=k+1);p.keyframe_insert('scale',frame=k+1)
    clips[name]={'duration_s':duration,'fps':30,'frames':[1,total+1],'loop':name!='Attack_Slam','root_motion':False}
    if name=='Attack_Slam':clips[name].update({'hit_time_s':1.,'hit_frame_30fps':31,'source_frame_1based':14})
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type in {'ARMATURE','MESH'}:o.select_set(True)
bpy.context.view_layer.objects.active=rig
export=root/'delivery';export.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(export/'SK_HandBrain_Animated.fbx'),use_selection=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.export_scene.gltf(filepath=str(export/'HandBrain_Animated.glb'),use_selection=True,export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_skins=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(export/'HandBrain_Animated.blend'))
report=json.loads((root/'build_report.json').read_text());report.update({'clips':clips,'impact_mount_degrees':contact_angle,'rig_visual_verified':True,'animation_authored':True,'animation_verified':False,'ue_runtime_verified':False})
(root/'build_report.json').write_text(json.dumps(report,indent=2))
(export/'animation_contract.json').write_text(json.dumps(clips,indent=2))
