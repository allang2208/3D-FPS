"""Create four new material props and their production icons, without changing old assets."""
from pathlib import Path
import json, math, sys
import bpy, bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/CraftingMaterialTiers20261026'
ROWS=json.loads((OUT/'materials.json').read_text(encoding='utf-8'))
for folder in ('Export','Icons','Blends'): (OUT/folder).mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools/AssetPipeline'))
from collection_icon_orientation import orient_collection_camera
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=768;scene.render.resolution_y=384;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.45,.48,.52,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for name,at,power,size in [('Key',(-.30,-.35,.55),6,.48),('Fill',(.25,.2,.25),2.5,.38),('Rim',(-.15,.35,.35),4,.32)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=at;aim(o,(0,0,0))
d=bpy.data.cameras.new('ProductionIcon');camera=bpy.data.objects.new('ProductionIcon',d);scene.collection.objects.link(camera)
camera.data.type='ORTHO';scene.camera=camera

def surface(c):
    m=bpy.data.materials.new('M_'+c['key']);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Metallic'].default_value=1 if c['family']=='metal' else 0
    bs.inputs['Roughness'].default_value=c['roughness']
    tc=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
    l.new(tc.outputs['Object'],scale.inputs[0]);scale.inputs[1].default_value=(9,650,650) if c['family']=='metal' else (9,160,160)
    fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=1;fine.inputs['Detail'].default_value=2
    l.new(scale.outputs['Vector'],fine.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.15;ramp.color_ramp.elements[0].color=(*c['low'],1)
    ramp.color_ramp.elements[1].position=.85;ramp.color_ramp.elements[1].color=(*c['high'],1)
    if c['family']=='wood':
        offset=n.new('ShaderNodeVectorMath');offset.operation='ADD';offset.inputs[1].default_value=(0,.052,.027)
        l.new(tc.outputs['Object'],offset.inputs[0])
        wave=n.new('ShaderNodeTexWave');wave.wave_type='RINGS';wave.rings_direction='X';wave.inputs['Scale'].default_value=38*c['grain']
        wave.inputs['Distortion'].default_value=3.2*c['warp'];wave.inputs['Detail Scale'].default_value=.65
        l.new(offset.outputs['Vector'],wave.inputs['Vector']);l.new(wave.outputs['Fac'],ramp.inputs['Fac'])
        bs.inputs['Specular IOR Level'].default_value=.23
    else:
        l.new(fine.outputs['Fac'],ramp.inputs['Fac'])
    l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.00005
    l.new(fine.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    rough=n.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1
    rough.inputs['To Min'].default_value=c['roughness']-.035;rough.inputs['To Max'].default_value=c['roughness']+.055
    l.new(fine.outputs['Fac'],rough.inputs['Value']);l.new(rough.outputs['Result'],bs.inputs['Roughness'])
    return m

def bevel(obj,name,width,segments):
    mod=obj.modifiers.new(name,'BEVEL');mod.width=width;mod.segments=segments
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)

def metal(c):
    # Same 24 x 9 x 5 cm taper as the established ingot family.
    verts=[(-.12,-.045,-.025),(.12,-.045,-.025),(.12,.045,-.025),(-.12,.045,-.025),
           (-.095,-.034,.025),(.095,-.034,.025),(.095,.034,.025),(-.095,.034,.025)]
    faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh=bpy.data.meshes.new('Ingot solid');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new('Ingot',mesh);scene.collection.objects.link(obj);obj.select_set(True)
    bevel(obj,'Cast edge radius',.0022,5)
    for y in ([0] if c['grooves']==1 else [-.013,.013]):
        bpy.ops.mesh.primitive_cube_add(size=1,location=(0,y,.027))
        cut=bpy.context.object;cut.dimensions=(.142,.007,.008);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bevel(cut,'Rounded stamp',.0017,5)
        bpy.context.view_layer.objects.active=obj;mod=obj.modifiers.new('Pressed identification groove','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
    bevel(obj,'Soft stamp lip',.00045,3)
    for p in obj.data.polygons:p.use_smooth=p.area<.00015
    return obj

def wood(c):
    bpy.ops.mesh.primitive_cube_add(size=1);obj=bpy.context.object;obj.dimensions=(.30,.07,.05)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bevel(obj,'Planed edge',.0032,5)
    for v in obj.data.vertices:
        x,y,z=v.co
        if abs(x)<.146:
            v.co.y+=.00045*math.sin(x*54)*math.sin(z*62)
            v.co.z+=.00028*math.sin(x*70+1)*math.cos(y*65)
    obj.data.update()
    for p in obj.data.polygons:p.use_smooth=abs(p.normal.x)<.8 and p.area<.0002
    roles=obj.data.color_attributes.new(name='SurfaceRole',type='FLOAT_COLOR',domain='CORNER')
    for p in obj.data.polygons:
        for loop in p.loop_indices:roles.data[loop].color=(1 if abs(p.normal.x)>.7 else 0,0,0,1)
    return obj

records=[]
for c in ROWS:
    bpy.ops.object.select_all(action='DESELECT')
    obj=metal(c) if c['family']=='metal' else wood(c)
    obj.name=('SM_Ingot_' if c['family']=='metal' else 'SM_WoodCore_')+c['key'];obj.data.name=obj.name
    obj.data.materials.append(surface(c));bpy.context.view_layer.objects.active=obj
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    # Explicit authored UVs for interchange/tangent generation; fine relief stays procedural.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'Export'/f'{obj.name}.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False)
    camera.location=(.42,-.73,.47);aim(camera,(0,0,0));orient_collection_camera(camera,2,1,forward=(-1,0,0),dimensions=tuple(obj.dimensions))
    bpy.context.view_layer.update();points=[camera.matrix_world.inverted()@(obj.matrix_world@v.co) for v in obj.data.vertices]
    x0=min(p.x for p in points);x1=max(p.x for p in points);y0=min(p.y for p in points);y1=max(p.y for p in points)
    camera.location+=camera.matrix_world.to_3x3()@Vector(((x0+x1)/2,(y0+y1)/2,0));camera.data.ortho_scale=max(x1-x0,2*(y1-y0))/.88
    scene.render.filepath=str(OUT/'Icons'/f'{c["id"]}.png');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Blends'/f'{obj.name}.blend'))
    bpy.ops.render.render(write_still=True)
    records.append(dict(id=c['id'],mesh=obj.name,dimensions_cm=[round(x*100,3) for x in obj.dimensions],vertices=len(obj.data.vertices),polygons=len(obj.data.polygons),icon='768x384 RGBA, actual authored model, horizontal',model_route='Blender exact geometry; procedural PBR'))
    bpy.data.objects.remove(obj,do_unlink=True)
(OUT/'model-authoring.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('CRAFTING_MATERIAL_MODELS_SAVED',len(records))
