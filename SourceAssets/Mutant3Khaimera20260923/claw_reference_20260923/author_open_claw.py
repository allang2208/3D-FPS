"""Author the user's spread, hooked claw from the original hand, not the rejected curl."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'Mutant3_Khaimera_Feral.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
rig.name='Mutant3Root'
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
mesh=bpy.data.objects['Mesh0']
points=[mesh.matrix_world@v.co for v in mesh.data.vertices]
original=[v.co.copy() for v in mesh.data.vertices]
original_rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parts=json.loads((ROOT.parent/'hand_ground_fix/finger_components.json').read_text())
chains={}
PROFILE={
    'Index': {'curl':[8,70,32], 'spread':-10},
    'Middle':{'curl':[6,76,32], 'spread':-2},
    'Ring':  {'curl':[10,72,35], 'spread':7},
    'Pinky': {'curl':[15,68,32], 'spread':15},
    'Thumb': {'curl':[5,30,28], 'spread':-10},
}

def centroid(ids):return sum((points[i] for i in ids),Vector())/len(ids)
for side,sign in [('Left',1),('Right',-1)]:
    # The four separated fingertip branches are actual connected components of
    # this mesh, ordered from index to little finger across the palm.
    digits=sorted(parts[side]['0.83'],key=lambda p:(p['lo'][1]+p['hi'][1])/2)
    for label,part in zip(['Index','Middle','Ring','Pinky'],digits):
        ids=part['ids'];end=max(points[i].x*sign for i in ids)
        tip=centroid([i for i in ids if points[i].x*sign>end-.009])
        root_x={'Index':.792,'Middle':.800,'Ring':.795,'Pinky':.788}[label]
        base=centroid([i for i in ids if points[i].x*sign<.855])
        base.x=sign*root_x
        # Finger bases sit on the palm plane; taper out to the measured tips.
        base.z+=.005
        knots=[base,base.lerp(tip,.43),base.lerp(tip,.76),tip]
        chains[side+label]={'side':side,'sign':sign,'digit':label,'knots':knots,'angles':PROFILE[label]['curl'],
                           'spread':PROFILE[label]['spread'],'curl':Vector((0,0,-1)), 'tip_ids':set(ids)}
    tip_part=next(p for p in parts[side]['0.775'] if p['hi'][1]<0)
    ids=tip_part['ids'];tip=centroid([i for i in ids if points[i].y<-.023])
    base=Vector((sign*.746,.020,1.300 if side=='Left' else 1.296))
    chains[side+'Thumb']={'side':side,'sign':sign,'digit':'Thumb','knots':[base,base.lerp(tip,.43),base.lerp(tip,.76),tip],
                        'angles':PROFILE['Thumb']['curl'],'spread':PROFILE['Thumb']['spread'],
                        'curl':Vector((0,.8,-.6)).normalized(),'tip_ids':set(ids)}

bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
inv=rig.matrix_world.inverted()
for key,chain in chains.items():
    parent=rig.data.edit_bones[chain['side']+'Hand']
    names=[]
    for j in range(3):
        bone=rig.data.edit_bones.new(key+str(j+1)+'_Claw')
        bone.head=inv@chain['knots'][j];bone.tail=inv@chain['knots'][j+1]
        bone.parent=parent;bone.use_connect=False;bone.use_deform=True
        bone.align_roll(inv.to_3x3()@Vector((0,0,1)))
        names.append(bone.name);parent=bone
    chain['bones']=names
bpy.ops.object.mode_set(mode='OBJECT')
groups={g.index:g.name for g in mesh.vertex_groups}
for chain in chains.values():
    for name in chain['bones']:mesh.vertex_groups.new(name=name)

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

changed=set();weighted={name:0 for chain in chains.values() for name in chain['bones']}
for vertex,p in zip(mesh.data.vertices,points):
    weights={groups[g.group]:g.weight for g in vertex.groups if g.group in groups}
    side='Left' if p.x>0 else 'Right'
    pool=sum(w for name,w in weights.items() if name.startswith(side+'Hand'))
    if pool<.01:continue
    candidates=[]
    for key,c in chains.items():
        if c['side']!=side:continue
        a,b=c['knots'][0],c['knots'][-1];v=b-a
        t=(p-a).dot(v)/v.length_squared
        nearest=a+v*max(0,min(1,t))
        dist=(p-nearest).length
        # Fully assign separated finger surfaces to their own digit. Do not
        # retain palm/old Hand_End influence on the edges of a bent fingertip.
        # Only the knuckle-to-palm transition uses a longitudinal weight fade.
        owned_tip=vertex.index in c['tip_ids']
        coverage=1.0 if owned_tip else smooth((t+.06)/.25)*smooth((.044-dist)/.012)
        if c['digit']=='Thumb' and not owned_tip:coverage*=smooth((.034-p.y)/.020)
        candidates.append((-1 if owned_tip else dist,c,coverage,t))
    _,chain,coverage,t=min(candidates,key=lambda item:item[0])
    if coverage<=.0001:continue
    changed.add(vertex.index)
    total=sum(weights.values())
    for name,w in weights.items():
        mesh.vertex_groups[name].add([vertex.index],w*(1-coverage),'REPLACE')
    # Smooth overlap around interphalangeal joints, leaving finger tips on the
    # distal bone and the palm/forearm weights outside this hand pool untouched.
    a=smooth((t-.36)/.14);b=smooth((t-.70)/.12)
    segments=[1-a,a*(1-b),a*b]
    for name,w in zip(chain['bones'],segments):
        value=total*coverage*w
        if value>1e-7:mesh.vertex_groups[name].add([vertex.index],value,'REPLACE');weighted[name]+=1

# Keep the proximal fingers extended and splayed, concentrate flexion at PIP/DIP,
# and keep the thumb outside the palm. Bake the skin and its matching bind pose.
for chain in chains.values():
    for name,angle in zip(chain['bones'],chain['angles']):
        pb=rig.pose.bones[name];direction=(chain['knots'][-1]-chain['knots'][0]).normalized()
        axis=direction.cross(chain['curl']).normalized()
        local=pb.bone.matrix_local.to_quaternion().inverted()@(inv.to_3x3()@axis)
        pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(local,math.radians(angle))
        if name==chain['bones'][0]:
            spread_axis=pb.bone.matrix_local.to_quaternion().inverted()@(inv.to_3x3()@Vector((0,0,chain['sign'])))
            pb.rotation_quaternion=Quaternion(spread_axis,math.radians(chain['spread']))@pb.rotation_quaternion
bpy.context.view_layer.update()
obj=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());evaluated=obj.to_mesh()
for i in changed:mesh.data.vertices[i].co=evaluated.vertices[i].co
obj.to_mesh_clear()
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
# Keep the original body's tangent-normal bake basis, but refresh the custom
# normals on fingers whose neutral geometry was curled above.
source_normals=[n.vector.copy() for n in mesh.data.corner_normals]
finger_groups={g.index for g in mesh.vertex_groups if g.name.endswith('_Claw')}
finger_weight=[min(1.0,sum(g.weight for g in v.groups if g.group in finger_groups)) for v in mesh.data.vertices]
for polygon in mesh.data.polygons:polygon.use_smooth=True
mesh.data.normals_split_custom_set([(0.0,0.0,0.0)]*len(mesh.data.loops))
mesh.data.update()
fresh_normals=[n.vector.copy() for n in mesh.data.corner_normals]
mesh.data.normals_split_custom_set([tuple(old.lerp(fresh,finger_weight[loop.vertex_index]).normalized())
    for loop,old,fresh in zip(mesh.data.loops,source_normals,fresh_normals)])
mesh.data.update()
report={'new_finger_bones':len(weighted),'weighted_vertices':weighted,'hand_vertices_modified':len(changed),
        'body_vertex_change_m':max((mesh.data.vertices[i].co-original[i]).length for i in range(len(original)) if i not in changed),
        'original_bone_rest_max_error':max(max(abs(rig.data.bones[n].matrix_local[i][j]-m[i][j]) for i in range(4) for j in range(4)) for n,m in original_rest.items()),
        'reference':'user_hand_reference.jpg',
        'chains':{k:{'bones':v['bones'],'curl_degrees':v['angles'],'spread_degrees':v['spread'],
                     'knots_world':[list(p) for p in v['knots']]} for k,v in chains.items()}}
# New finger rest transforms encode the relaxed claw; original body bones were
# neutral. Record their float roundtrip error instead of claiming bitwise identity.
if report['body_vertex_change_m']!=0:raise RuntimeError('Body vertices changed')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_OpenClaw_Source.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SK_Mutant3_Claw.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',mesh_smooth_type='FACE',path_mode='STRIP')
(ROOT/'claw_skin.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CLAW_SKIN_AUTHORED '+json.dumps({k:v for k,v in report.items() if k!='chains'}),flush=True)

# Preserve the existing grounded body animations exactly as Blender action
# curves; exporting with the new finger bind pose changes only finger tracks.
for action in bpy.data.actions:
    if action.name.startswith('A_Mutant3_'):action.name='BeforeOpenClaw_'+action.name
contract=json.loads((ROOT.parent/'hand_ground_fix/animation_contract.json').read_text())
action_names=['A_Mutant3_'+role for role in contract['clips']]
with bpy.data.libraries.load(str(ROOT.parent/'hand_ground_fix/Mutant3_Khaimera_ClawGrounded.blend'),link=False) as (available,loaded):
    loaded.actions=action_names
scene=bpy.context.scene;scene.render.fps=60;scene.render.fps_base=1
out=ROOT/'animations';out.mkdir(exist_ok=True)
for role,info in contract['clips'].items():
    action=bpy.data.actions['A_Mutant3_'+role]
    action.use_fake_user=True
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    scene.frame_start,scene.frame_end=info['frames']
    scene.frame_set(scene.frame_start)
    bpy.ops.export_scene.fbx(filepath=str(out/(action.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE',path_mode='STRIP')
    print('OPEN_CLAW_ANIMATION_EXPORTED '+role,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_OpenClaw_Animated.blend'))
contract['revision']='Spread hooked fingers from user photo, preserving V2 grounded body curves'
contract['state']='Authored mesh and nine animation FBX files; import pending; no gameplay tests'
(ROOT/'animation_contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
