"""M08: retain the rebuilt surface; author a fitted, non-humanoid rig and actions.
Background production only. No scene rendering or gameplay tests.
"""
import bpy, json, math
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector, Quaternion

ROOT=Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)
ANIM=ROOT/'Animations'; ANIM.mkdir(exist_ok=True)
TEX=ROOT/'Textures'; TEX.mkdir(exist_ok=True)
SOURCE=ROOT.parent/'BackRebuildV02_20261004/M08_BackRebuilt_V02.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
obj=bpy.data.objects['M08_BackRebuilt_V02']
for other in list(bpy.data.objects):
    if other != obj: bpy.data.objects.remove(other,do_unlink=True)
obj.hide_set(False);obj.hide_render=False
obj.name='SK_LurkerM08'
obj.vertex_groups.clear()
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
scene.render.fps=60;scene.render.fps_base=1.
scene.render.engine='BLENDER_EEVEE'
v=np.array([list(obj.matrix_world@p.co) for p in obj.data.vertices])
lo=v.min(axis=0);hi=v.max(axis=0)
scale=2.6/(hi[1]-lo[1]);offset=Vector((-(lo[0]+hi[0])*.5,0.,-lo[2]))
transform=Matrix.Scale(scale,4)@Matrix.Translation(offset)@obj.matrix_world
normals=[Vector(n.vector) for n in obj.data.corner_normals]
normalmat=transform.to_3x3().inverted().transposed()
obj.data.transform(transform);obj.matrix_world=Matrix.Identity(4)
obj.data.normals_split_custom_set([(normalmat@n).normalized() for n in normals])

def point(x,y,z):return Vector(((x+offset.x)*scale,y*scale,(z+offset.z)*scale))
spec=[]
def bone(name,a,b,parent='root',region='body',deform=True):
    spec.append(dict(name=name,head=list(point(*a)),tail=list(point(*b)),parent=parent,region=region,deform=deform))
spec.append(dict(name='root',head=[0,0,0],tail=[0,0,.12],parent=None,region='root',deform=False))
bone('pelvis',(0,.52,-.055),(0,.27,-.095))
bone('spine_01',(0,.27,-.095),(0,.01,-.10),'pelvis')
bone('spine_02',(0,.01,-.10),(0,-.24,-.075),'spine_01')
bone('chest',(0,-.24,-.075),(0,-.45,-.06),'spine_02')
bone('neck',(0,-.45,-.06),(0,-.65,-.12),'chest','head')
bone('head',(0,-.65,-.12),(0,-.85,-.17),'neck','head')
bone('jaw',(0,-.665,-.205),(0,-.865,-.305),'head','jaw')
# Existing melee implementation resolves this compatibility anchor; it carries
# no skin or physics and is located at the oral centre, not at the neck pivot.
bone('Wolf_-Head',(0,-.82,-.21),(0,-.90,-.21),'head','anchor',False)
for side,s in [('L',1),('R',-1)]:
    def p(x,y,z):return (s*x,y,z)
    bone('scapula.'+side,p(.12,-.38,-.01),p(.275,-.405,-.03),'chest','front_'+side)
    bone('upperarm.'+side,p(.275,-.405,-.03),p(.425,-.235,-.27),'scapula.'+side,'front_'+side)
    bone('forearm.'+side,p(.425,-.235,-.27),p(.475,-.62,-.345),'upperarm.'+side,'front_'+side)
    bone('hand.'+side,p(.475,-.62,-.345),p(.495,-.755,-.388),'forearm.'+side,'front_'+side)
    for i,(ax,ay,bx,by,cx,cy) in enumerate([
        (.422,-.723,.356,-.785,.302,-.837),(.451,-.774,.432,-.865,.413,-.931),
        (.492,-.790,.495,-.874,.500,-.946),(.534,-.776,.563,-.862,.589,-.926),
        (.560,-.741,.617,-.788,.678,-.827)]):
        region='finger_'+side
        bone('finger%d_01.%s'%(i+1,side),p(ax,ay,-.391),p(bx,by,-.403),'hand.'+side,region)
        bone('finger%d_02.%s'%(i+1,side),p(bx,by,-.403),p(cx,cy,-.411),'finger%d_01.%s'%(i+1,side),region)
    bone('thigh.'+side,p(.235,.565,-.025),p(.390,.440,-.185),'pelvis','rear_'+side)
    bone('calf.'+side,p(.390,.440,-.185),p(.465,.825,-.225),'thigh.'+side,'rear_'+side)
    bone('ankle.'+side,p(.465,.825,-.225),p(.475,.805,-.375),'calf.'+side,'rear_'+side)
    bone('hindfoot.'+side,p(.475,.805,-.375),p(.480,.705,-.41),'ankle.'+side,'rear_'+side)
    for i,x in enumerate([.417,.473,.529]):
        bone('toe%d.%s'%(i+1,side),p(x,.771,-.397),p(x,.686,-.414),'hindfoot.'+side,'rear_'+side)
    bone('arch_front.'+side,p(.152,-.420,.058),p(.09,-.08,.36),'chest','arch')
    bone('arch_rear.'+side,p(.155,.605,.06),p(.09,.23,.38),'pelvis','arch')
