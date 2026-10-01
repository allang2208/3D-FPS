"""Preserve source UV/topology/rig, refit support weights, author fast gallop and early collapse."""
import bpy, json, math, ast
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
OUT=Path(__file__).resolve().parent
OLD=OUT.parent/'AuthoringV1'
DELIVERY=OUT/'Delivery'; DELIVERY.mkdir(exist_ok=True)
(DELIVERY/'Animations').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OLD/'HundredEyedSlag_RigAndAnimations.blend'))
scene=bpy.context.scene;scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=next(o for o in scene.objects if o.type=='MESH');arm=rig.data
v=np.load(OLD/'source_vertices.npy').astype(np.float32)
spec=json.loads((OLD/'skeleton_spec.json').read_text())
meta=json.loads((OLD/'source_geometry.json').read_text())
byname={s['name']:s for s in spec}
skin=np.load(OLD/'skin_weights.npz');names=list(skin['bone_names'])
indices=skin['indices'].copy();values=skin['weights'].copy()
rest={b.name:b.matrix_local.copy() for b in arm.bones}
rest_inv={n:m.inverted() for n,m in rest.items()}
rest_np=np.asarray([np.asarray(rest_inv[n],dtype=np.float32) for n in names])
limbs={}
for key,pad in meta['feet_centres_m'].items():
    kind,side=key.split('.')
    up,low,palm=[kind+'_'+role+'.'+side for role in ('upper','lower','palm')]
    limbs[key]={'pad':Vector(pad),'shoulder':Vector(byname[up]['head']),
        'elbow':Vector(byname[low]['head']),'wrist':Vector(byname[palm]['head']),
        'parent':byname[up]['parent'],'bones':[up,low,palm],
        'toe_bones':[n for n in names if n.startswith(kind+'_digit_') and n.endswith('.'+side)]}
# Reuse the original analytic IK and attack poses, without executing its authoring side effects.
tree=ast.parse((OLD/'rig_and_animate.py').read_text())
helpers={'smooth','segment_distance','sstep','lerp','track','rotation','around','aim_matrix','solve_limb'}
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in helpers:
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(OLD/'rig_and_animate.py'),'exec'))
print('POLISH: refitting planted pads and joint transitions',flush=True)
deforms=[byname[n] for n in names]
weights=np.zeros((len(v),len(names)),dtype=np.float32)
rows=np.arange(len(v))[:,None];weights[rows,indices]=values
pad_array=np.asarray([list(d['pad']) for d in limbs.values()])
keys=list(limbs)
nearest=np.argmin(((v[:,None,:2]-pad_array[None,:,:2])**2).sum(axis=2),axis=1)
changed=0
for k,key in enumerate(keys):
    d=limbs[key];mask=(nearest==k)&(v[:,2]<.34)
    pts=v[mask];z=pts[:,2]
    local=np.zeros((len(pts),len(names)),dtype=np.float32)
    for n in d['bones']+d['toe_bones']:
        s=byname[n];r=s['radius']*(.9 if 'lower' in n else 1)
        field=np.exp(-.5*(segment_distance(pts,s['head'],s['tail'])/r)**2)
        if 'digit' in n:field*=.30*(1-smooth(.07,.14,z))
        elif 'palm' in n:field*=1.9*(1-smooth(.16,.28,z))
        elif 'upper' in n:field*=smooth(.13,.29,z)
        local[:,names.index(n)]=field
    local/=np.maximum(local.sum(axis=1,keepdims=True),1e-15)
    blend=1-smooth(.14,.34,z)
    # Plant surfaces follow a flat, anatomically fitted palm instead of stretching toward the torso.
    sole=1-smooth(.045,.105,z)
    rigid=np.zeros_like(local);rigid[:,names.index(d['bones'][2])]=1
    local=local*(1-sole[:,None])+rigid*sole[:,None]
    weights[mask]=weights[mask]*(1-blend[:,None])+local*blend[:,None]
    changed+=int(mask.sum())
indices=np.argpartition(weights,-4,axis=1)[:,-4:]
values=weights[rows,indices];values/=np.maximum(values.sum(axis=1,keepdims=True),1e-15)
np.savez_compressed(OUT/'skin_weights.npz',bone_names=np.asarray(names),indices=indices.astype(np.uint16),weights=values)
mesh.vertex_groups.clear()
for j,n in enumerate(names):
    group=mesh.vertex_groups.new(name=n);rr,cc=np.nonzero(indices==j)
    for vid,slot in zip(rr,cc):
        w=float(values[vid,slot])
        if w>1e-6:group.add([int(vid)],w,'REPLACE')
    if j%8==0:print('POLISH: weights '+n,flush=True)
