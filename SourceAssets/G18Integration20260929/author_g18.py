"""G18 source assembly, native V7 skin and pistol action adaptation; no preview/tests.

Blender -b --python author_g18.py -- single|r|l
Weapon geometry/UV/normals remain from the user package. Bone rest positions
and all mechanical tracks are transported together; no source hand bind swap.
"""
import ast,json,math,sys,re
from pathlib import Path
import bpy,bmesh
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
SIDE=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'single'
OUT=O/('Single' if SIDE=='single' else 'Dual/'+SIDE);(OUT/'Animations').mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
sys.path.insert(0,str(S/'M1911RevolverInspect20260927'))
import author_support as support
def open_file(path):
    try:bpy.ops.wm.open_mainfile(filepath=str(path))
    except RuntimeError as e:
        if 'Missing library override hierarchy root data' not in str(e):raise
def load_actions(path,prefix):
    with bpy.data.libraries.load(str(S/path),link=False) as (a,b):b.actions=[n for n in a.actions if n.startswith(prefix)]
    return {re.sub(r'\.\d{3}$','',a.name.removeprefix(prefix)):a for a in b.actions if a}
def select(action,t):
    r.animation_data_create();r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    f=t*60;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in r.pose.bones}
def smooth(t):t=max(0.,min(1.,t));return t*t*(3-2*t)

open_file(O/'G18_Original.blend')
source=[];source_bones={b.name:b.head_local.copy() for b in bpy.data.objects['G18_rig'].data.bones}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    source.append({'name':ob.name,'verts':[ob.matrix_world@v.co for v in ob.data.vertices],
        'faces':[tuple(p.vertices) for p in ob.data.polygons],
        'uv':[tuple(l.uv) for l in ob.data.uv_layers.active.data],
        'normals':[ob.matrix_world.to_3x3()@n.vector for n in ob.data.corner_normals],
        'weights':[[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in ob.data.vertices]})
base='M1911ReloadTiming20260913/M1911_ReloadReady_Editable.blend' if SIDE=='single' else f'PistolDualWield20260914/NaturalAimV3/M1911/{SIDE}/M1911_{SIDE}_Dual_Editable.blend'
open_file(S/base);s=bpy.context.scene;s.render.fps=60;r=bpy.data.objects['SK_M1911_Manny'];r.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest)
parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
root=rest['WPN_root'];rootinv=root.inverted()
if SIDE=='single':
    actions={a.name.removeprefix('M1911_Contact_'):a for a in bpy.data.actions if a.name.startswith('M1911_Contact_') and 'reload' not in a.name and 'inspect' not in a.name}
    actions.update({k:bpy.data.actions['M1911_ReloadReady_'+k] for k in ('reload','reload_empty')})
    actions.update(load_actions('PistolLocomotion20260914/M1911/M1911_Locomotion_Editable.blend','M1911_Locomotion_'))
    actions.update(load_actions('M1911QuickCombat20260919/M1911_QuickCombat_Editable.blend','M1911_quickcombat'))
    if '' in actions:actions['quickcombat']=actions.pop('')
    actions.update(load_actions('M1911RevolverInspect20260927/M1911_RevolverInspect_Editable.blend','M1911_Revolver_'))
else:
    prefix=f'Dual_M1911_{SIDE}_'
    actions={a.name.removeprefix(prefix):a for a in bpy.data.actions if a.name.startswith(prefix)}
    actions.update({k:v for k,v in load_actions(f'PistolDualWield20260914/SprintSmoothV5/M1911/{SIDE}/M1911_{SIDE}_Dual_Editable.blend',prefix).items() if k.startswith('sprint')})
    actions.update({k:v for k,v in load_actions(f'DualPistolQuickCombat20260920/SpinRecoveryV5/M1911/{SIDE}/M1911_{SIDE}_QuickCombat_Editable.blend',prefix).items() if k.startswith('quickcombat')})
