"""Author G18-only drum support grasp from the rifle palm-cup method.

No test, render, or game launch. Original right arm, weapon and mechanical
tracks retain their times; only the left arm and finger pose are authored.
"""
import bpy,json,math,ast,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parents[1];D=S/'AKMDrumFreeDrop20260920'
sys.path.insert(0,str(S/'M1911RevolverInspect20260927'))
import author_support as support
bpy.context.preferences.filepaths.save_version=0
contact=json.loads((D/'contact_fit.json').read_text())
donor_manifest=json.loads((D/'source_manifest.json').read_text())
donor_source=Path(donor_manifest['base/drum_reload']['source'][0]).with_suffix('.blend')
bpy.ops.wm.open_mainfile(filepath=str(donor_source))
donor_rig=bpy.data.objects['SK_M4_Infima']
donor_rest={b.name:b.matrix_local.copy() for b in donor_rig.data.bones}

def semantic_frame(forward,normal):
    f=forward.normalized();z=(normal-f*normal.dot(f)).normalized()
    return Matrix((f,f.cross(z),z)).transposed()

def palm_frame(rest):
    H=rest['hand_l'];forward=rest['middle_01_l'].translation-H.translation
    normal=(rest['pinky_01_l'].translation-H.translation).cross(rest['index_01_l'].translation-H.translation).normalized()
    return semantic_frame(forward,normal),normal

donor_semantic,_=palm_frame(donor_rest)
donor_frame=Matrix(json.loads((S/'LargeDrumUpgrade20260920/Reference/author_frames.json').read_text())['AKM']['canonical_to_source'])
donor_hand_canonical=donor_frame.inverted()@Matrix(contact['hand_in_mag'])
cup_semantic=donor_hand_canonical.to_3x3()@donor_rest['hand_l'].to_3x3().inverted()@donor_semantic
source=S/'G18Integration20260929/Single/G18_single_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
r=bpy.data.objects['SK_G18_Manny'];s=bpy.context.scene;s.render.fps=60
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest)
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
root=rest['WPN_root'];rootinv=root.inverted();magrest=rest['WPN_SOCKET_Magazine']
target_semantic,rest_normal=palm_frame(rest)
correction=target_semantic.inverted()@rest['hand_l'].to_3x3()
with bpy.data.libraries.load(str(O.parent/'G18_Drum50_Editable.blend'),link=False) as (src,dst):
    dst.objects=['Drum50_AuthoredBody','Retained_G18_Feed_Neck']
drum_objects=list(dst.objects)
feed=next(ob for ob in drum_objects if ob.name.startswith('Retained_'))
neck_points=[rootinv@v.co for v in feed.data.vertices]
neck_bottom=min(v.z for v in neck_points);end=[v for v in neck_points if abs(v.z-neck_bottom)<.00002]
cy=(min(v.y for v in end)+max(v.y for v in end))*.5+.004
center=Vector((0,cy,-.208));donor_center=Vector((0,0,-.085))
# Preserve the donor's supporting relation about the shell, compensating for
# radius and cap depth. Hand dimensions and bone lengths are not scaled.
anchor=donor_hand_canonical.translation-donor_center
anchor.z-=.063-.0605
anchor.y+=math.copysign(.004,anchor.y)
Hroot=Matrix.LocRotScale(center+anchor,(cup_semantic@correction).to_quaternion(),Vector((1,1,1)))
Hnative=root@Hroot
hand_in_mag=magrest.inverted()@Hnative
digits=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]

def finger_basis(strength):
    p={'hand_l':Hnative};result={};semantic=Hnative.to_3x3()@correction.inverted()
    for n in digits:
        parent=parents[n];m=p[parent]@lr[n];split=n.split('_')
        if len(split)==3 and split[1].isdigit():
            k=int(split[1])-1;nxt=f'{split[0]}_{k+2:02d}_l'
            rd=rest[nxt].translation-rest[n].translation if nxt in rest else rest[n].to_quaternion()@(rest[parent].to_quaternion().inverted()@(rest[n].translation-rest[parent].translation))
            spread=math.radians(contact['semantic_digits'][split[0]]['spread'][k])
            flex=math.radians(contact['semantic_digits'][split[0]]['flex'][k])*strength
            turn=semantic@Matrix.Rotation(spread,3,'Z')@Matrix.Rotation(-flex,3,'Y')@semantic_frame(rd,rest_normal).inverted()@rest[n].to_3x3()
            m=Matrix.LocRotScale(m.translation,turn.to_quaternion(),Vector((1,1,1)))
        p[n]=m;result[n]=(lr[n].inverted()@p[parent].inverted()@m).to_quaternion()
    return result

