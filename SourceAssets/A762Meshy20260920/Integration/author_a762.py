"""A762: preserve Meshy surfaces, split mechanical parts and bind to Manny.
Only author/export operations. No render or test execution.
"""
import bpy,json,math
from pathlib import Path
from collections import defaultdict
from mathutils import Matrix,Vector

O=Path(__file__).parent;S=O.parent.parent;D=O/'Exports';D.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
SCALE=.48
FIT=Matrix(((0,-SCALE,0,-.0052),(SCALE,0,0,-.13),(0,0,SCALE,-.008),(0,0,0,1)))
MARKERS={
 'WPN_FrontSight':(-.751,-.012,.248), 'WPN_RearSight':(.387,-.012,.248),
 'WPN_SOCKET_Muzzle':(-.951,-.012,.130), 'WPN_SOCKET_Eject':(.060,.033,.155)}
HINGES={'RearSight':Vector((.387,-.012,.223)), 'FrontSight':Vector((-.753,-.012,.173))}

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]

def part_of(c):
    x,y,z=c
    if -.225<x<.14 and z<.072:return 'Magazine'
    if .165<x<.222 and .006<z<.064 and -.032<y<.006:return 'Trigger'
    if -.145<x<.235 and y>.026 and .125<z<.184:return 'Bolt'
    if x<-.807:return 'Flash_Hider'
    if -.805<x<-.702 and z>.174:return 'FrontSight'
    if .31<x<.45 and z>.224:return 'RearSight'
    if x>.497:return 'FactoryStock'
    if .277<x<.51 and z<.041:return 'FactoryRearGrip'
    if -.495<x<-.167 and .075<z<.191:return 'Handguard'
    return 'Receiver'

bpy.ops.wm.open_mainfile(filepath=str(O.parent/'A762_Meshy_Candidate01_Editable.blend'))
src=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=src.data
raw=[src.matrix_world@v.co for v in me.vertices]
faces=[list(p.vertices) for p in me.polygons]
uv=[tuple(v.uv) for v in me.uv_layers.active.data]
normals=[(src.matrix_world.to_3x3().inverted().transposed()@n.vector).normalized() for n in me.corner_normals]
loops=[list(p.loop_indices) for p in me.polygons]
parts=defaultdict(list)
for i,face in enumerate(faces):parts[part_of(sum((raw[v] for v in face),Vector())/len(face))].append(i)
edge_parts=defaultdict(set)
for name,ids in parts.items():
    for fi in ids:
        f=faces[fi]
        for a,b in zip(f,f[1:]+f[:1]):edge_parts[tuple(sorted((a,b)))].add(name)

BASE=S/'AKMSoviet20260911/AKM_Soviet_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export']
r.animation_data.action=bpy.data.actions['AKM_Native_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy();pose={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones}
for ob in list(s.objects):
    if ob.type=='MESH' and ob!=hands:bpy.data.objects.remove(ob,do_unlink=True)

base=bpy.data.materials.new('M_A762_SourcePBR');base.use_nodes=True
nodes=base.node_tree.nodes;links=base.node_tree.links;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs['Surface'])
for channel,pin in [('base_color','Base Color'),('roughness','Roughness'),('metallic','Metallic'),('normal','Normal')]:
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O.parent/f'Meshy/candidate01/downloads/texture_urls_0_{channel}.png'))
    if channel!='base_color':tex.image.colorspace_settings.name='Non-Color'
    if channel=='normal':
        nm=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs[pin])
    else:links.new(tex.outputs['Color'],bs.inputs[pin])
