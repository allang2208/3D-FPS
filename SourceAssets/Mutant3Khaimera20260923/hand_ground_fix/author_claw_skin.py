"""Add local finger controls and a relaxed claw neutral pose, preserving body skin."""
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
parts=json.loads((ROOT/'finger_components.json').read_text())
chains={}

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
        chains[side+label]={'side':side,'digit':label,'knots':knots,'angles':[8,16,10] if label!='Pinky' else [10,18,10],
                           'curl':Vector((0,0,-1))}
    tip_part=next(p for p in parts[side]['0.775'] if p['hi'][1]<0)
    ids=tip_part['ids'];tip=centroid([i for i in ids if points[i].y<-.023])
    base=Vector((sign*.746,.020,1.300 if side=='Left' else 1.296))
    chains[side+'Thumb']={'side':side,'digit':'Thumb','knots':[base,base.lerp(tip,.43),base.lerp(tip,.76),tip],
                        'angles':[8,10,4],'curl':Vector((0,1,.12)).normalized()}

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
        # Local longitudinal falloff blends the knuckle into the unchanged palm.
        coverage=smooth((t+.12)/.32)*smooth((.029-dist)/.012)
        if c['digit']=='Thumb':coverage*=smooth((.031-p.y)/.022)
        candidates.append((dist,c,coverage,t))
    _,chain,coverage,t=min(candidates,key=lambda item:item[0])
    if coverage<=.0001:continue
    changed.add(vertex.index)
    for name in list(weights):
        if name.startswith(side+'Hand'):mesh.vertex_groups[name].remove([vertex.index])
    mesh.vertex_groups[side+'Hand'].add([vertex.index],pool*(1-coverage),'REPLACE')
    # Smooth overlap around interphalangeal joints, leaving finger tips on the
    # distal bone and the palm/forearm weights outside this hand pool untouched.
    a=smooth((t-.35)/.18);b=smooth((t-.68)/.16)
    segments=[1-a,a*(1-b),a*b]
    for name,w in zip(chain['bones'],segments):
        value=pool*coverage*w
        if value>1e-7:mesh.vertex_groups[name].add([vertex.index],value,'REPLACE');weighted[name]+=1

# Bake the modest curl into this mesh's neutral fingers. Original animations have
# no finger tracks, so this posture remains consistent across running and attacks.
for chain in chains.values():
    for name,angle in zip(chain['bones'],chain['angles']):
        pb=rig.pose.bones[name];direction=(chain['knots'][-1]-chain['knots'][0]).normalized()
        axis=direction.cross(chain['curl']).normalized()
        local=pb.bone.matrix_local.to_quaternion().inverted()@(inv.to_3x3()@axis)
        pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(local,math.radians(angle))
bpy.context.view_layer.update()
obj=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());evaluated=obj.to_mesh()
for i in changed:mesh.data.vertices[i].co=evaluated.vertices[i].co
obj.to_mesh_clear()
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
report={'new_finger_bones':len(weighted),'weighted_vertices':weighted,'hand_vertices_modified':len(changed),
        'body_vertex_change_m':max((mesh.data.vertices[i].co-original[i]).length for i in range(len(original)) if i not in changed),
        'original_bone_rest_max_error':max(max(abs(rig.data.bones[n].matrix_local[i][j]-m[i][j]) for i in range(4) for j in range(4)) for n,m in original_rest.items()),
        'chains':{k:{'bones':v['bones'],'curl_degrees':v['angles'],'knots_world':[list(p) for p in v['knots']]} for k,v in chains.items()}}
# New finger rest transforms encode the relaxed claw; original body bones were
# neutral. Record their float roundtrip error instead of claiming bitwise identity.
if report['body_vertex_change_m']!=0:raise RuntimeError('Body vertices changed')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_Claw_Source.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SK_Mutant3_Claw.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',mesh_smooth_type='FACE',path_mode='STRIP')
(ROOT/'claw_skin.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CLAW_SKIN_AUTHORED '+json.dumps({k:v for k,v in report.items() if k!='chains'}),flush=True)
