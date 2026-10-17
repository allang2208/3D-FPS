"""Adapt the shipped Super90 ShoulderReturnR3 sprint to M870 contacts.

Only enter/loop/exit are exported. The current M870 loading clips are inputs
in the editable scene and are never reimported by this batch.
"""
import ast,gzip,json,math,hashlib
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion

O=Path(__file__).parent;S=O.parent;INPUT=O/'Inputs';INPUT.mkdir(exist_ok=True)
X=O/'Exports/Animations';X.mkdir(parents=True,exist_ok=True)
REFERENCE=S/'Super90TacticalSprint20261007'
cache=INPUT/'super90_reference.json.gz'
if not cache.exists():
    source_script=(REFERENCE/'author_sprint.py').read_text(encoding='utf-8')
    (INPUT/'super90_author_sprint.py').write_text(source_script,encoding='utf-8')
    bpy.ops.wm.open_mainfile(filepath=str(REFERENCE/'Super90_TacticalSprint_Editable.blend'),use_scripts=False)
    donor=bpy.data.objects['SK_Super90'];ds=bpy.context.scene
    data={'source':str(REFERENCE/'Super90_TacticalSprint_Editable.blend'),
          'revision':'ShoulderReturnR3-20261007','sample_rate':120,
          'source_script_sha256':hashlib.sha256(source_script.encode()).hexdigest(),'clips':{}}
    for role,duration in (('sprint_enter',.30),('sprint_loop',.60),('sprint_exit',.30)):
        name='A_Super90_'+role;action=bpy.data.actions[name]
        donor.animation_data.action=action;donor.animation_data.action_slot=action.slots[0]
        rows=[]
        for j in range(round(duration*120)+1):
            ds.frame_set(j//2,subframe=(j%2)*.5)
            rows.append({b.name:[list(v) for v in b.matrix] for b in donor.pose.bones})
        data['clips'][role]={'action':name,'duration':duration,'rows':rows,
            'asset':'/Game/Weapons/Super90/TacticalSprint20261007/Animations/'+name}
    with gzip.open(cache,'wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))
with gzip.open(cache,'rt',encoding='utf-8') as f:reference=json.load(f)
source_rows={k:[{n:Matrix(m) for n,m in row.items()} for row in v['rows']] for k,v in reference['clips'].items()}
source_idle=source_rows['sprint_enter'][0]

bpy.ops.wm.open_mainfile(filepath=str(S/'M870ReloadContact20261016/M870_ReloadContact_Editable.blend'),use_scripts=False)
rig=bpy.data.objects['SK_Super90'];scene=bpy.context.scene;scene.render.fps=60;scene.render.fps_base=1.0
idle_name=json.loads((S/'M870AKMArmSupport20261016/authoring.json').read_text())['clips']['idle']['action']
rig.animation_data.action=bpy.data.actions[idle_name];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
names=list(rest);I=Matrix.Identity(4)
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
idles={'base':idle}

# Reuse the production donor's release and native-chain solver, with this
# gun's starting contacts. This is the initial clearance phase, before the
# arm can follow the donor's complete withdrawn shoulder/elbow/wrist chain.
tree=ast.parse((INPUT/'super90_author_sprint.py').read_text(encoding='utf-8'))
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('smooth','segment_frame','arm','pose')]
exec(compile(ast.Module(body=functions,type_ignores=[]),str(INPUT/'super90_author_sprint.py'),'exec'))
up=Vector((0,0,1));barrel=(idle['WPN_FrontSight'].translation-idle['WPN_RearSight'].translation).normalized()
forward=Vector((barrel.x,barrel.y,0)).normalized();right=forward.cross(up).normalized()
upright=forward*math.cos(math.radians(76))+up*math.sin(math.radians(76))
raise_q=Quaternion(up,math.radians(-7))@Quaternion(upright,math.radians(-8))@barrel.rotation_difference(upright)
forearm_rest=rest['hand_l'].translation-rest['lowerarm_l'].translation
skin_stations={n:max(0.,min(1.,(rest[n].translation-rest['lowerarm_l'].translation).dot(forearm_rest)/forearm_rest.length_squared))
    for n in ('lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l')}

def gun_frame(row):
    y=(row['WPN_FrontSight'].translation-row['WPN_RearSight'].translation).normalized()
    x=y.cross(up).normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_4x4()

# Framing is registered at the carrying hand, not at an unrelated model
# origin. Keep the traditional-stock M870 right-hand grip throughout.
alignment=Matrix.Translation(idle['hand_r'].translation)@gun_frame(idle)@gun_frame(source_idle).inverted()@Matrix.Translation(-source_idle['hand_r'].translation)
alignment_inverse=alignment.inverted();source_gun_inverse=source_idle['WPN_root'].inverted()
def under(n,root):
    while n:
        if n==root:return True
        n=parents.get(n)
    return False
left=[n for n in names if under(n,'clavicle_l')]

def adapt(source,progress,phase):
    p=pose(progress,phase)
    carry=alignment@source['WPN_root']@source_gun_inverse@alignment_inverse
    for n in names:
        if n.startswith('WPN_'):p[n]=carry@idle[n]
    arm(p,idle,'r',carry@idle['hand_r'])
    weight=smooth(.22,.78,progress)
    own={n:m.copy() for n,m in p.items()}
    mapped={n:alignment@m for n,m in source.items()}
    for n in left:
        parent=parents[n]
        a=own[parent].inverted()@own[n]
        b=(mapped[parent] if parent in left else own[parent]).inverted()@mapped[n]
        # Child offsets retain native segment lengths. Only the shoulder
        # anchor translates to the actual reference's withdrawn body position.
        v=a.translation.lerp(b.translation,weight) if n=='clavicle_l' else a.translation
        q=a.to_quaternion().slerp(b.to_quaternion(),weight)
        p[n]=p[parent]@Matrix.LocRotScale(v,q,a.to_scale())
    return p

def bake(role,rows):
    action=bpy.data.actions.new('A_M870_'+role);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    for b in rig.pose.bones:
        b.rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
    values={n:[] for n in names};previous={}
    for row in rows:
        for n in names:
            local=row[parents[n]].inverted()@row[n] if parents[n] else row[n]
            v,q,sc=(local_rest[n].inverted()@local).decompose()
            if n in previous and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy();values[n].append((v,q,sc))
    for n in names:
        for prop,k,count in (('location',0,3),('rotation_quaternion',1,4),('scale',2,3)):
            for axis in range(count):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(rows))
                curve.keyframe_points.foreach_set('co',[v for i,row in enumerate(values[n]) for v in (i*.5,row[k][axis])])
                for key in curve.keyframe_points:key.interpolation='LINEAR'
                curve.update()
    scene.frame_start=0;scene.frame_end=(len(rows)-1)//2;rig.animation_data.action_slot=action.slots[0];scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    file=X/('A_M870_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    return {'file':str(file),'action':action.name,'duration':(len(rows)-1)/120,'samples':len(rows)}