bone('arch_crown',(0,.04,.37),(0,.24,.385),'spine_02','arch')

arm=bpy.data.armatures.new('M08_FittedSkeleton')
rig=bpy.data.objects.new('Armature',arm);scene.collection.objects.link(rig)
rig.show_in_front=True
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for row in spec:
    b=arm.edit_bones.new(row['name']);b.head=row['head'];b.tail=row['tail'];b.use_deform=row['deform']
    if row['parent']:b.parent=arm.edit_bones[row['parent']]
    d=(b.tail-b.head).normalized()
    b.align_roll(Vector((1,0,0)) if abs(d.x)<.8 else Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT')
for title,prefixes in [('Body',('body',)),('Mouth',('head','jaw','anchor')),
                       ('Hands',('front_','finger_')),('Hindlegs',('rear_',)),('Dorsal arch',('arch',))]:
    col=arm.collections.new(title)
    for row in spec:
        if any(row['region'].startswith(p) for p in prefixes):col.assign(arm.bones[row['name']])

print('M08_RIG: calculating compartment-constrained surface weights',flush=True)
coords=np.array([list(p.co) for p in obj.data.vertices],dtype=np.float32)
raw=coords/scale-np.array(offset)
x,y,z=raw.T;ax=np.abs(x)
def smooth(a,b,q):
    t=np.clip((q-a)/(b-a),0,1);return t*t*(3-2*t)
deforms=[r for r in spec if r['deform']];names=[r['name'] for r in deforms]
weights=np.zeros((len(coords),len(deforms)),dtype=np.float32)
archmask=smooth(.045,.135,z)
jawmask=(1-smooth(-.695,-.63,y))*(1-smooth(-.235,-.195,z))*(1-smooth(.16,.225,ax))
for i,row in enumerate(deforms):
    a=np.array(row['head']);b=np.array(row['tail']);d=b-a
    t=np.clip(((coords-a)@d)/np.dot(d,d),0,1)
    dist=np.linalg.norm(coords-(a+t[:,None]*d),axis=1)
    region=row['region'];mask=np.ones(len(coords),dtype=np.float32)
    if region=='arch':mask=archmask
    else:mask*=1-archmask
    if region=='jaw':mask*=jawmask
    else:mask*=1-jawmask
    if region.startswith(('front_','finger_','rear_')):
        sign=1 if region.endswith('L') else -1
        mask*=smooth(.09,.22,x*sign)
        mask*=1-smooth(-.04,.035,z)
        if region.startswith(('front_','finger_')):mask*=1-smooth(-.12,.15,y)
        else:mask*=smooth(.04,.25,y)
        if region.startswith('finger_'):mask*=1-smooth(-.735,-.65,y)
    if region=='head':mask*=1-smooth(-.47,-.23,y)
    weights[:,i]=mask/np.maximum(dist,.022*scale)**4
# A bounded edge diffusion softens joints without crossing from fingers/legs
# through nearby but topologically disconnected surfaces.
edges=np.empty(len(obj.data.edges)*2,dtype=np.int32);obj.data.edges.foreach_get('vertices',edges)
edges=edges.reshape(-1,2);aa=edges[:,0];bb=edges[:,1]
weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-20)
degree=np.bincount(np.r_[aa,bb],minlength=len(coords)).astype(np.float32)
for iteration in range(4):
    for i in range(len(deforms)):
        avg=(np.bincount(aa,weights=weights[bb,i],minlength=len(coords))+
             np.bincount(bb,weights=weights[aa,i],minlength=len(coords)))/np.maximum(degree,1)
        weights[:,i]=weights[:,i]*.70+avg*.30
