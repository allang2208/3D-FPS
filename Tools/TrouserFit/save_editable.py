"""Packed native-rig source, FBX delivery, and production inventory thumbnails."""
import json
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TrouserFit20261018';(R/'Exports').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
def constant(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
def textured(name,root,prefix,repeat=(4,4),tint=(1,1,1)):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];uv=n.new('ShaderNodeTexCoord');mul=n.new('ShaderNodeVectorMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=(*repeat,1);l.new(uv.outputs['UV'],mul.inputs[0])
    for channel in ('BaseColor','Normal','ORM'):
        img=bpy.data.images.load(str(root/(prefix+channel+'.png')),check_existing=True)
        if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
        t=n.new('ShaderNodeTexImage');t.image=img;l.new(mul.outputs[0],t.inputs['Vector'])
        if channel=='BaseColor':
            scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=tint;l.new(t.outputs['Color'],scale.inputs[0]);l.new(scale.outputs[0],p.inputs['Base Color'])
        elif channel=='Normal':
            nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
        else:
            sp=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sp.inputs[0]);l.new(sp.outputs['Green'],p.inputs['Roughness']);l.new(sp.outputs['Blue'],p.inputs['Metallic'])
    return m
leather=P/'SourceAssets/BrownLeatherSet20261004/Textures';mail=P/'SourceAssets/ChainmailInterlace20260929/Textures';steel=P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2/Textures'
materials={
 'ue_leather_pants':[constant('Aged steel',(.105,.113,.12),.55,1),textured('Brown leather',leather,'T_BrownLeather_'),constant('Unused sole',(.03,.03,.03),.8),constant('Waxed thread',(.14,.11,.073),.8),textured('Leather reinforcement',leather,'T_BrownLeather_',tint=(.83,.80,.77))],
 'ue_chainmail_pants':[textured('Interlaced steel rings',mail,'T_ChainmailRelief_',repeat=(.25/.048,.25/.0176)),textured('Forged steel',steel,'T_ChainmailPants_Steel_'),constant('Charcoal lining',(.028,.033,.038),.82)]}
rows=[x for x in json.loads((R/'fit_inventory.json').read_text())['paths'] if x['action']=='tailored'];bones=json.loads(Path(rows[0]['output']).read_text())['bones'];reflect=Matrix.Diagonal((1,-1,1))
arm=bpy.data.armatures.new('Jason_NativeRig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in bones:
    eb=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflect@axes@reflect).to_4x4();matrix.translation=reflect@Vector(b['position'])*.01;eb.matrix=matrix;eb.length=.025
for b in bones:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[bones[b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);models={};standards={}
for row in rows:
    file=Path(row['output']);d=json.loads(file.read_text());name=file.stem;mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    for mat in materials[row['item']]:mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='Physical25cm')
    for fi,poly in enumerate(mesh.polygons):
        poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
        for ci,li in enumerate(poly.loop_indices):u,v=d['uv'][fi][ci];uv.data[li].uv=(u,1-v)
    mesh.normals_split_custom_set([(x,-y,z) for face in d['normals'] for x,y,z in face]);ids={i for ws in d['weights'] for i,w in ws};groups={i:ob.vertex_groups.new(name=bones[i]['name']) for i in ids}
    for vi,ws in enumerate(d['weights']):
        for bi,w in ws:groups[bi].add([vi],w,'REPLACE')
    ob.parent=rig;ob.modifiers.new('Native skinning','ARMATURE').object=rig;ob['SourceJSON']=str(file);ob['Parts']=json.dumps(d['parts']);ob['FitContract']=d['contract']
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
    ob.hide_set(True);ob.hide_render=True;models[name]=ob
    if 'standard' in row['uses']:standards[row['item']]=ob
standards['ue_leather_pants'].hide_set(False);standards['ue_leather_pants'].hide_render=False
bpy.context.scene['Production']='TrouserNativeWaist20261018; original family textures and native binding';bpy.context.scene['RuntimeTested']=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Tailored_Trousers_Editable.blend'))
# Update only inventory products, no game or acceptance views.
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=40;sc.render.resolution_x=320;sc.render.resolution_y=480;sc.render.resolution_percentage=100;sc.render.film_transparent=True;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.view_settings.view_transform='Standard';sc.view_settings.exposure=-.4
world=bpy.data.worlds.new('ProductStudio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.24,.28,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35;sc.world=world
for name,pos,power in [('Key',(-1.2,-1.2,1.8),150),('Fill',(1.2,-.8,.6),85),('Rim',(.1,1.1,1.5),110)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=1.;ob=bpy.data.objects.new(name,light);sc.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.56))-ob.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('InventoryCamera');camera.type='ORTHO';camera.ortho_scale=1.;cam=bpy.data.objects.new(camera.name,camera);sc.collection.objects.link(cam);sc.camera=cam;cam.location=(0,-3,.56);cam.rotation_euler=(Vector((0,0,.56))-cam.location).to_track_quat('-Z','Y').to_euler()
for item,ob in standards.items():
    for other in models.values():other.hide_render=True;other.hide_set(True)
    ob.hide_render=False;ob.hide_set(False);sc.render.filepath=str(R/(item+'.png'));bpy.ops.render.render(write_still=True)
(R/'editable_receipt.json').write_text(json.dumps(dict(blend=str(R/'Tailored_Trousers_Editable.blend'),fbx=[str(p) for p in (R/'Exports').glob('*.fbx')],icons=[item+'.png' for item in standards],runtime_tested=False),indent=2));print('TAILORED_TROUSERS_EDITABLE_SAVED',flush=True)
