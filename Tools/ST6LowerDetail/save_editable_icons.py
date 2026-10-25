"""Save native-rig upgraded author sources and the two requested catalog icons."""
import bpy,bmesh,json,sys,importlib.util
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerDetail20261024'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def append(base,extra):
    offset=len(base['positions'])
    for k in ('positions','weights','uv','normals','triangle_materials'):base[k].extend(extra[k])
    base['triangles'].extend([[v+offset for v in t] for t in extra['triangles']])
    base['parts'].extend(dict(p,first_vertex=p['first_vertex']+offset) for p in extra['parts'])
    base['contract']+='; ST6LowerDetail20261024 additive detail revision';return base
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
families=['Gunmetal','Fabric','Rubber','Thread','Khaki','Stretch'];mats=[]
for family in families:
    m=bpy.data.materials.new('ST6 '+family);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=4;l.new(uv.outputs['UV'],scale.inputs[0])
    for channel in ('BaseColor','Normal','ORM'):
        im=bpy.data.images.load(str(R/'Textures'/f'T_ST6_{family}_{channel}.png'),check_existing=True)
        if channel!='BaseColor':im.colorspace_settings.name='Non-Color'
        t=n.new('ShaderNodeTexImage');t.image=im;l.new(scale.outputs[0],t.inputs['Vector'])
        if channel=='BaseColor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
        elif channel=='Normal':
            normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.8;l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
        else:
            sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    if family in ('Fabric','Stretch','Thread'):bs.inputs['Sheen Weight'].default_value=.15
    mats.append(m)
skin=bpy.data.materials.new('Native skin reference; UE retains native material');skin.diffuse_color=(.38,.23,.16,1);mats.append(skin)
native=read(R/'Inputs/native_reference.json');bones=native['bones'];reflect=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new('Jason_NativeRig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in bones:
    eb=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflect@axes@reflect).to_4x4();matrix.translation=reflect@Vector(b['position'])*.01;eb.matrix=matrix;eb.length=.025
for b in bones:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[bones[b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
def make(name,d):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    for m in mats:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='Physical25cm')
    for fi,poly in enumerate(mesh.polygons):
        poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
        for j,li in enumerate(poly.loop_indices):u,v=d['uv'][fi][j];uv.data[li].uv=(u,1-v)
    mesh.normals_split_custom_set([(x,-y,z) for face in d['normals'] for x,y,z in face])
    groups={i:ob.vertex_groups.new(name=bones[i]['name']) for i in {i for ws in d['weights'] for i,w in ws}}
    for vi,ws in enumerate(d['weights']):
        for bi,w in ws:groups[bi].add([vi],w,'REPLACE')
    ob.parent=rig;ob.modifiers.new('Native binding','ARMATURE').object=rig;ob.hide_render=True;ob.hide_set(True);return ob
models={};counts={}
for kind,label,suffixes in [('pants','ST6Trousers',('','_ShortBootsFit','_HighBootsFit','_ST6BootsFit')),('boots','ST6Boots',('',))]:
    for suffix in suffixes:
        name='Jason_'+label+suffix;d=append(read(R/'Inputs'/(name+'.json')),read(R/'Authored'/('Jason_'+kind+suffix+'.json')))
        (R/'Authored'/(name+'.json')).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
        ob=make(name,d);models[name]=ob
        bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE');ob.hide_set(True)
    d=append(read(R/'Inputs'/('Jason_'+label+'_Garment.json')),read(R/'Authored'/('Jason_'+kind+'.json')))
    (R/'Authored'/(kind+'_garment.json')).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');models[kind]=make('Display_'+kind,d);counts[kind]=len(d['triangles'])
high=bpy.data.collections.new('BAKE_ONLY_SurfaceFields');bpy.context.scene.collection.children.link(high);high.hide_render=True;high.hide_viewport=True
for family in families:
    data=np.load(R/f'HIGH_{family}.npz');step=max(1,len(data['height_cm'])//160);h=data['height_cm'][::step,::step];n=len(h);span=float(data['span_cm']);mesh=bpy.data.meshes.new('HIGH_'+family)
    mesh.from_pydata([(x/(n-1)*span*.01,y/(n-1)*span*.01,float(h[y,x])*.01) for y in range(n) for x in range(n)],[],[(y*n+x,y*n+x+1,(y+1)*n+x+1,(y+1)*n+x) for y in range(n-1) for x in range(n-1)])
    ob=bpy.data.objects.new(mesh.name,mesh);high.objects.link(ob);ob['Usage']='Original physical height field; exclude from runtime export'
for key in ('Jason_ST6Trousers_ST6BootsFit','Jason_ST6Boots'):models[key].hide_set(False);models[key].hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Exports/ST6_LowerDetail_Editable.blend'))
# Use the established studio/exposure calibration; 2x3 gear is 320x480 pixels.
path=P/'Tools/FieldHat/render_icon.py';spec=importlib.util.spec_from_file_location('st6_lower_inventory',str(path));icons=importlib.util.module_from_spec(spec);source=path.read_text(encoding='utf-8')
source=source.replace('world.use_nodes = True','world.use_nodes = True\n    world.node_tree.nodes.clear()\n    bg=world.node_tree.nodes.new("ShaderNodeBackground")\n    bg.name="Background"\n    output=world.node_tree.nodes.new("ShaderNodeOutputWorld")\n    world.node_tree.links.new(bg.outputs[0],output.inputs[0])')
source=source.replace('width = round(320 * item["grid_w"] / item["grid_h"])','width = 160 * item["grid_w"]').replace('height = 320','height = 160 * item["grid_h"]')
exec(compile(source,str(path),'exec'),icons.__dict__);icons.OUT=R
for kind in ('pants','boots'):
    key='ue_st6_tactical_'+kind;icons.FAMILIES[key]='ST6LowerDetail20261024';ob=models[kind]
    if kind=='boots':
        ob=ob.copy();ob.data=ob.data.copy();bpy.context.collection.objects.link(ob);bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x<0],context='VERTS');bm.to_mesh(ob.data);bm.free()
    icons.render_current(key,ob,item=dict(grid_w=2,grid_h=3,ue_icon='Icons/ST6LowerDetail20261024/'+key+'.png'),camera_offset=(0,-3,.10) if kind=='pants' else (2.1,-3,1.65))
(R/'authored.json').write_text(json.dumps(dict(completed=True,garment_triangles=counts,texture_maps=24,inventory_icons=True,preview_rendered=False,runtime_tested=False,base_interfaces_changed=False),indent=2),encoding='utf-8')
print('ST6_LOWER_EDITABLE_AND_ICONS_SAVED',counts,flush=True)
