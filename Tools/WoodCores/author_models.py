"""Background authoring of four solid timber billets and production inventory icons."""
from pathlib import Path
import json, math, sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/WoodCoreMaterials20261026'
for sub in ('Export','Icons','Blends'): (OUT/sub).mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools/AssetPipeline'))
from collection_icon_orientation import orient_collection_camera
CORES=[
 dict(id='wood_core_plain',name='原木芯',key='Plain',bonus=0,low=[.22,.105,.037],high=[.48,.285,.115],grain=1.,rough=.02,glow=0),
 dict(id='wood_core_iron',name='铁木芯',key='Iron',bonus=.02,low=[.065,.033,.018],high=[.21,.105,.047],grain=1.6,rough=-.015,glow=0),
 dict(id='wood_core_ancient',name='古树木芯',key='Ancient',bonus=.06,low=[.095,.048,.024],high=[.30,.16,.066],grain=.7,rough=.055,glow=0),
 dict(id='wood_core_spirit',name='灵纹木芯',key='Spirit',bonus=.10,low=[.065,.095,.071],high=[.23,.31,.21],grain=1.15,rough=.025,glow=.12),
]
(OUT/'cores.json').write_text(json.dumps(CORES,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=768;scene.render.resolution_y=384;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.38,.43,.48,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35

def aim(obj,at):obj.rotation_euler=(Vector(at)-obj.location).to_track_quat('-Z','Y').to_euler()
for name,at,power,size in [('Key',(-.35,-.4,.55),45,.5),('Fill',(.3,.25,.25),20,.4),('Edge',(-.15,.3,.4),30,.25)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=at;aim(obj,(0,0,0))
camdata=bpy.data.cameras.new('IconCamera');camera=bpy.data.objects.new('IconCamera',camdata);scene.collection.objects.link(camera)
camera.location=(.43,-.75,.48);aim(camera,(0,0,0));camera.data.type='ORTHO';scene.camera=camera
orient_collection_camera(camera,2,1,forward=(-1,0,0),dimensions=(.30,.07,.05))

def material(c):
 m=bpy.data.materials.new('Wood_'+c['key']);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
 bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.77+c['rough']
 tc=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(.30,8*c['grain'],8*c['grain']);l.new(tc.outputs['Generated'],mapping.inputs[0])
 wave=n.new('ShaderNodeTexWave');wave.wave_type='RINGS';wave.rings_direction='X';wave.inputs['Scale'].default_value=4;wave.inputs['Distortion'].default_value=3;wave.inputs['Detail Scale'].default_value=.8;l.new(mapping.outputs['Vector'],wave.inputs['Vector'])
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.20;ramp.color_ramp.elements[0].color=(*c['low'],1);ramp.color_ramp.elements[1].position=.78;ramp.color_ramp.elements[1].color=(*c['high'],1);l.new(wave.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
 fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=65;fine.inputs['Detail'].default_value=2;l.new(mapping.outputs['Vector'],fine.inputs['Vector'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.00012;l.new(fine.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
 if c['glow']:
  glow=n.new('ShaderNodeMath');glow.operation='GREATER_THAN';glow.inputs[1].default_value=.985;l.new(wave.outputs['Fac'],glow.inputs[0]);l.new(glow.outputs[0],bs.inputs['Emission Strength']);bs.inputs['Emission Color'].default_value=(.018,.08,.045,1)
 return m

records=[]
for index,c in enumerate(CORES):
 bpy.ops.mesh.primitive_cube_add(size=1)
 obj=bpy.context.object;obj.name='SM_WoodCore_'+c['key'];obj.dimensions=(.30,.07,.05)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel=obj.modifiers.new('Worked soft edges','BEVEL');bevel.width=.0032;bevel.segments=5
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 # A solid billet with shallow hand-planed variations; no open end caps.
 for v in obj.data.vertices:
  x,y,z=v.co
  if abs(x)<.146:
   v.co.y+=.00055*math.sin(x*53+index)*math.sin(z*65)
   v.co.z+=.00032*math.sin(x*72+index)*math.cos(y*70)
 obj.data.update()
 for p in obj.data.polygons:p.use_smooth=abs(p.normal.x)<.8 and p.area<.0002
 attr=obj.data.color_attributes.new(name='SurfaceRole',type='FLOAT_COLOR',domain='CORNER')
 for poly in obj.data.polygons:
  for loop in poly.loop_indices:attr.data[loop].color=(1 if abs(poly.normal.x)>.7 else 0,0,0,1)
 obj.data.materials.append(material(c))
 bpy.context.view_layer.objects.active=obj;obj.select_set(True)
 bpy.ops.export_scene.fbx(filepath=str(OUT/'Export'/f'{obj.name}.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False)
 bpy.context.view_layer.update()
 points=[camera.matrix_world.inverted()@(obj.matrix_world@v.co) for v in obj.data.vertices]
 x0=min(p.x for p in points);x1=max(p.x for p in points);y0=min(p.y for p in points);y1=max(p.y for p in points)
 camera.location+=camera.matrix_world.to_3x3()@Vector(((x0+x1)/2,(y0+y1)/2,0))
 camera.data.ortho_scale=max(x1-x0,2*(y1-y0))/.88
 scene.render.filepath=str(OUT/'Icons'/f'{c["id"]}.png')
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Blends'/f'WoodCore_{c["key"]}.blend'))
 bpy.ops.render.render(write_still=True)
 records.append(dict(id=c['id'],mesh=obj.name,dimensions_cm=[30,7,5],vertices=len(obj.data.vertices),polygons=len(obj.data.polygons),material='procedural volume grain, roughness and micro-bump',icon='actual model, horizontal 2x1, transparent'))
 bpy.data.objects.remove(obj,do_unlink=True)
(OUT/'model-authoring.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