# The helper preserves the exact native arm binding, including the left-only rig.
skin_source=support.install_bare_arms(r,'M1911'+('' if SIDE=='single' else '_'+SIDE))
hands=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.get('inspect_skin_source')]
for ob in list(bpy.context.scene.objects):
    if ob!=r and ob not in hands:bpy.data.objects.remove(ob,do_unlink=True)
for ob in hands:
    ob.hide_set(False);ob.hide_render=False
    for m in ob.data.materials:
        # Preview/world-copy filters already hide Manny-labelled skin sections.
        if m and not m.name.startswith('M_G18_Manny_'):m.name='M_G18_Manny_'+m.name

# Registration uses the grip/trigger junction. Preserve the 204.9 mm source
# slide and its 29.8 mm width; no uniform scale to another pistol's bounds.
alignment=Matrix.Translation((0,-.030,-.031))
mapping={'G18_handle':'WPN_root','G18_slide':'WPN_Slide','G18_selectfire':'WPN_Safety',
    'G18_barrel':'WPN_Barrel','G18_trigger':'WPN_Trigger','G18_mag':'WPN_SOCKET_Magazine','G18_bullet':'WPN_Bullet'}
newrest={n:m.copy() for n,m in rest.items()}
for old,new in mapping.items():
    if new=='WPN_root':continue
    newrest[new].translation=root@(alignment@source_bones[old])
# Geometric markers in G18 source metres: bore exit, port and physical sights.
markers={'WPN_SOCKET_Muzzle':(0,-.102,.059612),'WPN_SOCKET_Eject':(-.012,.008,.0596),
         'WPN_RearSight':(0,.079,.0712),'WPN_FrontSight':(0,-.087,.0712)}
for n,p in markers.items():newrest[n].translation=root@(alignment@Vector(p))
newparent=dict(parent);newparent['WPN_Safety']='WPN_Slide';newparent['WPN_Bullet']='WPN_SOCKET_Magazine'
newlr={n:newrest[newparent[n]].inverted()@m if newparent[n] else m for n,m in newrest.items()}
gun=[];mat=bpy.data.materials.new('M_G18_SourcePBR')
for src in source:
    mesh=bpy.data.meshes.new(src['name']+'_Geometry');mesh.from_pydata([root@alignment@v for v in src['verts']],[],src['faces']);mesh.update()
    for p in mesh.polygons:p.use_smooth=True
    mesh.normals_split_custom_set([(root@alignment).to_3x3()@n for n in src['normals']])
    uv=mesh.uv_layers.new(name='UVMap')
    for l,co in zip(uv.data,src['uv']):l.uv=co
    ob=bpy.data.objects.new('G18_'+src['name'],mesh);s.collection.objects.link(ob);ob.parent=r;ob.matrix_basis=Matrix.Identity(4)
    part_mat=mat
    if src['name']=='G18_mag':part_mat=bpy.data.materials.get('M_G18_Magazine') or bpy.data.materials.new('M_G18_Magazine')
    ob.data.materials.append(part_mat);groups={n:ob.vertex_groups.new(name=n) for n in set(mapping.values())}
    for i,ww in enumerate(src['weights']):
        for n,w in ww:groups[mapping[n]].add([i],w,'REPLACE')
    mod=ob.modifiers.new('G18_MechanicalSkin','ARMATURE');mod.object=r;gun.append(ob)

# Source action pose is sampled on its original rig; only the resulting new
# tracks use the relocated G18 mechanical reference. Arm rest matrices stay put.
idle=select(actions['idle'],0)
oldmag=(rootinv@rest['WPN_SOCKET_Magazine']).translation
newmag=(rootinv@newrest['WPN_SOCKET_Magazine']).translation
mag_delta=newmag-oldmag
held={side:idle['WPN_root'].inverted()@idle['hand_'+side] for side in ('r','l')}
# Author a bounded whole-hand fit on the actual G18 surface. Native finger
# curvature is retained; arm IK carries the wrist, elbow and twist chain.
gv=[];gf=[]
for src in source:
    off=len(gv);gv.extend([alignment@v for v in src['verts']]);gf.extend([tuple(off+i for i in f) for f in src['faces']])