top=np.argpartition(weights,-4,axis=1)[:,-4:]
chosen=np.take_along_axis(weights,top,axis=1)
chosen/=np.maximum(chosen.sum(axis=1,keepdims=True),1e-20)
# Quantize only the weight encoding, retaining four influences and source mesh.
units=np.rint(chosen*4095).astype(np.int32)
units[np.arange(len(units)),np.argmax(units,axis=1)]+=4095-units.sum(axis=1)
for i,name in enumerate(names):
    group=obj.vertex_groups.new(name=name)
    rows,cols=np.where(top==i)
    values=units[rows,cols]
    for value in np.unique(values):
        if value>0:group.add(rows[values==value].tolist(),float(value)/4095.,'REPLACE')
mod=obj.modifiers.new('M08 skeletal deformation','ARMATURE');mod.object=rig
mod.use_deform_preserve_volume=False
obj.parent=rig

# Save the exact material inputs for UE (glTF normal maps use +Y).
texture_manifest=[]
for mi,mat in enumerate(obj.data.materials):
    row={'slot':mi,'name':mat.name,'images':[]}
    for node in mat.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image:
            im=node.image
            safe='slot%d_%s.png'%(mi,''.join(c if c.isalnum() or c in '_-' else '_' for c in im.name))
            dest=TEX/safe
            im.filepath_raw=str(dest);im.file_format='PNG';im.save();im.pack()
            row['images'].append({'file':str(dest),'node':node.name,'image':im.name,'colorspace':im.colorspace_settings.name})
    texture_manifest.append(row)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
common=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SK_LurkerM08.fbx'),object_types={'ARMATURE','MESH'},
                        bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type='OFF',
                        path_mode='COPY',embed_textures=False,**common)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'SK_LurkerM08.glb'),export_format='GLB',use_selection=True,
                         export_animations=False,export_skins=True,export_all_influences=False)

NAMES=[b.name for b in arm.bones]
PARENT={b.name:b.parent.name if b.parent else None for b in arm.bones}
REST={b.name:b.matrix_local.copy() for b in arm.bones}
LOCAL={n:REST[PARENT[n]].inverted()@REST[n] if PARENT[n] else REST[n].copy() for n in NAMES}
def fk(local):
    w={}
    for n in NAMES:w[n]=w[PARENT[n]]@local[n] if PARENT[n] else local[n].copy()
    return w
def orient(local,n,worldq):
    w=fk(local);parent=PARENT[n]
    q=w[parent].to_quaternion().inverted()@worldq if parent else worldq
    local[n]=Matrix.LocRotScale(local[n].translation,q,Vector((1,1,1)))
def turn(local,n,angle,axis=(1,0,0)):
    w=fk(local);q=Quaternion(Vector(axis),angle)@w[n].to_quaternion();orient(local,n,q)
def aim(local,n,direction,child):
    ref=REST[child].translation-REST[n].translation
    orient(local,n,ref.normalized().rotation_difference(direction.normalized())@REST[n].to_quaternion())
def ik(local,chain,goal,pole):
    w=fk(local);a,b,c=[w[n].translation.copy() for n in chain]
    l1=(REST[chain[1]].translation-REST[chain[0]].translation).length
    l2=(REST[chain[2]].translation-REST[chain[1]].translation).length
    d=goal-a;r=max(abs(l1-l2)+.0001,min(d.length,(l1+l2)*.998));axis=d.normalized()
    pole=Vector(pole);pole-=axis*pole.dot(axis);pole.normalize()
    along=(l1*l1-l2*l2+r*r)/(2*r)
    mid=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along));end=a+axis*r
    aim(local,chain[0],mid-a,chain[1]);aim(local,chain[1],end-mid,chain[2])
