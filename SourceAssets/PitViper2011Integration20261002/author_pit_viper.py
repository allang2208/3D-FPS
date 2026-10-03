"""PitViper2011 source assembly, native V7 skin and pistol action adaptation; no preview/tests.

Blender -b --python author_pit_viper.py -- single|r|l
Weapon geometry/UV/normals remain from the user package. Bone rest positions
and all mechanical tracks are transported together; no source hand bind swap.
"""
import ast,json,math,sys,re
from pathlib import Path
import bpy,bmesh
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(O))
import fire_motion
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

raw=json.loads((O/'canonical_parts.json').read_text(encoding='utf8'))
source=[];source_bones={};source_transforms={}
for part in raw:
    identity=part['identity']
    source_transforms[identity]=Matrix(part['owner_transform'])
    if identity.startswith('2011pv') or identity.startswith('919 2011 15rnd mag empty'):
        p=dict(part);p['name']=part['object']
        p['verts']=[Vector(v) for v in part['verts']]
        p['normals']=[Vector(n) for n in part['normals']]
        source.append(p);source_bones[identity]=Vector(part['origin'])
# Carry the top cartridge from the author's spare full magazine into the fitted one.
empty=next(v for k,v in source_transforms.items() if 'mag empty' in k)
full=next(v for k,v in source_transforms.items() if k.startswith('919 2011 15rnd mag_'))
relocate=empty@full.inverted()
for part in raw:
    if not part['identity'].startswith('919 2011 15rnd mag_') or part['material'] not in ('brass','copper'):continue
    vv=[relocate@Vector(v) for v in part['verts']]
    # glTF duplicates vertices at sharp corners; join coincident positions for shell identity.
    key={};representatives=[];adj={}
    for i,v in enumerate(vv):
        q=tuple(round(x,6) for x in v)
        k=key.setdefault(q,len(key));representatives.append(k);adj.setdefault(k,set())
    for face in part['faces']:
        ids=[representatives[i] for i in face]
        for a in ids:adj[a].update(ids)
    seen=set();components=[]
    for k in adj:
        if k in seen:continue
        stack=[k];seen.add(k);component=set()
        while stack:
            i=stack.pop();component.add(i)
            for j in adj[i]:
                if j not in seen:seen.add(j);stack.append(j)
        ids=[i for i,rid in enumerate(representatives) if rid in component]
        components.append(ids)
    chosen=max(components,key=lambda ids:sum(vv[i].z for i in ids)/len(ids))
    keep=set(chosen);mapping_indices={old:i for i,old in enumerate(chosen)}
    faces=[];uv=[];normals=[]
    normals_in=[relocate.to_3x3()@Vector(n) for n in part['normals']]
    cursor=0
    for face in part['faces']:
        if all(i in keep for i in face):
            faces.append([mapping_indices[i] for i in face])
            uv.extend(part['uv'][cursor:cursor+len(face)])
            normals.extend(normals_in[cursor:cursor+len(face)])
        cursor+=len(face)
    source.append({'name':'TopRound_'+part['material'],'identity':'TopRound','material':part['material'],
        'verts':[vv[i] for i in chosen],'faces':faces,'uv':uv,'normals':normals})
source_bones['TopRound']=sum((v for p in source if p['identity']=='TopRound' for v in p['verts']),Vector())/sum(len(p['verts']) for p in source if p['identity']=='TopRound')
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
        if m and not m.name.startswith('M_PitViper2011_Manny_'):m.name='M_PitViper2011_Manny_'+m.name

# Source trigger pivot registers to the donor's real trigger; source dimensions stay intact.
trigger_identity='2011pv trigga_5'
alignment=Matrix.Translation((rootinv@rest['WPN_Trigger']).translation-source_bones[trigger_identity])
mapping={
 '2011pv slide_1':'WPN_Slide','2011pv barrel compensator_2':'WPN_Barrel',
 '2011pv hammer_3':'WPN_Hammer','2011pv trigga_5':'WPN_Trigger',
 '2011pv mag release_0':'WPN_MagRelease','2011pv bolt release_6':'WPN_SlideRelease',
 '2011pv safety_7':'WPN_Safety','919 2011 15rnd mag empty_8':'WPN_SOCKET_Magazine',
 'TopRound':'WPN_Bullet'}