authored={}
for role,sources in source_rows.items():
    rows=[];last=len(sources)-1
    for j,source in enumerate(sources):
        t=j/last;progress=1. if role=='sprint_loop' else 1-t if role=='sprint_exit' else t
        rows.append(adapt(source,progress,2*math.pi*t if role=='sprint_loop' else None))
    if role=='sprint_enter':rows[0]={n:m.copy() for n,m in idle.items()}
    if role=='sprint_exit':rows[-1]={n:m.copy() for n,m in idle.items()}
    if role=='sprint_loop':rows[-1]={n:m.copy() for n,m in rows[0].items()}
    authored[role]=bake(role,rows);print('M870_SUPER90_SPRINT_AUTHORED',role,len(rows),flush=True)
entry=bpy.data.actions[authored['sprint_enter']['action']]
rig.animation_data.action=entry;rig.animation_data.action_slot=entry.slots[0];scene.frame_set(0);scene.frame_end=18
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_Super90Sprint_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':authored,'sample_rate':120,
    'reference_revision':reference['revision'],'reference_source':reference['source'],
    'reference_assets':{k:v['asset'] for k,v in reference['clips'].items()},'reference_script_sha256':reference['source_script_sha256'],
    'target_idle_action':idle_name,'alignment':[list(v) for v in alignment],
    'method':'Exact Super90 gun trajectory around M870 carrying-hand contact; native reference release then full shoulder/elbow/wrist chain after fore-end clearance.',
    'scope':'Sprint enter/loop/exit only. Current reload, idle, aiming, shot and mechanical tracks are not imported.',
    'runtime_tested':False,'visual_tested':False},indent=2),encoding='utf-8')
