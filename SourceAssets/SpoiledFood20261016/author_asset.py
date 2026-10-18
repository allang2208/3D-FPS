"""Author a compact spoiled-food scrap pile, bake PBR, export, render inventory icon.
All geometry/materials are authored locally; no external generator output is used.
The icon render is requested production artwork, not a gameplay acceptance run.
"""
import bpy, json, math, random
from pathlib import Path
from mathutils import Vector, noise

OUT=Path(__file__).resolve().parent
random.seed(10162026)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'

parts=[]
def lump(name,center,radii,seed,tear=False):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5,radius=1)
    ob=bpy.context.object;ob.name=name
    offset=Vector((seed,seed*.317,seed*.713))
    for v in ob.data.vertices:
        p=v.co.copy()
        broad=noise.noise_vector(p*3.4+offset)
        fine=noise.noise(p*31+offset)
        p+=broad*.12+p*(fine*.025)
        if tear:
            # Flatten and rag the broken end instead of making a smooth pebble.
            if p.x>.25:
                p.x=.25+(p.x-.25)*.28+noise.noise(p*16+offset)*.09
            p.z+=.09*math.sin(p.x*5+p.y*4)
        v.co=Vector((p.x*radii[0],p.y*radii[1],p.z*radii[2]))+Vector(center)
    parts.append(ob)

lump('Collapsed fibrous food core',(0,0,.025),(.058,.038,.025),1,True)
lump('Torn bread-like scrap',(-.032,.013,.046),(.031,.029,.025),8,True)
lump('Collapsed soft scrap',(.033,.005,.019),(.035,.031,.020),17,True)
lump('Loose decayed morsel',(-.046,-.025,.013),(.024,.020,.014),23,True)
lump('Small attached crumb',(.021,-.028,.014),(.025,.018,.013),31,True)

# User revision: only compact chunks; no ribbons, strings or projecting strips.

bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
obj=bpy.context.object;obj.name='SM_SpoiledFood'
# Bound the pile to a hand-sized 14 cm item; origin sits on its resting surface.
coords=[v.co for v in obj.data.vertices]
low=Vector([min(v[i] for v in coords) for i in range(3)])
high=Vector([max(v[i] for v in coords) for i in range(3)])
factor=.14/(high.x-low.x);center=(low+high)*.5;center.z=low.z
for v in obj.data.vertices:v.co=(v.co-center)*factor
for p in obj.data.polygons:p.use_smooth=True
# Keep an editable surface master, then budget the small world pickup.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SpoiledFood_GeometryMaster.blend'))
dec=obj.modifiers.new('Pickup surface budget','DECIMATE');dec.ratio=.4
bpy.ops.object.modifier_apply(modifier=dec.name)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.015)
bpy.ops.object.mode_set(mode='OBJECT')

mat=bpy.data.materials.new('M_SpoiledFood_Author');mat.use_nodes=True
obj.data.materials.clear();obj.data.materials.append(mat)
nodes=mat.node_tree.nodes;links=mat.node_tree.links
shader=nodes.get('Principled BSDF');output=nodes.get('Material Output')
shader.inputs['Metallic'].default_value=0;shader.inputs['Specular IOR Level'].default_value=.27
coord=nodes.new('ShaderNodeTexCoord')
def texture(name,scale,detail=3):
    n=nodes.new('ShaderNodeTexNoise');n.name=name;n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=detail
    links.new(coord.outputs['Generated'],n.inputs['Vector']);return n
def ramp(name,source,entries):
    n=nodes.new('ShaderNodeValToRGB');n.name=name;r=n.color_ramp;r.elements.remove(r.elements[1])
    for i,(position,color) in enumerate(entries):
        e=r.elements[0] if i==0 else r.elements.new(position);e.position=position;e.color=(*color,1)
    links.new(source,n.inputs['Fac']);return n

