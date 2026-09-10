"""Fit the user-provided AKM to the existing animation contract in an isolated file."""
import bpy
import json
import math
import shutil
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT=Path(r'D:\FPS3D\FPSGAME')
OUT=ROOT/'SourceAssets/AKMReplacement'
SOURCE=ROOT/'SourceAssets/AKM/SK_AKM_Viewmodel_Source.blend'
RAW=Path(r'D:\迅雷下载\akm.fbx')
SCALE=.13459
FIT=Matrix(((0,-SCALE,0,.0600),(SCALE,0,0,.2553),(0,0,SCALE,-.095),(0,0,0,1)))
PARTS={'high part akm':('AKMR_Body','WPN_root'),'ejection akm':('AKMR_Bolt','WPN_bolt'),
       'magazine akm':('AKMR_Magazine','WPN_SOCKET_Magazine'),'trigger akm':('AKMR_Trigger','WPN_Trigger')}
CLIPS=('idle','aim','fire','aim_fire','reload','reload_empty','draw','holster','inspect')
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
rig=bpy.data.objects['SK_AKM_Viewmodel']
rig.hide_set(False)
rig.hide_render=False
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.parent==rig and o.name.startswith('AKM_Classic_'):
        bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(RAW))
imported={name:bpy.data.objects[name] for name in PARTS}
components=json.loads((OUT/'akm_replacement_components.json').read_text())
wood_ids=set(i for c in components if c['index'] in [12,13,35] for i in c['ids'])
grip_ids=set(i for c in components if c['index']==37 for i in c['ids'])

def material(name,color,metallic,rough):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1)
    mat.use_nodes=True
    mat.node_tree.nodes.clear()
    bsdf=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled');bsdf.name='Principled BSDF'
    output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Metallic'].default_value=metallic
    bsdf.inputs['Roughness'].default_value=rough
    return mat

steel=material('M_AKMR_BluedSteel',(.032,.040,.049),.82,.38)
wood=material('M_AKMR_Walnut',(.23,.055,.017),0,.47)
grip=material('M_AKMR_Bakelite',(.15,.029,.011),0,.43)
bolt=material('M_AKMR_BoltSteel',(.09,.105,.12),.88,.29)
mag=material('M_AKMR_Parkerized',(.025,.032,.038),.72,.5)
materials=[steel,wood,grip,bolt,mag]
for name,obj in imported.items():
    obj.data.materials.clear()
    for mat in materials:obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.material_index=4 if name=='magazine akm' else 3 if name=='ejection akm' else 0
        if name=='high part akm':
            if all(v in wood_ids for v in face.vertices):face.material_index=1
            elif all(v in grip_ids for v in face.vertices):face.material_index=2
    transform=FIT@obj.matrix_world
    if name=='magazine akm':
        # Keep the old left-hand grasp volume and insertion path. A rigid offset only.
        transform.translation+=Vector((0,-.013,.005))
    obj.data.transform(rig.matrix_world.inverted()@transform)
    obj.parent=rig
    obj.matrix_parent_inverse=Matrix.Identity(4)
    obj.matrix_basis=Matrix.Identity(4)
    obj.name=PARTS[name][0]
    for g in list(obj.vertex_groups):obj.vertex_groups.remove(g)
    group=obj.vertex_groups.new(name=PARTS[name][1]);group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Rigid mechanical binding','ARMATURE');mod.object=rig
    obj.hide_render=False;obj.hide_set(False)

# The supplied mesh has a solid rear leaf and front protective ears but no notch
# or central post. Add three small physical sight inserts so ADS has real sights.
sight_vertices=[];sight_faces=[]
for mn,mx in [((.316,-.0336,.45),(.343,-.010,.51)),
              ((.316,.02208,.45),(.343,.0457,.51)),
              ((3.115,-.00196,.458),(3.133,.01404,.51))]:
    offset=len(sight_vertices)
    sight_vertices.extend([(x,y,z)for x in [mn[0],mx[0]]for y in [mn[1],mx[1]]for z in [mn[2],mx[2]]])
    sight_faces.extend([tuple(offset+i for i in f)for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]])