surface=BVHTree.FromPolygons(gv,gf,all_triangles=True)
fit={};fit_record={}
for side in (('r','l') if SIDE=='single' else (SIDE,)):
    candidates=[]
    for ob in hands:
        for v in ob.data.vertices:
            weights=[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups]
            dominant=max(weights,key=lambda p:p[1])[0] if weights else ''
            if not dominant.endswith('_'+side) or not dominant.startswith(('hand','thumb','index','middle','ring','pinky')):continue
            pt=sum((idle[n]@rest[n].inverted()@v.co*w for n,w in weights if n in rest),Vector())
            candidates.append((idle['WPN_root'].inverted()@pt,dominant.split('_')[0]))
    step=max(1,len(candidates)//240);points=candidates[::step]
    def loss(delta):
        score=0.;contacts={}
        for p,digit in points:
            pt=p+delta;near,normal,_,distance=surface.find_nearest(pt)
            if near is None:continue
            signed=distance if (pt-near).dot(normal)>=0 else -distance
            depth=max(0.,.00045-signed);score+=60*depth*depth/max(1,len(points))
            if digit!='index' or side=='l':contacts.setdefault(digit,[]).append(abs(distance-.0007))
        for distances in contacts.values():
            distances.sort();use=distances[:max(2,len(distances)//6)];score+=sum(d*d for d in use)/len(use)
        return score+.65*delta.length_squared
    delta=Vector();value=loss(delta)
    for step in (.004,.0015,.0005):
        for _ in range(5):
            changed=False
            for axis in range(3):
                for sign in (-1,1):
                    candidate=delta.copy();candidate[axis]+=step*sign
                    if max(abs(v) for v in candidate)>.012:continue
                    candidate_loss=loss(candidate)
                    if candidate_loss<value:delta,value,changed=candidate,candidate_loss,True
            if not changed:break
    fit[side]=delta;fit_record[side]={'translation_m':list(delta),'source':'native V7 palm and fingers; bounded G18 surface authoring','objective':value}
    print('G18_GRIP_AUTHORED',SIDE,side,list(delta),flush=True)
# Existing full-chain solver carries elbow and twist bones with contact changes.
tree=ast.parse((S/'M1911Contact20260913/author_contacts.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve_arm'],type_ignores=[]),'<G18 full arm contact>','exec'))
def shift_hand(p,old,side,delta):
    H=old['hand_'+side].copy();H.translation+=old['WPN_root'].to_3x3()@delta
    D=H@old['hand_'+side].inverted()
    for n in names:
        if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n]=D@old[n]
    solve_arm(p,old,side,H)