inside=bpy.data.materials.new('M_A762_Inside');inside.use_nodes=True
inside.node_tree.nodes.clear();ib=inside.node_tree.nodes.new('ShaderNodeBsdfPrincipled');io=inside.node_tree.nodes.new('ShaderNodeOutputMaterial');inside.node_tree.links.new(ib.outputs[0],io.inputs['Surface'])
ib.inputs['Base Color'].default_value=(.013,.016,.020,1)
ib.inputs['Metallic'].default_value=.8
ib.inputs['Roughness'].default_value=.52
objects=[];report={'fit_matrix':[list(row) for row in FIT],'working_length_m':1.900689*SCALE,'parts':{},'markers_blender_root':{k:list(FIT@Vector(v)) for k,v in MARKERS.items()},'hinges_ue_root':{},'animations':{}}
for name,ids in parts.items():
    bone={'Magazine':'WPN_SOCKET_Magazine','Trigger':'WPN_Trigger','Bolt':'WPN_bolt'}.get(name,'WPN_root')
    static=name in HINGES
    transform=Matrix.Translation(-(FIT@HINGES[name]))@FIT if static else rest[bone]@pose[bone].inverted()@root@FIT
    normal_xf=transform.to_3x3().inverted().transposed()
    source_ids=sorted({vi for fi in ids for vi in faces[fi]});mapping={vi:i for i,vi in enumerate(source_ids)}
    verts=[transform@raw[vi] for vi in source_ids];newfaces=[[mapping[v] for v in faces[fi]] for fi in ids]
    face_uv=[[uv[li] for li in loops[fi]] for fi in ids]
    face_norm=[[tuple((normal_xf@normals[li]).normalized()) for li in loops[fi]] for fi in ids]
    original_faces=len(newfaces)
    # Close only newly cut interfaces. Intentional original holes remain untouched.
    borders=defaultdict(list)
    for fi in ids:
        f=faces[fi]
        for a,b in zip(f,f[1:]+f[:1]):
            if len(edge_parts[tuple(sorted((a,b)))])>1:borders[a].append(b)
    used=set()
    for start in borders:
        for nxt in borders[start]:
            if (start,nxt) in used:continue
            ring=[start];a,b=start,nxt
            for _ in range(len(borders)+2):
                used.add((a,b));ring.append(b)
                if b==start:break
                choices=[c for c in borders.get(b,[]) if (b,c) not in used]
                if len(choices)!=1:break
                a,b=b,choices[0]
            if ring[-1]!=start or len(ring)<4:continue
            ring=ring[:-1];center=sum((verts[mapping[v]] for v in ring),Vector())/len(ring);ci=len(verts);verts.append(center)
            for k,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
                newfaces.append([mapping[b],mapping[a],ci]);face_uv.append([(1,0),(0,0),(.5,1)])
                n=(verts[mapping[a]]-verts[mapping[b]]).cross(center-verts[mapping[b]]).normalized();face_norm.append([tuple(n)]*3)
    mesh=bpy.data.meshes.new('A762_'+name);mesh.from_pydata(verts,[],newfaces);mesh.update()
    mat=base.copy();mat.name='M_A762_'+name;mesh.materials.append(mat);mesh.materials.append(inside)
    layer=mesh.uv_layers.new(name='UVMap')
    for fi,p in enumerate(mesh.polygons):
        p.use_smooth=True;p.material_index=0 if fi<original_faces else 1
        for j,li in enumerate(p.loop_indices):layer.data[li].uv=face_uv[fi][j]
    mesh.normals_split_custom_set([n for face in face_norm for n in face])
    ob=bpy.data.objects.new(('SM_' if static else '')+'A762_'+name,mesh);s.collection.objects.link(ob)
    if static:
        select([ob]);bpy.ops.export_scene.fbx(filepath=str(D/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
        p=FIT@HINGES[name];report['hinges_ue_root'][name]=[p.x,-p.y,p.z]
        ob.hide_set(True);ob.hide_render=True
    else:
        ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
        ob.vertex_groups.new(name=bone).add(list(range(len(verts))),1,'REPLACE');mod=ob.modifiers.new('MannyWeaponRig','ARMATURE');mod.object=r;objects.append(ob)
    report['parts'][name]={'faces':len(newfaces),'source_faces':original_faces,'bone':bone,'static':static,'material':mat.name}
select(objects+[hands,r]);bpy.ops.export_scene.fbx(filepath=str(D/'SK_A762_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
for a in bpy.data.actions:a.use_fake_user=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_Rigged_Editable.blend'))

clips=[('idle',BASE,'AKM_Native_idle'),('aim',BASE,'AKM_Native_aim'),('fire',BASE,'AKM_Native_fire'),('aim_fire',BASE,'AKM_Native_aim_fire'),('inspect',BASE,'AKM_Native_inspect'),('equip',BASE,'AKM_EquipCharge')]
for key in ['reload','reload_empty']:clips.append((key,S/f'AKMReloadPolish20260911/base/A_AKM_{key}.blend',f'A_AKM_{key}_Polished'))
SPRINT=S/'RifleTacticalSprint20260915/AKM/Base/AKM_TacticalSprint_Base_Editable.blend'
for key in ['Enter','Loop','Exit']:clips.append(('sprint_'+key.lower(),SPRINT,'AKM_TacticalSprint_Base_'+key))
for key,blend,action_name in clips:
    bpy.ops.wm.open_mainfile(filepath=str(blend));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
    source=bpy.data.actions.get(action_name)
    if source is None:raise RuntimeError('Missing donor action '+action_name+' in '+str(blend))
    r.animation_data.action=source;r.animation_data.action_slot=source.slots[0]
    fps=s.render.fps/s.render.fps_base;start,end=map(int,source.frame_range);samples=[]
    for f in range(start,end+1):
        s.frame_set(f);bpy.context.view_layer.update();rt=r.pose.bones['WPN_root'].matrix.copy()
        for marker,position in MARKERS.items():
            pb=r.pose.bones[marker];m=pb.matrix.copy();m.translation=rt@(FIT@Vector(position));pb.matrix=m
        bpy.context.view_layer.update()
        samples.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
    a=bpy.data.actions.new('A_A762_'+key);a.use_fake_user=True;r.animation_data.action=a;previous={}
    for f,frame in enumerate(samples):
        for name,m in frame.items():
            loc,rot,scale=m.decompose()
            if name in previous and previous[name].dot(rot)<0:rot.negate()
            previous[name]=rot.copy();b=r.pose.bones[name];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=rot;b.scale=scale
            for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
    s.frame_start=0;s.frame_end=end-start;s.frame_set(0)
    select([r]);bpy.ops.export_scene.fbx(filepath=str(D/('A_A762_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    # Keep animation sources independently editable without duplicating the high-poly gun.
    bpy.data.libraries.write(str(O/('A_A762_'+key+'.blend')),{r,a},fake_user=True)
    report['animations'][key]={'source':str(blend),'action':action_name,'fps':fps,'frames':end-start,'seconds':(end-start)/fps,'loop':key in ['idle','aim','sprint_loop']}
    print('A762_AUTHORED',key,flush=True)
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('A762_AUTHORING_COMPLETE',flush=True)