newrest={n:m.copy() for n,m in rest.items()}
for old,new in mapping.items():
    if new=='WPN_root':continue
    newrest[new].translation=root@(alignment@source_bones[old])
slide=next(p for p in source if p['identity']=='2011pv slide_1' and p['material']=='h-190')
front=next(p for p in source if p['material']=='tritium')
fv=front['verts'];front_point=sum(fv,Vector())/len(fv)
rear_vertices=[v for v in slide['verts'] if v.y>.075 and v.z>.05]
rear_point=Vector((0,sum(v.y for v in rear_vertices)/len(rear_vertices),front_point.z))
comp=next(p for p in source if p['identity']=='2011pv barrel compensator_2' and p['material']=='h-190')
barrel=next(p for p in source if p['identity']=='2011pv barrel compensator_2' and p['material']=='copper')
bore_front=min(v.y for v in barrel['verts'])
rim=[v for v in barrel['verts'] if v.y<bore_front+.0005]
bore_z=(min(v.z for v in rim)+max(v.z for v in rim))*.5
markers={'WPN_SOCKET_Muzzle':(0,min(v.y for v in comp['verts']),bore_z),
         'WPN_SOCKET_Eject':(.010,0,.034),
         'WPN_RearSight':list(rear_point),'WPN_FrontSight':list(front_point)}
for n,p in markers.items():newrest[n].translation=root@(alignment@Vector(p))
newparent=dict(parent)
newparent['WPN_Safety']='WPN_root'
newparent['WPN_Bullet']='WPN_SOCKET_Magazine'
newparent['WPN_FrontSight']='WPN_Barrel'
newlr={n:newrest[newparent[n]].inverted()@m if newparent[n] else m for n,m in newrest.items()}
gun=[]
for src in source:
    mesh=bpy.data.meshes.new(src['name']+'_Geometry');mesh.from_pydata([root@alignment@v for v in src['verts']],[],src['faces']);mesh.update()
    for p in mesh.polygons:p.use_smooth=True
    mesh.normals_split_custom_set([(root@alignment).to_3x3()@n for n in src['normals']])
    uv=mesh.uv_layers.new(name='UVMap')
    for l,co in zip(uv.data,src['uv']):l.uv=co
    ob=bpy.data.objects.new('PitViper2011_'+src['name'],mesh);s.collection.objects.link(ob);ob.parent=r;ob.matrix_basis=Matrix.Identity(4)
    slot='Magazine_'+src['material'] if mapping.get(src['identity'])=='WPN_SOCKET_Magazine' else src['material']
    if src['identity']=='2011pv barrel compensator_2' and src['material']=='h-190':slot='FactoryCompensator'
    part_mat=bpy.data.materials.get('M_PitViper2011_'+slot) or bpy.data.materials.new('M_PitViper2011_'+slot)
    ob.data.materials.append(part_mat)
    bone='WPN_Barrel' if src['material']=='tritium' else mapping.get(src['identity'],'WPN_root')
    ob.vertex_groups.new(name=bone).add(list(range(len(src['verts']))),1.,'REPLACE')
    mod=ob.modifiers.new('PitViper2011_MechanicalSkin','ARMATURE');mod.object=r;gun.append(ob)

# Source action pose is sampled on its original rig; only the resulting new
# tracks use the relocated PitViper2011 mechanical reference. Arm rest matrices stay put.
idle=select(actions['idle'],0)
oldmag=(rootinv@rest['WPN_SOCKET_Magazine']).translation
newmag=(rootinv@newrest['WPN_SOCKET_Magazine']).translation
mag_delta=newmag-oldmag
held={side:idle['WPN_root'].inverted()@idle['hand_'+side] for side in ('r','l')}
# Author a bounded whole-hand fit on the actual PitViper2011 surface. Native finger
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
    fit[side]=delta;fit_record[side]={'translation_m':list(delta),'source':'native V7 palm and fingers; bounded PitViper2011 surface authoring','objective':value}
    print('PitViper2011_GRIP_AUTHORED',SIDE,side,list(delta),flush=True)