sight_mesh=bpy.data.meshes.new('AKMR_FunctionalIronSights');sight_mesh.from_pydata(sight_vertices,[],sight_faces)
sight_mesh.transform(rig.matrix_world.inverted()@FIT);sight_mesh.materials.append(mag)
sight_obj=bpy.data.objects.new('AKMR_FunctionalIronSights',sight_mesh);bpy.context.collection.objects.link(sight_obj)
sight_obj.parent=rig;sight_obj.matrix_parent_inverse=Matrix.Identity(4);sight_obj.matrix_basis=Matrix.Identity(4)
group=sight_obj.vertex_groups.new(name='WPN_root');group.add(list(range(len(sight_mesh.vertices))),1,'REPLACE')
mod=sight_obj.modifiers.new('Rigid sight binding','ARMATURE');mod.object=rig
for obj in [*imported.values(),sight_obj]:
    obj.modifiers.new('Export triangulation','TRIANGULATE')

# Coordinates refer to the upper edge of the two physical sight inserts.
marker_source={'WPN_RearSight':(.3295,.00604,.51),
               'WPN_FrontSight':(3.124,.00604,.51),
               'WPN_SOCKET_Muzzle':(3.44223,.00604,.13639),
               'WPN_SOCKET_Eject':(.04,-.123,.265),
               'WPN_Trigger':(-.645,.00604,-.15)}
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name,source_co in marker_source.items():
    b=rig.data.edit_bones.get(name) or rig.data.edit_bones.new(name)
    b.parent=rig.data.edit_bones['WPN_root'];b.use_connect=False
    b.head=rig.matrix_world.inverted()@(FIT@Vector(source_co))
    b.tail=b.head+Vector((0,1,0))
bpy.ops.object.mode_set(mode='OBJECT')

def assign(action):
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]

def sample(action,frame):
    assign(action);scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
    return {b.name:(b.location.copy(),b.rotation_quaternion.copy(),b.scale.copy())for b in rig.pose.bones}

idle_pose=sample(bpy.data.actions['AKM_idle'],1)
aim_pose=sample(bpy.data.actions['AKM_aim'],1)
for pose in [idle_pose,aim_pose]:pose['WPN_Trigger']=(Vector((0,0,0)),Quaternion((1,0,0,0)),Vector((1,1,1)))
clip_meta=[]
for clip in CLIPS:
    if clip not in ['fire','aim_fire']:
        act=bpy.data.actions['AKM_'+clip]
        clip_meta.append({'clip':clip,'action':act.name,'fps':24,'start':int(act.frame_range[0]),'end':int(act.frame_range[1]),'source':'unchanged source action'})

def new_action(name):
    act=bpy.data.actions.new(name);act.use_fake_user=True
    act.slots.new(id_type='OBJECT',name=rig.name);assign(act)
    return act

def write_pose(pose,frame):
    for n,(loc,rot,scale)in pose.items():
        b=rig.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=rot;b.scale=scale
        for key in ['location','rotation_quaternion','scale']:b.keyframe_insert(key,frame=frame,group=n)

fire_contract=json.loads((OUT/'akm_replacement_fire_contract.json').read_text())
travel=max(row['bones']['WPN_bolt']['loc'][1]for row in fire_contract if row['clip']=='fire')
for name,base in [('fire',idle_pose),('aim_fire',aim_pose)]:
    act=new_action('AKMR_'+name)
    for f in range(1,14):
        t=(f-1)/120
        # First recoil is code-driven; the magazine, weapon root and hand grip stay stable.
        if t<.012:pulse=0
        elif t<.033:pulse=(t-.012)/.021
        elif t<.05:pulse=1
        elif t<.085:pulse=1-(t-.05)/.035
        else:pulse=0
        pulse=max(0,min(1,pulse))
        pose={n:tuple(v.copy()for v in vals)for n,vals in base.items()}
        pose['WPN_bolt'][0].y+=travel*pulse
        pose['WPN_Trigger']=(Vector((0,0,0)),Quaternion(Vector((1,0,0)),math.radians(-4)*pulse),Vector((1,1,1)))
        write_pose(pose,f)
    clip_meta.append({'clip':name,'action':act.name,'fps':120,'start':1,'end':13,'source':'source bolt displacement envelope, resampled to 0.10 seconds; stable idle/aim hands; added trigger pivot'})

empty=bpy.data.actions['AKM_reload_empty']
target=sample(empty,43)
samples=[]
for f in range(1,329):
    t=(f-1)/120
    if t<.18:
        a=t/.18;a=a*a*(3-2*a)
        pose={n:(idle_pose[n][0].lerp(vals[0],a),idle_pose[n][1].slerp(vals[1],a),idle_pose[n][2].lerp(vals[2],a))for n,vals in target.items()}
    else:pose=sample(empty,min(104,43+(t-.18)*24))
    pose['WPN_Trigger']=(Vector((0,0,0)),Quaternion((1,0,0,0)),Vector((1,1,1)))
    samples.append(pose)
