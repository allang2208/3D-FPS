"""Blender: editable native rigs, matching pickup FBX and production inventory icon."""
import json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
OUT=ROOT/'Editable';OUT.mkdir(exist_ok=True)
SCAN=P/'SourceAssets/HandEquipmentAppearance/Source'
reflection=Matrix.Diagonal((1,-1,1))
def material():
    mat=bpy.data.materials.new('FingerlessHunt_Leather');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bsdf=nodes.get('Principled BSDF');bsdf.inputs['Specular IOR Level'].default_value=.28
    for suffix,space,socket in [('BaseColor','sRGB','Base Color'),('Roughness','Non-Color','Roughness'),('Normal','Non-Color','Normal')]:
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(SCAN/f'Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_{suffix}.jpg'),check_existing=True)
        tex.image.colorspace_settings.name=space
        if suffix=='Normal':
            n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.85;links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bsdf.inputs[socket])
        elif suffix=='Roughness':
            n=nodes.new('ShaderNodeMath');n.operation='MULTIPLY_ADD';n.inputs[1].default_value=.38;n.inputs[2].default_value=.33
            links.new(tex.outputs['Color'],n.inputs[0]);links.new(n.outputs[0],bsdf.inputs[socket])
        else:links.new(tex.outputs['Color'],bsdf.inputs[socket])
    return mat
def mesh_object(d):
    mesh=bpy.data.meshes.new(d['profile']+'_FingerlessHuntV2')
    mesh.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in d['positions']],[],d['triangles']);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
    mesh.materials.append(material())
    for field,name in [('uv','LeatherMetric25cm'),('uv1','PalmAndEdgeDistance'),('uv2','StitchArcAndLining')]:
        layer=mesh.uv_layers.new(name=name)
        for face,uv in zip(mesh.polygons,d[field]):
            for loop,(u,v) in zip(face.loop_indices,uv):layer.data[loop].uv=(u,1-v) if field=='uv' else (u,v)
    mesh.uv_layers.active_index=0
    for i,l in enumerate(mesh.uv_layers):l.active_render=i==0
    ns=[]
    for face,normals in zip(mesh.polygons,d['normals']):
        face.use_smooth=True
        ns.extend((n[0],-n[1],n[2]) for n in normals)
    mesh.normals_split_custom_set(ns)
    return obj
entries=json.loads((ROOT/'manifest.json').read_text())
for entry in ([] if '--presentation-only' in sys.argv else entries):
    d=json.loads(Path(entry['authored']).read_text());name=d['profile'];bpy.ops.wm.read_factory_settings(use_empty=True)
    arm=bpy.data.armatures.new(name+'_NativeReference');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    by_id={b['index']:n for n,b in d['bones'].items()}
    for n,b in d['bones'].items():
        bone=arm.edit_bones.new(n);axes=Matrix(b['axes']).transposed()
        for k in range(3):axes.col[k]=axes.col[k].normalized()
        matrix=(reflection@axes@reflection).to_4x4();matrix.translation=reflection@Vector(b['position'])*.01;bone.matrix=matrix;bone.length=.025
    for n,b in d['bones'].items():
        if b['parent'] in by_id:arm.edit_bones[n].parent=arm.edit_bones[by_id[b['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT');obj=mesh_object(d);obj.parent=rig
    mod=obj.modifiers.new('NativeBinding','ARMATURE');mod.object=rig
    for n in sorted({n for w in d['weights'] for n in w}):obj.vertex_groups.new(name=n)
    for vi,w in enumerate(d['weights']):
        for n,v in w.items():obj.vertex_groups[n].add([vi],v,'REPLACE')
    obj['Contract']=d['contract'];obj['UEBindingSource']=d['binding_source'];obj['UE_shader_source']='Tools/ModularOutfit/fingerless_hunt_leather_v2.hlsl'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{name}_FingerlessHuntV2.blend'))
    print('FINGERLESS_BLEND_SAVED',name,flush=True)

# Inventory/drop presentation is the empty leather shell, without a mannequin.
bpy.ops.wm.read_factory_settings(use_empty=True);presentation=ROOT/'PresentationM4.json';d=json.loads((presentation if presentation.exists() else ROOT/'Authored/M4.json').read_text());obj=mesh_object(d)
anatomy=json.loads((P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json').read_text())['anatomy']
for vi,v in enumerate(obj.data.vertices):
    w=d['weights'][vi];side='l' if sum(value for key,value in w.items() if key.endswith('_l'))>.5 else 'r'
    f=anatomy[side];p=Vector(d['positions'][vi])-Vector(f['wrist'])
    v.co=Vector((p.dot(Vector(f['across']))*.01+(-.065 if side=='l' else .065),p.dot(Vector(f['forward']))*.01-.045,p.dot(Vector(f['dorsal']))*.01))
obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops));obj.data.update()
obj.name='SM_FingerlessHunt_Pickup';bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SM_FingerlessHunt_Pickup.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=320;scene.render.resolution_y=320;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.7,.75,.85,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
def point(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for loc,energy,size in [((-.2,-.15,.4),35,.30),((.25,.05,.20),18,.22)]:
    light=bpy.data.lights.new('Softbox','AREA');light.energy=energy;light.shape='DISK';light.size=size
    o=bpy.data.objects.new(light.name,light);bpy.context.collection.objects.link(o);o.location=loc;point(o,(0,0,0))
cam=bpy.data.cameras.new('CatalogCamera');cam.type='ORTHO';cam.ortho_scale=.265
o=bpy.data.objects.new('CatalogCamera',cam);bpy.context.collection.objects.link(o);o.location=(0,-.18,.34);point(o,(0,.005,0));scene.camera=o
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
icon=P/'Content/ColdSteelData/Icons/ModularOutfit20260924/ue_field_gloves_fingerless.png';scene.render.filepath=str(icon)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FingerlessHunt_Pickup.blend'))
# Catalog icons have their own vertical framing and exposure authoring pass.
# Re-exporting this model must not restore the obsolete overexposed icon.
import runpy
runpy.run_path(str(P/'Tools/ModularOutfit/render_field_glove_icons.py'),init_globals=dict(ONLY_ITEMS={'ue_field_gloves'}))
(ROOT/'presentation.json').write_text(json.dumps(dict(fbx=str(ROOT/'SM_FingerlessHunt_Pickup.fbx'),icon=str(icon),editable_profiles=len(entries)),indent=2)+'\n')
print('FINGERLESS_PRESENTATION_SAVED',flush=True)