# Existing full-chain solver carries elbow and twist bones with contact changes.
tree=ast.parse((S/'M1911Contact20260913/author_contacts.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve_arm'],type_ignores=[]),'<PitViper2011 full arm contact>','exec'))
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
    fire_recipe=fire_motion.settings(SIDE,kind) if is_fire else None
    duration=fire_recipe['duration'] if is_fire else (2.25 if kind=='reload_empty' else 1.75) if SIDE!='single' and kind in ('reload','reload_empty') else source_duration
    frames=[i*.5 for i in range(round(duration*120)+1)];rows=[];previous={}
    for f in frames:
        t=f/60
        sample_time=t*source_duration/duration if is_fire or (SIDE!='single' and kind in ('reload','reload_empty')) else t
        if is_fire:
            neutral=select(actions['aim' if kind.startswith('aim') else 'idle'],0)
            old=fire_motion.pose(neutral,select(source_action,sample_time),parent,fire_recipe['source_gain'])
        else:old=select(source_action,sample_time)
        p={n:m.copy() for n,m in old.items()};G=old['WPN_root']
        for n in names:
            if n.startswith('WPN_') and n!='WPN_root':p[n]=old[n]@rest[n].inverted()@newrest[n]
        # Frame-mounted controls stay with the frame, never with the slide.
        p['WPN_Safety']=G@rootinv@newrest['WPN_Safety']
        p['WPN_Bullet']=p['WPN_SOCKET_Magazine']@newrest['WPN_SOCKET_Magazine'].inverted()@newrest['WPN_Bullet']
        for n in markers:
            bone='WPN_Barrel' if n in ('WPN_SOCKET_Muzzle','WPN_FrontSight') else 'WPN_Slide'
            p[n]=p[bone]@newrest[bone].inverted()@newrest[n]
        if is_fire:
            peak=smooth(t/.012)
            travel=peak if kind.endswith('_last') else peak*(1-smooth((t-.012)/.031))
            for n in ('WPN_Slide','WPN_RearSight','WPN_SOCKET_Eject'):
                p[n]=G@rootinv@newrest[n];p[n].translation+=G.to_3x3()@Vector((0,.032*travel,0))
            local=rootinv@newrest['WPN_Barrel'];p['WPN_Barrel']=G@Matrix.Translation((0,.004*travel,-.0015*travel))@local@Matrix.Rotation(-.035*travel,4,'X')
            for marker in ('WPN_SOCKET_Muzzle','WPN_FrontSight'):
                p[marker]=p['WPN_Barrel']@newrest['WPN_Barrel'].inverted()@newrest[marker]
            trigger=(rootinv@newrest['WPN_Trigger']).translation
            p['WPN_Trigger']=G@Matrix.Translation((0,.0018*peak,0))@rootinv@newrest['WPN_Trigger']
            hammer=(rootinv@newrest['WPN_Hammer']).translation
            fall=smooth(t/.003)*(1-smooth((t-.010)/.025))
            p['WPN_Hammer']=G@Matrix.Translation(hammer)@Matrix.Rotation(.55*fall,4,'X')@Matrix.Translation(-hammer)@rootinv@newrest['WPN_Hammer']

        else:
            # The reference slide stroke is longer; rescale only its relative
            # translation, leaving the author gun/hand motion intact.
            slide_local=G.inverted()@p['WPN_Slide'];bind=rootinv@newrest['WPN_Slide']
            travel=slide_local.translation-bind.translation
            offset=-travel*.20
            for n in ('WPN_Slide','WPN_RearSight','WPN_SOCKET_Eject'):p[n].translation+=G.to_3x3()@offset
        for side,delta in fit.items():
            distance=((G.inverted()@old['hand_'+side]).translation-held[side].translation).length
            weight=1. if SIDE!='single' or side=='r' else 1-smooth((distance-.018)/.050)
            if SIDE=='single' and side=='l' and kind.startswith('reload'):
                weight*=1-smooth((t-.04)/.1)+smooth((t-(1.85 if kind=='reload_empty' else 1.25))/.25)
            if weight:shift_hand(p,p.copy(),side,delta*weight)
        if SIDE=='single' and kind.startswith('reload'):
            w=smooth((t-.08)/.14)*(1-smooth((t-1.13)/.17))
            if w:shift_hand(p,old,'l',mag_delta*w)
        if SIDE=='single' and kind=='reload_empty':
            delta=(rootinv@newrest['WPN_SlideRelease']).translation-(rootinv@rest['WPN_SlideRelease']).translation
            w=smooth((t-1.37)/.12)*(1-smooth((t-1.67)/.14))
            if w:shift_hand(p,p.copy(),'l',delta*w)
        p['WPN_Bullet']=p['WPN_SOCKET_Magazine']@newrest['WPN_SOCKET_Magazine'].inverted()@newrest['WPN_Bullet']
        empty=('empty' in kind and not kind.startswith('reload')) or (kind=='reload_empty' and t<1.05) or (kind.endswith('_last') and t>.016)
        # A singular FBX bone transform produces non-finite decomposition.
        # The fire family's top round becomes submicron instead of scale zero.
        if empty:p['WPN_Bullet']=p['WPN_Bullet']@Matrix.Scale(.0001 if is_fire else 0.,4)
        row={}
        for n in names:
            loc,q,scale=(newlr[n].inverted()@(p[newparent[n]].inverted()@p[n] if newparent[n] else p[n])).decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        rows.append(row)
    support.DURATION=duration
    stem='PitViper2011' if SIDE=='single' else 'Dual_PitViper2011_'+SIDE
    a=support.bake_action(r,s,'PitViper2011Auth_'+SIDE+'_'+kind,rows,frames);made[kind]=a
    records[kind]={'duration':duration,'donor_action':source_action.name,'sample_rate':120,'file':'Animations/A_'+stem+'_'+kind+'.fbx'}
    if fire_recipe:records[kind]['fire_motion']=dict(fire_recipe,source_duration=source_duration)
    print('PitViper2011_ACTION_AUTHORED',SIDE,kind,duration,flush=True)

