"""Save native-rig Blend/FBX and produce inventory icons from the actual models."""
import json,math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerSet20261018'
bpy.ops.wm.read_factory_settings(use_empty=True)
def constant(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
def fabric(name,prefix,root=R/'Textures'):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
    uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=4;l.new(uv.outputs['UV'],scale.inputs[0])
    for channel in ('BaseColor','Normal','ORM'):
        img=bpy.data.images.load(str(root/(prefix+channel+'.png')),check_existing=True)
        if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
        t=n.new('ShaderNodeTexImage');t.image=img;l.new(scale.outputs[0],t.inputs['Vector'])
        if channel=='BaseColor':l.new(t.outputs['Color'],p.inputs['Base Color'])
        elif channel=='Normal':
            nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
        else:
            sp=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sp.inputs[0]);l.new(sp.outputs['Green'],p.inputs['Roughness']);l.new(sp.outputs['Blue'],p.inputs['Metallic'])
    return m
mats=[constant('ST6 Gunmetal',(.045,.052,.055),.5,1),fabric('ST6 Gray Ripstop','T_ST6_Fabric_'),fabric('ST6 Black Rubber and Hard Shell','T_ST6_Rubber_'),constant('ST6 Stitch Thread',(.12,.10,.067),.82),fabric('ST6 Khaki Leather','T_ST6_Khaki_'),fabric('ST6 Black Stretch and Nylon','T_ST6_Stretch_'),constant('Native skin reference only - original UE skin retained',(.38,.23,.16),.55)]
capri_mats=[constant('Capri metal',(.065,.073,.075),.57,1),fabric('Capri cotton','T_SmokeGreyTwill_',P/'SourceAssets/SmokeGreyCapri20261004/Textures'),constant('Unused',(.1,.1,.1),.8),constant('Capri thread',(.067,.070,.062),.88),fabric('Capri facing','T_SmokeGreyTwill_',P/'SourceAssets/SmokeGreyCapri20261004/Textures')]
native=json.loads((R/'native_reference.json').read_text());bones=native['bones'];reflect=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new('Jason_NativeRig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in bones:
    eb=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflect@axes@reflect).to_4x4();matrix.translation=reflect@Vector(b['position'])*.01;eb.matrix=matrix;eb.length=.025
for b in bones:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[bones[b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
models={}
def make(name,data,materials):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in data['positions']],[],data['triangles']);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    for m in materials:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='UVMap')
    for fi,poly in enumerate(mesh.polygons):
        poly.material_index=data['triangle_materials'][fi];poly.use_smooth=True
        for j,li in enumerate(poly.loop_indices):u,v=data['uv'][fi][j];uv.data[li].uv=(u,1-v)
    mesh.normals_split_custom_set([(x,-y,z) for face in data['normals'] for x,y,z in face])
    ids={i for ws in data['weights'] for i,w in ws};groups={i:ob.vertex_groups.new(name=bones[i]['name']) for i in ids}
    for vi,ws in enumerate(data['weights']):
        for bi,w in ws:groups[bi].add([vi],w,'REPLACE')
    ob.parent=rig;ob.modifiers.new('Native skinning','ARMATURE').object=rig;ob.hide_render=True;ob.hide_set(True);return ob
for name in ('Jason_ST6Trousers','Jason_ST6Trousers_ShortBootsFit','Jason_ST6Trousers_HighBootsFit','Jason_ST6Trousers_ST6BootsFit','Jason_ST6Boots'):
    d=json.loads((R/(name+'.json')).read_text());models[name]=make(name,d,mats)
for name in ('Jason_ST6Trousers_Garment','Jason_ST6Boots_Garment'):
    models[name]=make(name,json.loads((R/(name+'.json')).read_text()),mats)
models['Capri_Tailored']=make('Capri_Tailored',json.loads((P/'SourceAssets/SmokeGreyCapri20261004/Jason_SmokeGreyCapri_Garment.json').read_text()),capri_mats)
for name,ob in models.items():
    if name.endswith('_Garment') or name=='Capri_Tailored':continue
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
    ob.hide_set(True)
high=bpy.data.collections.new('BAKE_ONLY_SurfaceFields');bpy.context.scene.collection.children.link(high);high.hide_render=True;high.hide_viewport=True
for name in ('Fabric','Khaki','Rubber','Stretch'):
    d=np.load(R/f'HIGH_{name}.npz');h=d['height_cm'][::4,::4];n=len(h);span=float(d['span_cm']);mesh=bpy.data.meshes.new('HIGH_'+name)
    mesh.from_pydata([(x/(n-1)*span*.01,y/(n-1)*span*.01,float(h[y,x])*.01) for y in range(n) for x in range(n)],[],[(y*n+x,y*n+x+1,(y+1)*n+x+1,(y+1)*n+x) for y in range(n-1) for x in range(n-1)])
    ob=bpy.data.objects.new(mesh.name,mesh);high.objects.link(ob);ob['Usage']='Surface height authoring source; exclude from game exports'
for name in ('Jason_ST6Trousers_ST6BootsFit','Jason_ST6Boots'):models[name].hide_set(False);models[name].hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'ST6_LowerSet_Editable.blend'))
# Only the required inventory icons are rendered. No automatic acceptance views.
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=48;sc.render.resolution_x=320;sc.render.resolution_y=480;sc.render.resolution_percentage=100;sc.render.film_transparent=True;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.view_settings.view_transform='Standard';sc.view_settings.exposure=-.4
world=bpy.data.worlds.new('ProductStudio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.24,.28,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35;sc.world=world
for name,pos,power in [('Key',(-1.2,-1.2,1.8),150),('Fill',(1.2,-.8,.6),85),('Rim',(.1,1.1,1.5),110)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=1.;ob=bpy.data.objects.new(name,light);sc.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.5))-ob.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('InventoryCamera');camera.type='ORTHO';cam=bpy.data.objects.new('InventoryCamera',camera);sc.collection.objects.link(cam);sc.camera=cam
for key,name in [('ue_st6_tactical_pants','Jason_ST6Trousers_Garment'),('ue_st6_tactical_boots','Jason_ST6Boots_Garment'),('ue_smoke_grey_capri','Capri_Tailored')]:
    for ob in models.values():ob.hide_render=True;ob.hide_set(True)
    ob=models[name];ob.hide_render=False;ob.hide_set(False)
    if 'Boots' in name:
        # Single boot in the inventory; the saved wearable remains a pair.
        import bmesh
        duplicate=ob.copy();duplicate.data=ob.data.copy();bpy.context.collection.objects.link(duplicate);ob.hide_render=True
        bm=bmesh.new();bm.from_mesh(duplicate.data);bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x<0],context='VERTS');bm.to_mesh(duplicate.data);bm.free();ob=duplicate
        target=Vector((.145,0,.14));cam.location=(.85,-1.3,.65);camera.ortho_scale=.45
    else:target=Vector((0,0,.57 if 'ST6' in name else .65));cam.location=(0,-3,target.z);camera.ortho_scale=.97 if 'ST6' in name else .79
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(R/(key+'.png'));bpy.ops.render.render(write_still=True)
    if 'Boots' in name:bpy.data.objects.remove(ob,do_unlink=True)
(R/'editable_receipt.json').write_text(json.dumps(dict(blend=str(R/'ST6_LowerSet_Editable.blend'),fbx=[str(x) for x in (R/'Exports').glob('*.fbx')],icons=['ue_st6_tactical_pants.png','ue_st6_tactical_boots.png','ue_smoke_grey_capri.png'],runtime_tested=False),indent=2))
print('ST6_EDITABLE_EXPORTS_AND_ICONS_SAVED',flush=True)