del weights
# Fixed palm basis keeps each sole horizontal through stance; limbs retain real bone lengths.
def pose(t,role):
    fast=role=='Run';duration=20/30 if fast else 1.0
    phase=2*math.pi*t/duration
    if role=='Death':
        amount=sstep(t/.55);recoil=math.sin(math.pi*min(1,t/.18)) if t<.18 else 0
        global_body=around((-.04,0,.64),(-.055*recoil-.025*amount,-.075*amount,-.16*amount),
            rotation(.72*amount,.10*amount,-.09*amount))
    else:
        global_body=around((-.04,0,.64),(.035, .014*math.sin(phase),
            (-.10 if fast else -.080)+(.030 if fast else .012)*math.cos(phase)),
            rotation(.038*math.sin(phase),.06*math.sin(phase+.8),.015*math.sin(phase)))
    target={'root':rest['root'].copy(),'death_pivot':global_body@rest['death_pivot']}
    pelvis=global_body@around(rest['pelvis'].translation,(0,0,0),rotation(ry=.07*math.sin(phase) if role!='Death' else .09*amount))
    chest=global_body@around(rest['chest'].translation,(0,0,0),rotation(ry=-.09*math.sin(phase+.6) if role!='Death' else -.12*amount))
    for n in ('pelvis','spine','chest','carapace','front_plate','shell.L','shell.R'):
        core=pelvis if n=='pelvis' else chest if n in ('chest','front_plate') else global_body
        target[n]=core@rest[n]
    info={}
    settings={'rear.L':(0,.34,-.39),'rear.R':(.10,.32,-.37),
        'front.L':(.47,.35,.12),'front.R':(.55,.40,.34)}
    for k,d in limbs.items():
        parent=target[d['parent']]@rest_inv[d['parent']]
        sh=parent@d['shoulder'];pole=parent@d['elbow']
        pad=d['pad'].copy();footrot=rotation();curl=0.;stance=True
        if role=='Death':
            buckle=sstep((t-.10)/.35)
            # Lose the large right support first; other feet briefly catch the falling mass.
            loss=buckle*(1 if k=='front.R' else .60 if k=='rear.R' else .24)
            pad+=Vector((-.075*loss, .035*loss, .085*loss))
            footrot=rotation(ry=.4*loss,rx=.18*loss);curl=.18*loss
        else:
            offset,duty,center=settings[k]
            if not fast:offset={'rear.L':.25,'rear.R':.75,'front.L':.5,'front.R':0}[k];duty=.52
            f=(t/duration-offset)%1;stride=(2.8 if fast else 1.2)*duration*duty
            half=stride/2;pad.x=center
            if f<duty:
                pad.x+=half-stride*f/duty
            else:
                stance=False;u=(f-duty)/(1-duty);swing=(1-duty)*duration
                # Hermite swing has the same backward velocity at lift-off and touch-down.
                h00=2*u**3-3*u*u+1;h10=u**3-2*u*u+u
                h01=-2*u**3+3*u*u;h11=u**3-u*u
                velocity=-(2.8 if fast else 1.2)*swing
                pad.x+=h00*(-half)+h10*velocity+h01*half+h11*velocity
                pad.z+=(.13 if k=='front.R' else .105 if fast else .075)*math.sin(math.pi*u)**2
                footrot=rotation(ry=-.32*math.sin(2*math.pi*u)*math.sin(math.pi*u)**2)
                curl=.18*math.sin(math.pi*u)**2
        elbow,wrist=solve_limb(k,sh,pad,pole,footrot)
        achieved=wrist-footrot@(d['wrist']-d['pad'])
        up,low,palm=d['bones']
        target[up]=aim_matrix(up,sh,elbow);target[low]=aim_matrix(low,elbow,wrist)
        target[palm]=Matrix.Translation(wrist)@footrot.to_matrix().to_4x4()@rest[palm].to_3x3().to_4x4()
        for toe in d['toe_bones']:
            goal=target[palm]@rest_inv[palm]@rest[toe]
            p=goal.translation.copy()
            target[toe]=Matrix.Translation(p)@rotation(ry=curl).to_matrix().to_4x4()@goal.to_3x3().to_4x4()
        info[k]={'stance':stance,'reach_error_m':(achieved-pad).length,'pad_z_m':achieved.z-d['pad'].z}
    for n,parent in [('ash_origin','front_plate'),('attack_origin','front_palm.R')]:
        target[n]=target[parent]@rest_inv[parent]@rest[n]
    return target,info
contracts=[];contacts={}
for role,duration in [('Run',20/30),('Move',1.0),('Death',1.0)]:
    action=bpy.data.actions.new('A_HundredEyedSlag_'+role+'_V2');action.use_fake_user=True
    rig.animation_data.action=action;frames=round(duration*30)+1;contacts[role]=[]
    for frame in range(1,frames+1):
        target,info=pose((frame-1)/30,role)
        contacts[role].append({'frame':frame,'feet':info})
        for b in arm.bones:
            basis=rest_inv[b.name]@rest[b.parent.name]@target[b.parent.name].inverted()@target[b.name] if b.parent else rest_inv[b.name]@target[b.name]
            pb=rig.pose.bones[b.name];pb.rotation_mode='QUATERNION';pb.matrix_basis=basis
            for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=frame)
        if not rig.animation_data.action_slot:rig.animation_data.action_slot=action.slots[0]
    bag=action.layers[0].strips[0].channelbag(action.slots[0])
    for curve in bag.fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    contracts.append({'role':role,'action':action.name,'seconds':duration,'fps':30,'end_frame':frames,
        'reference_speed_cm_s':280 if role=='Run' else 120 if role=='Move' else 0,
        'ragdoll_handoff_s':.42 if role=='Death' else None})
    print('POLISH: action '+action.name,flush=True)
rig.animation_data.action=bpy.data.actions['A_HundredEyedSlag_Run_V2']
rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_end=21;scene.frame_set(1)
blend=OUT/'HundredEyedSlag_PolishV2.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
fbx=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True,bake_anim_step=1.0,bake_anim_simplify_factor=0.,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'SK_HundredEyedSlag_V2.fbx'),object_types={'ARMATURE','MESH'},
    bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='COPY',embed_textures=True,**fbx)
mesh.select_set(False)
for c in contracts:
    action=bpy.data.actions[c['action']];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_end=c['end_frame'];scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'Animations'/(c['action']+'.fbx')),object_types={'ARMATURE'},bake_anim=True,**fbx)
(OUT/'contact_analysis.json').write_text(json.dumps(contacts,indent=2))
(OUT/'animation_contract.json').write_text(json.dumps({'actions':contracts,'vertices':len(v),'refitted_vertices':changed,
    'topology_uv_rest_skeleton_preserved':True,'skin_max_influences':4},indent=2))
print('POLISH_EXPORT_COMPLETE',flush=True)