closed=finger_basis(1.0);opened=finger_basis(.38)
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def mix(a,b,t):
    al,aq,az=a.decompose();bl,bq,bz=b.decompose()
    return Matrix.LocRotScale(al.lerp(bl,t),aq.slerp(bq,t),az.lerp(bz,t))
# Reuse the full-arm solver: forearm roll follows the supporting palm, twist
# helpers follow complete bone segments, and each clip keeps its elbow side.
tree=ast.parse((D/'Scripts/build_animations.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve_arm'],type_ignores=[]),'<rifle drum whole-arm solver>','exec'))

def sample(action,t):
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    f=t*60;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in r.pose.bones}

arm=[n for n in names if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand'))]
report={'reference':str(D/'contact_fit.json'),'reference_revision':contact['revision'],'source':str(source),
        'method':'Shell-registered palm-under support, semantic finger remap to native G18 bind, fixed contact during insertion, release before withdrawal',
        'hand_in_mag':[list(row) for row in hand_in_mag],'drum_center_root_m':list(center),
        'changed_bones':arm+digits,'clips':{},'runtime_tested':False}
made={}
for kind,duration in [('reload',1.75),('reload_empty',2.25)]:
    base=bpy.data.actions['G18Auth_single_'+kind]
    frames=[i*.5 for i in range(round(duration*120)+1)];rows=[];previous={}
    return_end=1.48 if kind=='reload' else 1.40
    for f in frames:
        t=f/60;old=sample(base,t);p={n:m.copy() for n,m in old.items()}
        entry=smooth((t-.38)/.26)
        exit_blend=smooth((t-1.30)/(return_end-1.30))
        weight=entry*(1-exit_blend)
        if weight>0:
            held=old['WPN_SOCKET_Magazine']@hand_in_mag
            # Below/outside approach, then fixed shell-space grasp through seating.
            approach=held.copy()
            approach.translation+=old['WPN_SOCKET_Magazine'].to_3x3()@(magrest.inverted().to_3x3()@root.to_3x3()@Vector((.028,.018,-.034)))*(1-smooth((t-.48)/.16))
            H=mix(old['hand_l'],approach,entry)
            if t>1.215:
                clear=held.copy()
                clear.translation+=old['WPN_SOCKET_Magazine'].to_3x3()@(magrest.inverted().to_3x3()@root.to_3x3()@Vector((.070,.012,-.035)))
                H=mix(held,clear,smooth((t-1.215)/.085))
                H=mix(H,old['hand_l'],exit_blend)
            solve_arm(p,H,weight)
            if 'ik_hand_l' in p:p['ik_hand_l']=H.copy()
        row={}
        for n in names:
            local=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
            loc,q,scale=local.decompose()
            if n in digits and weight>0:
                base_local=lr[n].inverted()@old[parents[n]].inverted()@old[n]
                loc,base_q,scale=base_local.decompose()
                delay={'thumb':0,'index':.005,'middle':.010,'ring':.015,'pinky':.020}[n.split('_')[0]]
                close=smooth((t-.48-delay)/.14)
                release=smooth((t-1.135)/.080)
                target=opened[n].slerp(closed[n],close*(1-release))
                q=base_q.slerp(target,weight)
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        rows.append(row)
    support.DURATION=duration
    action=support.bake_action(r,s,'G18_Drum50_'+kind,rows,frames);made[kind]=action
    s.frame_start=0;s.frame_end=round(duration*60);s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    file=O/('A_G18_Drum50_'+kind+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    report['clips'][kind]={'duration':duration,'sample_rate':120,'fbx':str(file),'contact_window':[.64,1.135],'release_window':[1.135,return_end]}
    print('G18_DRUM50_RELOAD_AUTHORED',kind,flush=True)

# Store actual final drum on the native magazine bone in the editable source.
bpy.data.objects['G18_G18_mag'].hide_render=True;bpy.data.objects['G18_G18_mag'].hide_set(True)
for ob in drum_objects:
    s.collection.objects.link(ob);ob.parent=r;ob.matrix_basis=Matrix.Identity(4);ob.matrix_parent_inverse=Matrix.Identity(4)
    ob.vertex_groups.clear();group=ob.vertex_groups.new(name='WPN_SOCKET_Magazine');group.add(list(range(len(ob.data.vertices))),1,'REPLACE')
    ob.modifiers.clear();mod=ob.modifiers.new('Native magazine deformation','ARMATURE');mod.object=r
r.animation_data.action=made['reload'];r.animation_data.action_slot=made['reload'].slots[0];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'G18_Drum50_Reload_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('G18_DRUM50_RELOAD_SOURCE_SAVED',flush=True)