equip=new_action('AKMR_equip')
for f,pose in enumerate(samples,1):write_pose(pose,f)
clip_meta.append({'clip':'equip','action':equip.name,'fps':120,'start':1,'end':328,'source':'0.18s smooth idle blend to reload_empty at source 1.75s then remainder; terminal duration quantized +0.003333s'})

# Optional arms authored by the parallel pipeline, sharing the same bind matrices.
arms_path=ROOT/'SourceAssets/ArmsReplacement/SK_ArmsReplacement_Source.blend'
arms_manifest=ROOT/'SourceAssets/ArmsReplacement/arms_replacement_export.json'
arms_used=[]
if arms_path.exists() and arms_manifest.exists():
    manifest=json.loads(arms_manifest.read_text())
    names=manifest.get('mesh_objects',[manifest['mesh']])
    with bpy.data.libraries.load(str(arms_path),link=False)as (data_from,data_to):
        data_to.objects=names
    for o in data_to.objects:
        bpy.context.collection.objects.link(o)
        # The supplied arms vertices already use the combined rig's local bind
        # coordinates. A just-appended object's matrix_world is stale until depsgraph
        # evaluation, so do not preserve that transient matrix (it may be identity).
        o.parent=rig;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
        for m in o.modifiers:
            if m.type=='ARMATURE':m.object=rig
        o.hide_render=False;o.hide_set(False);arms_used.append(o.name)
        for mat in o.data.materials:
            if mat and mat not in materials:materials.append(mat)
    for o in list(bpy.data.objects):
        if o.type=='MESH' and o.parent==rig and o.name.startswith('SK_FP_CH_Default_Cubic'):
            bpy.data.objects.remove(o,do_unlink=True)

meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig and not o.hide_render]

def export_fbx(path,with_meshes,bake):
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);rig.hide_set(False)
    for o in with_meshes:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        apply_scale_options='FBX_SCALE_ALL',apply_unit_scale=True,use_space_transform=True,
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=bake,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,
        bake_anim_simplify_factor=0,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE',use_tspace=True)

assign(bpy.data.actions['AKM_idle']);scene.render.fps=24;scene.frame_start=1;scene.frame_end=2;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SK_AKM_Replacement_Source.blend'))
export_fbx(OUT/'SK_AKM_Replacement.fbx',meshes,False)
for clip in clip_meta:
    assign(bpy.data.actions[clip['action']]);scene.render.fps=clip['fps'];scene.frame_start=clip['start'];scene.frame_end=clip['end'];scene.frame_set(clip['start'])
    path=OUT/('A_AKM_'+clip['clip']+'.fbx');export_fbx(path,[],True)
    clip['duration']=(clip['end']-clip['start'])/clip['fps'];clip['path']=str(path)

root_inv=rig.data.bones['WPN_root'].matrix_local.inverted()
anchors={name:{'source_fbx':list(co),'blender_world_rest_m':list(FIT@Vector(co)),
               'weapon_root_local_cm':list(root_inv@rig.data.bones[name].head_local)}for name,co in marker_source.items()}
report={'raw_source':str(RAW),'source_to_world_rest':[list(r)for r in FIT],
    'missing_texture_count':12,'material_policy':'Authored constant PBR steel/walnut/bakelite substitutes; source FBX textures missing',
    'sight_geometry':'Added rear notch ears and central front post; supplied source has a solid rear leaf and empty front guard',
    'mesh_fbx':str(OUT/'SK_AKM_Replacement.fbx'),'blend':str(OUT/'SK_AKM_Replacement_Source.blend'),
    'bone_count':len(rig.data.bones),'anchors':anchors,'clips':clip_meta,'arms_replacement_meshes':arms_used,
    'meshes':[{'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'groups':[g.name for g in o.vertex_groups]}for o in meshes],
    'materials':[{'name':m.name,'color':list(next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value)[:3],
                  'metallic':next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Metallic'].default_value,
                  'roughness':next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value}for m in materials]}
(OUT/'akm_replacement_export_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
shutil.copy2(RAW,OUT/'UserProvided_AKM.fbx')
print('AKM_REPLACEMENT_EXPORTED='+json.dumps({'mesh':report['mesh_fbx'],'bones':report['bone_count'],'clips':len(clip_meta),'anchors':anchors,'arms':arms_used}))