def ease(t):t=max(0,min(1,t));return t*t*(3-2*t)
def curve(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,av),(b,bv) in zip(keys,keys[1:]):
        if t<=b:return av+(bv-av)*ease((t-a)/(b-a))
    return keys[-1][1]
clips={'Idle':(3.,True),'IdleAlert':(1.8,True),'Walk':(.9,True),'Run':(.6,True),
       'AttackBite':(.85,False),'AttackPounce':(1.10,False),
       'HitFront':(.55,False),'HitLeft':(.55,False),'HitRight':(.55,False),'Death':(1.4,False)}
report={'source':str(SOURCE),'mesh':str(ROOT/'SK_LurkerM08.fbx'),'scale':scale,
        'dimensions_m':((hi-lo)*scale).tolist(),'bones':spec,'texture_slots':texture_manifest,
        'vertices':len(coords),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
        'stride_speeds_cm_s':{'Walk':100.,'Run':210.},'clips':{},
        'runtime_tested':False,'preview_rendered':False,'surface_decimated':False}
rig.animation_data_create()
# Mesh evaluation is unnecessary while baking bone curves.
mod.show_viewport=False
for role,(duration,loop) in clips.items():
    action=bpy.data.actions.new('A_M08_'+role);action.use_fake_user=True
    rig.animation_data.action=action
    count=round(duration*60);scene.frame_start=1;scene.frame_end=count+1
    for frame in range(1,count+2):
        t=(frame-1)/60.;phase=t/duration
        local={n:m.copy() for n,m in LOCAL.items()}
        breath=math.sin(phase*math.tau)
        bodyz=.007*breath;bodyy=0.;pitch=0.;roll=0.;jaw=-26.
        forward=0.;lift=0.;finger_curl=0.
        if role=='IdleAlert':bodyz+=.015;jaw=-14+2*breath
        if role in ['Walk','Run']:
            bodyz=(-.020 if role=='Run' else -.005)+(.020 if role=='Run' else .010)*math.cos(phase*math.tau*2)
            pitch=.025*math.sin(phase*math.tau*2);roll=.025*math.sin(phase*math.tau)
            jaw=-18 if role=='Run' else -24
        if role=='AttackBite':
            bodyz=curve(t,[(0,0),(.13,-.06),(.30,-.01),(.48,.015),(.85,0)])
            bodyy=curve(t,[(0,0),(.14,.06),(.30,-.12),(.43,-.12),(.85,0)])
            jaw=curve(t,[(0,-20),(.18,8),(.30,-39),(.42,-39),(.85,-26)])
            pitch=curve(t,[(0,0),(.15,.04),(.30,-.06),(.85,0)])
            finger_curl=8*math.sin(min(1,t/.85)*math.pi)
        if role=='AttackPounce':
            bodyz=curve(t,[(0,0),(.12,-.10),(.25,.03),(.48,.04),(.62,-.065),(1.1,0)])
            bodyy=curve(t,[(0,0),(.12,.04),(.24,-.04),(.5,-.05),(1.1,0)])
            pitch=curve(t,[(0,0),(.12,.10),(.26,-.08),(.56,.025),(1.1,0)])
            lift=curve(t,[(0,0),(.13,0),(.23,.14),(.43,.12),(.60,0),(1.1,0)])
            forward=curve(t,[(0,0),(.14,.04),(.32,-.20),(.52,-.16),(.72,0),(1.1,0)])
            jaw=curve(t,[(0,-20),(.23,10),(.48,10),(.56,-39),(.68,-39),(1.1,-26)])
            finger_curl=curve(t,[(0,0),(.15,12),(.32,20),(.48,0),(1.1,0)])
        if role.startswith('Hit'):
            impact=curve(t,[(0,0),(.09,1),(.55,0)])
            bodyy=.075*impact;bodyz=-.025*impact;pitch=.06*impact
            roll=(.13 if role=='HitLeft' else -.13 if role=='HitRight' else .0)*impact
            jaw=-26+12*impact
        death=ease(t/.9) if role=='Death' else 0.
        if role=='Death':bodyz=-.33*death;roll=.65*death;bodyy=.045*death;jaw=-22+16*death
        local['pelvis'].translation+=Vector((0,bodyy,bodyz))
        turn(local,'pelvis',pitch);turn(local,'pelvis',roll,(0,1,0))
        turn(local,'spine_01',-.35*pitch);turn(local,'chest',-.35*pitch)
        turn(local,'neck',-.3*pitch)
        turn(local,'jaw',math.radians(jaw))
        for side,sign in [('L',1),('R',-1)]:
            for front in [True,False]:
                name=('hand.' if front else 'hindfoot.')+side
                goal=REST[name].translation.copy()
                if role in ['Walk','Run']:
                    shift=(0 if side=='L' else .5)+(0 if front else (.25 if role=='Walk' else .56))
                    u=(phase+shift)%1.;stance=.70 if role=='Walk' else .52
                    speed=1. if role=='Walk' else 2.1
                    travel=speed*duration*stance
                    if u<stance:dy=-travel*.5+travel*(u/stance);dz=0.
                    else:
                        swing=(u-stance)/(1-stance)
                        dy=travel*.5-travel*ease(swing)
                        dz=(.09 if role=='Walk' else .17)*math.sin(math.pi*swing)**1.5
                    goal+=Vector((0,dy,dz))
                elif role=='AttackPounce':
                    goal+=Vector((sign*.025*lift/.14,forward if front else -forward*.45,lift if front else lift*.70))
                if role=='Death':goal+=Vector((sign*.10*death,.10*death,.06*death))
                if front:
                    ik(local,['upperarm.'+side,'forearm.'+side,name],goal,(sign*.40,1,0))
                    orient(local,name,REST[name].to_quaternion())
                    for i in range(1,6):
                        turn(local,'finger%d_01.%s'%(i,side),math.radians(finger_curl*.65))
                        turn(local,'finger%d_02.%s'%(i,side),math.radians(finger_curl))
                else:
                    # The frog hock retains its fitted distal segment while
                    # the knee/shin solve to the ankle's implied contact goal.
                    ankle='ankle.'+side
                    ankle_goal=goal+(REST[ankle].translation-REST[name].translation)
                    ik(local,['thigh.'+side,'calf.'+side,ankle],ankle_goal,(sign*.2,-1,0))
                    orient(local,ankle,REST[ankle].to_quaternion())
                    orient(local,name,REST[name].to_quaternion())
            # Independent dorsal supports: small follow-through only. Large
            # limb excursions do not collapse the front/back aperture.
            turn(local,'arch_front.'+side,-pitch*.20+breath*.003)
            turn(local,'arch_rear.'+side,pitch*.15-breath*.003)
        for n in NAMES:
            pb=rig.pose.bones[n];basis=LOCAL[n].inverted()@local[n]
            loc,q,s=basis.decompose();pb.rotation_mode='QUATERNION'
            if frame>1 and pb.rotation_quaternion.dot(q)<0:q.negate()
            pb.location=loc;pb.rotation_quaternion=q;pb.scale=s
            for path in ['location','rotation_quaternion','scale']:pb.keyframe_insert(path,frame=frame,group=n)
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    file=ANIM/(action.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),object_types={'ARMATURE'},bake_anim=True,
        bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.,**common)
    contact=[.30,.42] if role=='AttackBite' else [.52,.64] if role=='AttackPounce' else [-1,-1]
    report['clips'][role]={'file':str(file),'seconds':duration,'frames':count+1,'loop':loop,'contact':contact}
    print('M08_ACTION_SAVED',role,flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
mod.show_viewport=True;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'M08_Rigged_Animated_V01.blend'))
(ROOT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M08_PRODUCTION_SAVED',flush=True)
