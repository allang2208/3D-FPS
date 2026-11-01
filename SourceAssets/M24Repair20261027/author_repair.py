"""Restore glTF surface corners and export one consistent metric rig."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;SRC=O.parent/'M24CustomScope20261026'
X=O/'Exports';(X/'Animations').mkdir(parents=True,exist_ok=True)
original=json.loads((SRC/'gameplay_authoring.json').read_text())
reg=Matrix(json.loads((SRC/'authoring.json').read_text())['static_remix_to_source'])
C=Matrix.Rotation(math.pi,4,'Z')
bpy.ops.wm.open_mainfile(filepath=str(O/'OriginalGLTF_Reference.blend'),use_scripts=False)
surfaces={}
names={row[4:]:row for row in json.loads((O.parent/'M24Modular20261027/authoring.json').read_text())['source_parts']}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    name=next(n for n in names if ob.name.startswith(n+'_'))
    transform=C@reg@ob.matrix_world
    me=ob.data;normals=[(transform.to_3x3().inverted().transposed()@n.vector).normalized()[:] for n in me.corner_normals]
    surfaces[names[name]]={'vertices':[list(transform@v.co) for v in me.vertices],
      'faces':[list(p.vertices) for p in me.polygons],'normals':normals,
      'uvs':{uv.name:[list(x.uv) for x in uv.data] for uv in me.uv_layers}}
bpy.ops.wm.open_mainfile(filepath=str(SRC/'M24_V9_Gameplay_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
r.animation_data_clear();r.matrix_world=Matrix.Identity(4);r.scale=(1,1,1)
for p in r.pose.bones:p.matrix_basis=Matrix.Identity(4)
s.frame_set(0);bpy.context.view_layer.update()
report={'source':'original selected glTF corner UVs/normals, existing V9 animation curves',
        'rig_object_scale':list(r.scale),'surface_repair':{},'mesh':str(X/'SK_M24_RepairedV9.fbx'),
        'clips':{},'models':{},'sockets_source':original['markers']}
for name,row in surfaces.items():
    ob=bpy.data.objects[name];mats=list(ob.data.materials);group=ob.vertex_groups[0].name
    previous=len(ob.data.vertices)
    me=bpy.data.meshes.new(name+'_glTF_Corners');me.from_pydata(row['vertices'],[],row['faces']);me.update()
    for mat in mats:me.materials.append(mat)
    for key,values in row['uvs'].items():
        uv=me.uv_layers.new(name=key)
        for dst,value in zip(uv.data,values):dst.uv=value
    for p in me.polygons:p.use_smooth=True
    me.normals_split_custom_set(row['normals'])
    ob.data=me;ob.vertex_groups.clear();ob.vertex_groups.new(name=group).add(list(range(len(me.vertices))),1,'REPLACE')
    ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    report['surface_repair'][name]={'previous_vertices':previous,'vertices':len(me.vertices),'triangles':sum(len(f)-2 for f in row['faces']),'uv0':me.uv_layers[0].name,'custom_normals':me.has_custom_normals}
# Preserve accepted hand surface normals as well as all V9 morphs/weights/UVs.
before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(SRC/'V9/M4_V9_Template.fbx'),use_anim=False)
added=[o for o in bpy.data.objects if o not in before]
template=next(o for o in added if o.type=='MESH');template_rig=next(o for o in added if o.type=='ARMATURE')
slots={i for i,m in enumerate(template.data.materials) if m and 'SkinV9' in m.name}
loops=[i for p in template.data.polygons if p.material_index in slots for i in p.loop_indices]
normal_matrix=(template_rig.matrix_world.inverted()@template.matrix_world).to_3x3().inverted().transposed()
skin.data.normals_split_custom_set([(normal_matrix@template.data.corner_normals[i].vector).normalized() for i in loops])
for ob in added:bpy.data.objects.remove(ob,do_unlink=True)
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
def export(path,obs,anim=False):
    select(obs);bpy.context.view_layer.update()
    assert all(abs(v-1)<1e-7 for v in r.scale),tuple(r.scale)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=anim,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
        mesh_smooth_type='FACE',use_tspace=True,use_mesh_modifiers=False)
for role,row in original['clips'].items():
    action=bpy.data.actions['A_M24_'+role];r.animation_data_create();r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    s.render.fps=30;s.frame_start=0;s.frame_end=round(row['duration']*30);s.frame_set(0)
    path=X/'Animations'/('A_M24_'+role+'.fbx');export(path,[r],True)
    report['clips'][role]={'file':str(path),'duration':row['duration']}
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis=Matrix.Identity(4)
s.frame_set(0)
mod=json.loads((O.parent/'M24Modular20261027/authoring.json').read_text())
removed=set(n for row in mod['models'].values() for n in row['objects'])
for key,row in mod['models'].items():
    copies=[]
    for n in row['objects']:
        ob=bpy.data.objects[n];copy=ob.copy();copy.data=ob.data.copy();s.collection.objects.link(copy)
        copy.parent=None;copy.matrix_world=Matrix.Identity(4);copy.modifiers.clear();copies.append(copy)
    select(copies);bpy.ops.object.join();part=bpy.context.object;part.name='SM_M24_'+key
    file=X/(part.name+'.fbx');export(file,[part])
    report['models'][key]={'file':str(file),'objects':row['objects'],'sockets_ue_cm':row['sockets_ue_cm']}
    bpy.data.objects.remove(part,do_unlink=True)
kept=[bpy.data.objects[n] for n in surfaces if n not in removed]
export(Path(report['mesh']),[r,skin,*kept])
r.animation_data.action=bpy.data.actions['A_M24_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=1;s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Repaired_Editable.blend'))
report['skin_morph_count']=len(skin.data.shape_keys.key_blocks)
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_REPAIR_EXPORTED',len(report['clips']),len(report['surface_repair']),flush=True)