decay=texture('Brown decomposed flesh and stale crumb',6,4)
base=ramp('Muted organic decay',decay.outputs['Fac'],[(.15,(.032,.018,.010)),(.34,(.083,.045,.021)),(.49,(.16,.10,.045)),(.65,(.25,.19,.105)),(.82,(.34,.30,.19))])
colonies=texture('Irregular mold colony boundaries',9,4)
mask=ramp('Patchy colony coverage',colonies.outputs['Fac'],[(.46,(0,0,0)),(.56,(0,0,0)),(.61,(1,1,1))])
spores=texture('Granular mold microstructure',145,2)
mold=ramp('Dull sage olive and chalk mold',spores.outputs['Fac'],[(.2,(.055,.085,.038)),(.42,(.15,.20,.10)),(.59,(.31,.36,.22)),(.77,(.54,.55,.39))])
mix=nodes.new('ShaderNodeMixRGB');links.new(mask.outputs['Color'],mix.inputs[0]);links.new(base.outputs['Color'],mix.inputs[1]);links.new(mold.outputs['Color'],mix.inputs[2]);links.new(mix.outputs[0],shader.inputs['Base Color'])
rough=nodes.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.47;rough.inputs['To Max'].default_value=.94
links.new(mask.outputs['Color'],rough.inputs['Value']);links.new(rough.outputs['Result'],shader.inputs['Roughness'])
grain=texture('Torn crumb pores and fibers',72,4)
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.42;bump.inputs['Distance'].default_value=.0011
links.new(grain.outputs['Fac'],bump.inputs['Height'])
micro=nodes.new('ShaderNodeBump');micro.inputs['Strength'].default_value=.27;micro.inputs['Distance'].default_value=.00024
links.new(spores.outputs['Fac'],micro.inputs['Height']);links.new(bump.outputs['Normal'],micro.inputs['Normal']);links.new(micro.outputs['Normal'],shader.inputs['Normal'])

scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12
scene.render.bake.margin=16;scene.render.bake.use_clear=True
target=nodes.new('ShaderNodeTexImage');target.name='PBR bake target'
def bake(suffix,kind):
    image=bpy.data.images.new('T_SpoiledFood_'+suffix,width=2048,height=2048,alpha=False)
    image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
    target.image=image
    for n in nodes:n.select=False
    target.select=True;nodes.active=target
    bpy.ops.object.bake(type=kind)
    image.filepath_raw=str(OUT/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
    print('BAKED',suffix,flush=True);return image

normal=bake('NormalGL','NORMAL')
emit=nodes.new('ShaderNodeEmission');links.new(emit.outputs[0],output.inputs['Surface'])
links.new(rough.outputs['Result'],emit.inputs['Color']);roughmap=bake('Roughness','EMIT')
links.new(mix.outputs[0],emit.inputs['Color']);color=bake('BaseColor','EMIT')
links.new(shader.outputs[0],output.inputs['Surface']);nodes.remove(emit)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SpoiledFood_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_SpoiledFood.fbx'),use_selection=True,object_types={'MESH'},
    add_leaf_bones=False,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,use_mesh_modifiers=True)

# Render the requested transparent inventory icon from the exported pickup mesh.
def aim(ob,point):ob.rotation_euler=(point-ob.location).to_track_quat('-Z','Y').to_euler()
points=[obj.matrix_world@v.co for v in obj.data.vertices];center=sum(points,Vector())/len(points)
if scene.world is None:scene.world=bpy.data.worlds.new('Inventory studio world')
scene.world.color=(.16,.16,.16)
for name,location,power,size in [('Key',(-.20,-.24,.34),3,.25),('Fill',(.25,-.05,.18),1.5,.22),('Rim',(.03,.23,.29),2.5,.20)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=center+Vector(location);aim(ob,center)
cam=bpy.data.objects.new('Inventory camera',bpy.data.cameras.new('Inventory camera'));scene.collection.objects.link(cam)
cam.location=center+Vector((.17,-.27,.25));cam.data.type='ORTHO';aim(cam,center);scene.camera=cam
bpy.context.view_layer.update();projected=[cam.matrix_world.inverted()@p for p in points]
width=max(p.x for p in projected)-min(p.x for p in projected);height=max(p.y for p in projected)-min(p.y for p in projected)
cam.data.ortho_scale=max(width,height)/.85
shift=Vector(((max(p.x for p in projected)+min(p.x for p in projected))/2,(max(p.y for p in projected)+min(p.y for p in projected))/2,0))
cam.location+=cam.matrix_world.to_3x3()@shift
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.8;scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.filepath=str(OUT/'spoiled_food.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SpoiledFood_Icon.blend'))
obj.data.calc_loop_triangles()
report={'mesh':'SM_SpoiledFood.fbx','triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices),
    'dimensions_cm':[float(x*100) for x in obj.dimensions],'texture_size':[2048,2048],
    'maps':['T_SpoiledFood_BaseColor.png','T_SpoiledFood_Roughness.png','T_SpoiledFood_NormalGL.png'],
    'normal_convention':'OpenGL; flip green on UE import','icon':'spoiled_food.png','icon_size':[512,512],
    'source':'Local Blender geometry and procedural decay/mold PBR, seed 10162026',
    'structure':'Five compact irregular chunks only; no strips or strands',
    'remote_5080_used':False,'imagegen_used':False,'game_or_pie_run':False}
(OUT/'preparation.json').write_text(json.dumps(report,indent=2))
print('SPOILED_FOOD_AUTHORED',json.dumps(report),flush=True)
