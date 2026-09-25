"""Dedicated Bow V7 rig, constrained first-person Sparrow adaptation, editable actions.

Run in Blender background. No render/playback. Skin is the accepted V7 surface;
new rig has unit-scale anatomical bones and dedicated grip/nock contact markers.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

P=Path(__file__).parent
PROJECT=P.parents[2]
OUT=P/'Export'; OUT.mkdir(exist_ok=True)
data=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json').read_text())
native=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources/M4.json').read_text())
anatomy=json.loads((PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json').read_text())['anatomy']
donor=json.loads((P.parent/'ArmsV2/sparrow_motion.json').read_text())
surface=json.loads((P.parent/'ArmsV2/bow_surface.json').read_text())
FPS=120
DURATIONS={'Idle':2.,'Ready':2.,'Equip':.45,'Nock':.68,'Draw':1.4,'Hold':2.,'Release':.64,'Run':.8}
R=Matrix.Rotation(math.pi/2,3,'Z')
S=Matrix.Diagonal((1,-1,1))
def unit(v): return Vector(v).normalized()
def smooth(x):
    x=max(0.,min(1.,x)); return x*x*(3-2*x)
def mat(p,r=None):
    a=(r or Matrix.Identity(3)).to_4x4();a.translation=Vector(p);return a
def limb_frame(axis,across):
    x=axis.normalized();y=across-x*across.dot(x);y.normalize()
    return Matrix((x,y,x.cross(y))).transposed()
digits={side:{d['bone']:d for d in anatomy[side]['digits']} for side in ('l','r')}
def world_to_blender(m):return mat(S@m.translation*.01,S@m.to_3x3()@S)
names_by_index={v['index']:n for n,v in native['bones'].items()}
keep={n for w in data['weights'] for n in w}
for n in list(keep):
    while native['bones'][n]['parent'] in names_by_index:
        n=names_by_index[native['bones'][n]['parent']];keep.add(n)
order=[n for n in native['bones'] if n in keep]
parent={n:names_by_index.get(native['bones'][n]['parent']) for n in order}
rest={}
for n in order:
    b=native['bones'][n];a=Matrix(b['axes']).transposed()
    for i in range(3):a.col[i]=a.col[i].normalized()
    rest[n]=mat(R@Vector(b['position']),R@a)
# A new, unit-scale root is the native basis for this weapon. No source gun root.
root='bow_root'
for n in order:
    if parent[n] not in keep:parent[n]=root
order=[root]+order;parent[root]=None;rest[root]=Matrix.Identity(4)
for n in ('bow_grip','bow_nock'):
    order.append(n);parent[n]='hand_l' if n=='bow_grip' else 'hand_r';rest[n]=Matrix.Identity(4)
local={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in order}

# Actual donor hand separation, sampled until the draw settles at 2.333 seconds.
draw=donor['clips']['RMB_Drawback']['frames']
dist=[(Vector(f['hand_l']['p'])-Vector(f['hand_r']['p'])).length for f in draw]
curve=[max(0.,min(1.,(dist[round(i*70/16)]-dist[0])/(dist[70]-dist[0]))) for i in range(17)]
curve[0]=0.;curve[-1]=1.
def progress(t):
    x=max(0.,min(1.,t))*16;i=min(15,int(x));return curve[i]*(1-x+i)+curve[i+1]*(x-i)
def sample_reference(t):return draw[min(70,max(0,round(t*70)))]
def bow_frame(q):
    return mat(Vector((57.,-15.,-13.)).lerp(Vector((60.,-10.,-8.)),q),Matrix.Rotation(math.radians(-12+7*q),3,'X'))
BRACE=Vector((-21.46,-.935,1.5));ANCHOR=Vector((-52.5,8.,3.))

def hand_basis(side,forward,dorsal):
    oldf=R@Vector(anatomy[side]['forward']);oldd=R@Vector(anatomy[side]['dorsal'])
    oldd=(oldd-oldf*oldf.dot(oldd)).normalized();olda=oldf.cross(oldd)
    f=unit(forward);d=(Vector(dorsal)-f*f.dot(Vector(dorsal))).normalized();a=f.cross(d)
    return Matrix((f,d,a)).transposed()@Matrix((oldf,oldd,olda))

def pose(role,t):
    phase=t/DURATIONS[role]
    q=progress(phase) if role=='Draw' else 1. if role=='Hold' else 0.
    bow=bow_frame(q)
    nock=bow@BRACE.lerp(ANCHOR,q)
    hook=1.;right=nock.copy();release=0.
    if role=='Idle':
        right=bow@BRACE+Vector((-2,8,-5));hook=.18
    if role=='Nock':
        keys=[(0.,bow@BRACE+Vector((-2,8,-5))),(.34,Vector((8,31,-42))),
              (.58,Vector((22,18,-26))),(.82,bow@BRACE+Vector((1,3,-3))),(1.,bow@BRACE)]
        for (a,p),(b,v) in zip(keys,keys[1:]):
            if a<=phase<=b:right=p.lerp(v,smooth((phase-a)/(b-a)));break
        hook=.2+.8*smooth((phase-.58)/.32)
    if role=='Release':
        release=smooth(t/.075)
        settle=smooth((t-.16)/(.64-.16))
        bow=bow_frame(1.).lerp(bow_frame(0.),settle)
        right=(bow_frame(1.)@ANCHOR+Vector((-4*release,3*release,1*release))).lerp(
            bow_frame(0.)@BRACE+Vector((-2,8,-5)),settle)
        hook=.15+.85*(1-release)
        nock=bow@ANCHOR.lerp(BRACE,release)
    if role=='Equip':
        lift=1-smooth(phase)
        offset=Vector((-10,6,-30))*lift
        bow.translation+=offset;right+=offset;nock+=offset
    if role=='Run':
        off=Vector((-8,6,-16));off+=Vector((math.sin(t*2*math.pi/.8)*.9,0,math.cos(t*4*math.pi/.8)*.8))
        bow.translation+=off;right+=off;nock+=off
        right+=Vector((-2,8,-5));hook=.18
    if role in ('Idle','Ready'):
        # Low amplitude reference idle breathing, with identical contact transport.
        frames=donor['clips']['idle']['frames'];f=frames[round(t*30)%len(frames)];f0=frames[0]
        change=Vector(f['hand_l']['p'])-Vector(f0['hand_l']['p'])
        off=Vector((change.y,-change.x,change.z))*.20*math.sin(math.pi*phase)**2
        bow.translation+=off;right+=off;nock+=off
    left_delta=hand_basis('l',bow.to_3x3()@Vector((0,0,1)),bow.to_3x3()@Vector((-1,0,0)))
    right_delta=hand_basis('r',(1,0,.06),(0,1,0))
    # Palm/phalange contact offsets, not the wrist origin, touch riser and string.
    targets={'l':bow.translation-bow.to_3x3()@Vector((1.6,0,6.5)),
             'r':right-Vector((7.,-1.0,.4))}
    hands={'l':left_delta,'r':right_delta}
    world={}
    ref=sample_reference(phase if role=='Draw' else 1.)
    for n in order:
        world[n]=(world[parent[n]]@local[n]) if parent[n] else local[n].copy()
    for side in ('l','r'):
        clav='clavicle_'+side;up='upperarm_'+side;low='lowerarm_'+side;hand='hand_'+side
        world[clav].translation+=Vector((8,0,0))
        shoulder=(world[clav]@local[up]).translation
        wrist=targets[side]
        l1=(rest[low].translation-rest[up].translation).length
        l2=(rest[hand].translation-rest[low].translation).length
        axis=(wrist-shoulder).normalized();distance=min((wrist-shoulder).length,l1+l2-.12)
        # Sparrow's elbow travel supplies the changing pole; hand contacts and
        # V7 bone lengths remain authoritative for the first-person adaptation.
        elbow=Vector(ref['lowerarm_'+side]['p'])-Vector(ref['head']['p'])
        pole=Vector((elbow.y,-elbow.x,elbow.z))
        pole.y=(-1 if side=='l' else 1)*max(22,abs(pole.y))
        pole.z=min(-8,pole.z)
        bend=(pole-shoulder)-axis*(pole-shoulder).dot(axis)
        bend.normalize()
        a=(l1*l1-l2*l2+distance*distance)/(2*distance)
        h=math.sqrt(max(0.,l1*l1-a*a));elbow=shoulder+axis*a+bend*h
        wrist=shoulder+axis*distance
        ru=rest[low].translation-rest[up].translation
        rl=rest[hand].translation-rest[low].translation
        ud=(elbow-shoulder).normalized();ld=(wrist-elbow).normalized()
        ref_across=R@Vector(anatomy[side]['across'])
        # Palm hinge determines roll independently of wrist extension.
        dl=limb_frame(ld,hands[side]@ref_across)@limb_frame(rl,ref_across).transposed()
        du=limb_frame(ud,ud.cross(ld))@limb_frame(ru,ru.cross(rl)).transposed()
        world[up]=mat(shoulder,du@rest[up].to_3x3())
        world[low]=mat(elbow,dl@rest[low].to_3x3())
        world[hand]=mat(wrist,hands[side]@rest[hand].to_3x3())
        descendants=set((up,low,hand))
        for n in order:
            if parent[n] in descendants and n not in (low,hand):
                descendants.add(n);world[n]=world[parent[n]]@local[n]
                # Twist/support bones keep their complete rest-local pose.
                # Their weighted skin follows the same solved rigid segment.
                digit=n.split('_')[0]
                if digit in ('index','middle','ring','pinky','thumb') and '_metacarpal_' not in n:
                    seg=int(n.split('_')[1])-1
                    curl=([24,38,25] if side=='l' else [4,60,30])[seg]
                    if digit=='thumb':curl=[8,12,8][seg]
                    if side=='r':curl*=hook*(.7 if digit=='pinky' else 1.)
                    parent_delta=world[parent[n]].to_3x3()@rest[parent[n]].to_3x3().transposed()
                    direction=parent_delta@(R@Vector(digits[side][n]['across']))
                    # Across x forward = -dorsal, the palm-side curl direction.
                    world[n]=mat(world[n].translation,Matrix.Rotation(math.radians(curl),3,direction)@world[n].to_3x3())
    world['bow_grip']=bow
    world['bow_nock']=mat(right if role=='Nock' else nock)
    return world

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.render.fps=FPS
arm=bpy.data.armatures.new('Bow_V7_Native')
rig=bpy.data.objects.new('Bow_V7_Native',arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for n in order:
    b=arm.edit_bones.new(n)
    # A zero-length edit bone cannot retain a requested orientation. Establish
    # its direction BEFORE assigning the native reference matrix.
    b.head=(0,0,0);b.tail=(0,.025,0)
    b.matrix=world_to_blender(rest[n]);b.length=.025
    if parent[n]:b.parent=arm.edit_bones[parent[n]]
bpy.ops.object.mode_set(mode='OBJECT')
mesh=bpy.data.meshes.new('V7_BareBowArms')
mesh.from_pydata([S@(R@Vector(p))*.01 for p in data['positions']],[],data['triangles']);mesh.update()
obj=bpy.data.objects.new('SK_Bow_BareArmsV7',mesh);bpy.context.collection.objects.link(obj)
obj.parent=rig;mod=obj.modifiers.new('BowNativeBinding','ARMATURE');mod.object=rig
for n in {n for w in data['weights'] for n in w}:obj.vertex_groups.new(name=n)
for i,w in enumerate(data['weights']):
    for n,v in w.items():obj.vertex_groups[n].add([i],v,'REPLACE')
for label in ('BareUpperArms','BareLowerArms','BareHandsOriginalGrip'):
    m=bpy.data.materials.new(label);m.diffuse_color=(.372,.232,.182,1);mesh.materials.append(m)
uvs=[mesh.uv_layers.new(name=n) for n in ('Anatomy','CanonicalXY','CanonicalZNormalX','CanonicalNormalYZ')];normals=[]
for p in mesh.polygons:
    ti=p.index;p.material_index=data['triangle_materials'][ti];p.use_smooth=True
    for j,loop in enumerate(p.loop_indices):
        vi=mesh.loops[loop].vertex_index;c=data['canonical_positions'][vi];n=data['canonical_normals'][ti][j]
        pairs=[data['uv'][ti][j],c[:2],(c[2],n[0]),n[1:]]
        for layer,pair in zip(uvs,pairs):layer.data[loop].uv=(pair[0],1-pair[1])
        normals.append(S@(R@Vector(data['normals'][ti][j])))
mesh.normals_split_custom_set(normals)
def export(name,animated=False,include_mesh=False):
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    if not animated or include_mesh:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
        object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=animated,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0.,mesh_smooth_type='FACE',use_tspace=True)
# FBX bind poses exported before the dependency graph was evaluated had
# different bone axes from the animation tracks. Author an explicit rest take,
# evaluate it, and import its frame zero as the skeleton/mesh reference pose.
rig.animation_data_create()
bind_action=bpy.data.actions.new('Bow_BindPose');rig.animation_data.action=bind_action
scene.frame_start=0;scene.frame_end=1
for bone in rig.pose.bones:
    bone.rotation_mode='QUATERNION';bone.matrix_basis=Matrix.Identity(4)
    for f in (0,1):
        bone.keyframe_insert('location',frame=f);bone.keyframe_insert('rotation_quaternion',frame=f);bone.keyframe_insert('scale',frame=f)
scene.frame_set(0);bpy.context.view_layer.update()
export('SK_Bow_BareArmsV7',True,True)
for role,seconds in DURATIONS.items():
    rig.animation_data_create();action=bpy.data.actions.new('A_Bow_'+role);rig.animation_data.action=action
    scene.frame_start=0;scene.frame_end=round(seconds*FPS)
    previous={}
    for frame in range(scene.frame_end+1):
        t=frame/FPS;world=pose(role,t)
        for n in order:
            b=rig.pose.bones[n]
            relative=world_to_blender(world[parent[n]]).inverted()@world_to_blender(world[n]) if parent[n] else world_to_blender(world[n])
            restlocal=arm.bones[parent[n]].matrix_local.inverted()@arm.bones[n].matrix_local if parent[n] else arm.bones[n].matrix_local
            b.rotation_mode='QUATERNION'
            b.matrix_basis=restlocal.inverted()@relative
            if frame and b.rotation_quaternion.dot(previous[n])<0:b.rotation_quaternion.negate()
            previous[n]=b.rotation_quaternion.copy()
            b.keyframe_insert('location',frame=frame);b.keyframe_insert('rotation_quaternion',frame=frame);b.keyframe_insert('scale',frame=frame)
    action.use_fake_user=True
    scene.frame_set(0);bpy.context.view_layer.update()
    export('A_Bow_'+role,True)
    print('BOW_ACTION_EXPORTED',role,seconds,flush=True)
rig.animation_data.action=bpy.data.actions['A_Bow_Idle'];scene.frame_start=0;scene.frame_end=240;scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_BareArmsV7_Actions.blend'))
(P/'authoring.json').write_text(json.dumps({'fps':FPS,'durations':DURATIONS,'draw_curve':curve,
    'reference':'Paragon Sparrow source joint trajectories, 0..2.333 seconds of RMB_Drawback',
    'skin':'V7 surface and weights; explicit evaluated bind take; full-segment helpers; local digit hinge axes',
    'brace_nock_cm':list(BRACE),'draw_anchor_cm':list(ANCHOR),
    'runtime_tested':False},indent=2),encoding='utf-8')