records={};made={}
for kind,source_action in actions.items():
    if '.00' in kind:continue
    is_fire='fire' in kind and 'quick' not in kind
    source_duration=float(source_action.frame_range[1])/60
    duration=.15 if is_fire else (2.25 if kind=='reload_empty' else 1.75) if SIDE!='single' and kind in ('reload','reload_empty') else source_duration
    frames=[i*.5 for i in range(round(duration*120)+1)];rows=[];previous={}
    for f in frames:
        t=f/60
        sample_time=t*source_duration/duration if SIDE!='single' and kind in ('reload','reload_empty') else t
        old=select(actions['aim' if kind.startswith('aim') else 'idle'],0) if is_fire else select(source_action,sample_time)
        p={n:m.copy() for n,m in old.items()};G=old['WPN_root']
        for n in names:
            if n.startswith('WPN_') and n!='WPN_root':p[n]=old[n]@rest[n].inverted()@newrest[n]
        # Safety selector stays on the moving slide; G18 has no exposed hammer.
        p['WPN_Safety']=p['WPN_Slide']@newrest['WPN_Slide'].inverted()@newrest['WPN_Safety']
        p['WPN_Bullet']=p['WPN_SOCKET_Magazine']@newrest['WPN_SOCKET_Magazine'].inverted()@newrest['WPN_Bullet']
        for n in markers:
            bone='WPN_Barrel' if n=='WPN_SOCKET_Muzzle' else 'WPN_Slide'
            p[n]=p[bone]@newrest[bone].inverted()@newrest[n]
        if is_fire:
            peak=smooth(t/.012)
            travel=peak if kind.endswith('_last') else peak*(1-smooth((t-.012)/.031))
            for n in ('WPN_Slide','WPN_Safety','WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Eject'):
                p[n]=G@rootinv@newrest[n];p[n].translation+=G.to_3x3()@Vector((0,.033*travel,0))
            local=rootinv@newrest['WPN_Barrel'];p['WPN_Barrel']=G@Matrix.Translation((0,.004*travel,-.0015*travel))@local@Matrix.Rotation(-.035*travel,4,'X')
            p['WPN_SOCKET_Muzzle']=p['WPN_Barrel']@newrest['WPN_Barrel'].inverted()@newrest['WPN_SOCKET_Muzzle']
            p['WPN_Trigger']=G@rootinv@newrest['WPN_Trigger']@Matrix.Rotation(.065*peak,4,'X')
        else:
            # The reference slide stroke is longer; rescale only its relative
            # translation, leaving the author gun/hand motion intact.
            slide_local=G.inverted()@p['WPN_Slide'];bind=rootinv@newrest['WPN_Slide']
            travel=slide_local.translation-bind.translation
            offset=-travel*.18
            for n in ('WPN_Slide','WPN_Safety','WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Eject'):p[n].translation+=G.to_3x3()@offset
        for side,delta in fit.items():
            distance=((G.inverted()@old['hand_'+side]).translation-held[side].translation).length
            weight=1. if SIDE!='single' or side=='r' else 1-smooth((distance-.018)/.050)
            if SIDE=='single' and side=='l' and kind.startswith('reload'):
                weight*=1-smooth((t-.04)/.1)+smooth((t-(1.85 if kind=='reload_empty' else 1.25))/.25)
            if weight:shift_hand(p,p.copy(),side,delta*weight)
        if SIDE=='single' and kind.startswith('reload'):
            w=smooth((t-.08)/.14)*(1-smooth((t-1.13)/.17))
            if w:shift_hand(p,old,'l',mag_delta*w)
        row={}
        for n in names:
            loc,q,scale=(newlr[n].inverted()@(p[newparent[n]].inverted()@p[n] if newparent[n] else p[n])).decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        rows.append(row)
    support.DURATION=duration
    stem='G18' if SIDE=='single' else 'Dual_G18_'+SIDE
    a=support.bake_action(r,s,'G18Auth_'+SIDE+'_'+kind,rows,frames);made[kind]=a
    records[kind]={'duration':duration,'donor_action':source_action.name,'sample_rate':120,'file':'Animations/A_'+stem+'_'+kind+'.fbx'}
    print('G18_ACTION_AUTHORED',SIDE,kind,duration,flush=True)

r.animation_data_clear()
bpy.context.view_layer.objects.active=r;bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n in names:
    b=r.data.edit_bones[n];length=b.length;b.parent=r.data.edit_bones[newparent[n]] if newparent[n] else None;b.use_connect=False;b.matrix=newrest[n];b.length=length
bpy.ops.object.mode_set(mode='OBJECT')
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
r.name='SK_G18_Manny' if SIDE=='single' else 'SK_Dual_G18_'+SIDE
for ob in [r]+hands+gun:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(OUT/(r.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False)
for kind,a in made.items():
    r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.frame_start=0;s.frame_end=round(records[kind]['duration']*60);s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/records[kind]['file']),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
r.animation_data.action=made['idle'];r.animation_data.action_slot=made['idle'].slots[0];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('G18_'+SIDE+'_Editable.blend')))
(OUT/'authoring.json').write_text(json.dumps({'source':str(O/'Original/G18/G18/FBX/G18_full.fbx'),'skin':skin_source,'alignment':[list(x) for x in alignment],'markers_source_m':markers,'grip_authoring':fit_record,'magazine_contact_delta_m':list(mag_delta),'clips':records,'mesh':r.name+'.fbx','testing':'Not performed'},indent=2))
print('G18_AUTHORING_SAVED',SIDE,flush=True)