r.animation_data_clear()
bpy.context.view_layer.objects.active=r;bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n in names:
    b=r.data.edit_bones[n];length=b.length;b.parent=r.data.edit_bones[newparent[n]] if newparent[n] else None;b.use_connect=False;b.matrix=newrest[n];b.length=length
bpy.ops.object.mode_set(mode='OBJECT')
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
r.name='SK_PitViper2011_Manny' if SIDE=='single' else 'SK_Dual_PitViper2011_'+SIDE
for ob in [r]+hands+gun:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(OUT/(r.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False)
for kind,a in made.items():
    r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.frame_start=0;s.frame_end=round(records[kind]['duration']*60);s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/records[kind]['file']),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
r.animation_data.action=made['idle'];r.animation_data.action_slot=made['idle'].slots[0];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('PitViper2011_'+SIDE+'_Editable.blend')))
(OUT/'authoring.json').write_text(json.dumps({'source':str(O/'Original/PitViper2011_Official.glb'),'skin':skin_source,'alignment':[list(x) for x in alignment],'markers_source_m':markers,'mechanical_part_mapping':mapping,'source_dimension_policy':'0.1m/source-unit from author 9mm bullet, no model resize to donor','factory_capacity':15,'grip_authoring':fit_record,'magazine_contact_delta_m':list(mag_delta),'clips':records,'mesh':r.name+'.fbx','testing':'Not performed'},indent=2))
print('PitViper2011_AUTHORING_SAVED',SIDE,flush=True)

if SIDE=='single':
    (O/'icon_parts.json').write_text(json.dumps([{k:v for k,v in p.items() if k in ('name','identity','material','faces')}|{'verts':[list(v) for v in p['verts']]} for p in source]),encoding='utf8')
