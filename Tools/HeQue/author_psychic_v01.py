"""Original suspended-heart pulse animation, core weight mask and spherical wave."""
import ast,bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/PsychicV01'
for folder in ('Authoring','Export','Textures','Audio','Records','Before'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];body=bpy.data.objects['HeQueBody'];rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones};ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive));desired={}
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
for path,names in (('author_side_crush.py',('ease','curve','transform','at')),('author_rig_motion.py',('solve_two',))):
    tree=ast.parse((PROJECT/'Tools/HeQue'/path).read_text('utf8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'HeQue/psychic_helpers','exec'))
CORE=('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002')
vertices=np.array([v.co[:] for v in body.data.vertices]);core_weights=np.zeros(len(vertices))
for v in body.data.vertices:
    core_weights[v.index]=sum(g.weight for g in v.groups if body.vertex_groups[g.group].name in CORE)
center=Vector(vertices[core_weights>.65].mean(axis=0).tolist())
END=5.2;FPS=120;PULSES=(1.6,2.2,2.8)
def pulse(t,p):
    return curve(t,[(0,0),(p-.10,-.18),(p,0),(p+.055,1),(p+.10,.82),(p+.23,-.20),(p+.42,0),(END,0)])
def pose(t):
    desired.clear()
    tension=curve(t,[(0,0),(.45,.22),(1.25,.95),(1.60,1),(2.80,1),(3.15,.35),(3.6,.12),(END,0)])
    beat=sum(pulse(t,p)*g for p,g in zip(PULSES,(1.,1.06,1.12)))
    spent=curve(t,[(0,0),(2.8,0),(3.25,1),(3.8,.85),(4.6,.3),(END,0)])
    top=heads['HQ_Arch'];brace=Vector((.008*spent,.018*tension+.028*max(0,beat),-.045*tension-.055*spent))
    mass=Matrix.Translation(top+brace)@Matrix.Rotation(math.radians(-2*tension-3.5*max(0,beat)+3*spent),4,'X')@Matrix.Translation(-top)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    for side,s in sides.items():
        sign=-1 if side=='R' else 1
        spread=Matrix.Translation(top)@Matrix.Rotation(math.radians(-sign*(8.5*tension+2*max(0,beat))),4,'Y')@Matrix.Translation(-top)
        half=mass@spread
        for name in s['arch']:transform(name,half)
        hip=half@heads[s['upper']];foot=heads[s['foot']].copy();knee=solve_two(hip,foot,s)
        at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        for name in (s['foot'],s['toe'],s['tip']):transform(name,Matrix.Identity(4))
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    # Component-space scale affects only the real suspended organ, once. No
    # inherited exponential scale along its chain, and no alternate core mesh.
    lateral=1-.10*tension+.32*beat;depth=1-.07*tension+.27*beat;vertical=1+.035*tension-.10*beat
    tremor=.004*math.sin(t*math.tau*14)*tension*(1-max(0,beat))
    sway=math.radians(2.5*math.sin(t*8)*spent)
    organ=mass@Matrix.Translation(center+Vector((tremor,-.045*tension,.115*tension-.065*spent)))@Matrix.Rotation(sway,4,'X')@Matrix.Diagonal((lateral,depth,vertical,1.))@Matrix.Translation(-center)
    for name in CORE:transform(name,organ)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length;swing=0.
        for p in PULSES:
            age=t-p-.055-i*.012
            if age>=0:swing+=math.sin(age*18)*math.exp(-age*6)*.22
        direction=(Vector((-.006,.002,-.0355)).normalized()+Vector((swing*.12,swing,0))).normalized()
        if current.z+direction.z*length<.025:
            direction.z=max(-1.,min(1.,(.025-current.z)/length))
            horizontal=Vector((direction.x,direction.y,0)).normalized()*math.sqrt(max(0.,1-direction.z**2))
            direction.x=horizontal.x;direction.y=horizontal.y
        target=current+direction*length;at(name,current,target);current=target
    for b in ordered:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=round(END*FPS)+1
name='A_HeQue_PsychicHeartV01';action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
for f in range(scene.frame_end):
    scene.frame_set(f+1);pose(f/FPS)
    for b in rig.pose.bones:
        for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f+1,group=b.name)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_PsychicHeart_v01.blend'))

# Rasterize a data mask from the real organ's skin weights into its unchanged UV
# atlas. The overlay is bound only to the flesh slot, never to the iron links.
size=1024;mask=np.zeros((size,size),dtype=np.float32);uv=body.data.uv_layers.active.data
body.data.calc_loop_triangles()
for tri in body.data.loop_triangles:
    weights=np.array([core_weights[i] for i in tri.vertices]);weights=np.clip((weights-.12)/.73,0,1)
    if weights.max()<.001:continue
    xy=np.array([uv[i].uv[:] for i in tri.loops])*(size-1)
    lo=np.maximum(0,np.floor(xy.min(axis=0)).astype(int));hi=np.minimum(size-1,np.ceil(xy.max(axis=0)).astype(int))
    if np.any(hi<lo):continue
    a,b,c=xy;d=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(d)<1e-8:continue
    yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/d
    v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/d;w=1-u-v
    inside=(u>=-.015)&(v>=-.015)&(w>=-.015)
    values=np.where(inside,np.clip(u*weights[0]+v*weights[1]+w*weights[2],0,1),0)
    tile=mask[lo[1]:hi[1]+1,lo[0]:hi[0]+1];np.maximum(tile,values,out=tile)
pixels=np.ones((size,size,4),dtype=np.float32);pixels[:,:,:3]=mask[:,:,None]
image=bpy.data.images.new('T_HeQue_CoreMaskV01',size,size,alpha=True)
image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(pixels.ravel())
image.filepath_raw=str(ROOT/'Textures/T_HeQue_CoreMaskV01.png');image.file_format='PNG';image.save()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=1.)
shell=bpy.context.object;shell.name='SM_HeQue_PsychicShellV01'
for v in shell.data.vertices:
    theta=math.atan2(v.co.y,v.co.x);height=v.co.z
    v.co*=1-.014*(.5+.5*math.sin(theta*9+height*13))*(1-height*height)
for poly in shell.data.polygons:poly.use_smooth=True
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SM_HeQue_PsychicShellV01.fbx'),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_PsychicShell_v01.blend'))
report=dict(clip=name,duration=END,fps=FPS,releases=PULSES,wave_seconds=.36,radius_cm=1000,damage_per_wave=25,
    cooldown=18,fear_seconds=3,fear_applications_per_cast=1,core_center_source=list(center),
    reference_heads={n:list(heads[n]) for n in ('HQ_Root','HQ_Arch','Bone_006','Bone_013')},
    fixed_wave_components=3,mask_size=size,gameplay_tested=False,rendered=False)
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_PSYCHIC_AUTHORED '+json.dumps(report),flush=True)
