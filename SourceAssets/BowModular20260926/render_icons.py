"""Produce installed-part icons and the catalog bow PNG from retained geometry."""
import bpy,math,json,shutil
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;ROOT=P.parents[1];OUT=P/'Icons';OUT.mkdir(exist_ok=True)
WOOD=P.parent/'DarkBow20260925/WoodLongbow20260925';SIGHT=P.parent/'BowWoodSight20260926'
bow=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8-sig'))['bow_dark']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
def append(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[name]
    o=b.objects[0];scene.collection.objects.link(o);o.data=o.data.copy()
    o.data.transform(Matrix.Scale(.01,4)@o.matrix_world);o.matrix_world=Matrix.Identity(4)
    o.hide_render=False;o.hide_viewport=False;o.hide_set(False);return o
body=append(P/'Bow_ModularParts.blend','SM_Bow_BodyModular')
grip=append(P/'Bow_ModularParts.blend','SM_Bow_GripWrap')
rest=append(P/'Bow_ModularParts.blend','SM_Bow_ArrowRestWood')
lined=append(P/'Bow_ModularParts.blend','SM_Bow_ArrowRestLined')
sight=append(SIGHT/'Bow_CarvedWoodSight.blend','SM_Bow_CarvedWoodSight')
def shader(m):return next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def constant(name,rgb,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=shader(m)
    p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Roughness'].default_value=rough;return m
def woodmat(name,carved=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=shader(m)
    images=[]
    for i in range(3):
        t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(WOOD/'Textures'/('Image_'+str(i)+'.png')),check_existing=True)
        t.image.colorspace_settings.name='sRGB' if i==0 else 'Non-Color';images.append(t)
    l.new(images[0].outputs['Color'],p.inputs['Base Color']);s=n.new('ShaderNodeSeparateColor');l.new(images[1].outputs['Color'],s.inputs['Color'])
    if carved:
        mx=n.new('ShaderNodeMath');mx.operation='MAXIMUM';mx.inputs[1].default_value=.42;l.new(s.outputs['Green'],mx.inputs[0]);l.new(mx.outputs[0],p.inputs['Roughness'])
    else:l.new(s.outputs['Green'],p.inputs['Roughness']);l.new(s.outputs['Blue'],p.inputs['Metallic'])
    nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.55 if carved else 1
    l.new(images[2].outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal']);return m
original=woodmat('Runtime_LongbowPBR');wood=woodmat('Runtime_CarvedWoodPBR',True)
linen=constant('Runtime_WaxedLinen',(.105,.068,.038),.84)
inlay=constant('Runtime_PaleWoodInlay',(.48,.31,.145),.60)
for o in [body,grip]:
    o.data.materials.clear();o.data.materials.append(original)
    for f in o.data.polygons:f.material_index=0
for o in [rest,lined,sight]:
    for i,m in enumerate(o.data.materials):
        o.data.materials[i]=linen if m.name.startswith(('ArrowRestLeather','WaxedLinen')) else inlay if m.name.startswith('PaleWoodInlay') else wood
def point(key):
    x,y,z=map(float,bow[key].split(','));return Vector((x,-y,z))*.01
stringmat=constant('Runtime_BowString',(.035,.026,.016),.74)
fastmat=constant('Runtime_FastString',(.17,.115,.06),.78)
strings=[]
def place_string(drawn=False,fast=False):
    for i,key in enumerate(['nock_upper_cm','nock_lower_cm']):
        a,b=point(key),point('draw_anchor_cm' if drawn else 'brace_nock_cm');d=b-a
        o=strings[i];o.location=(a+b)*.5;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized())
        o.scale=((.065 if fast else .09)*.01,)*2+(d.length,);o.data.materials.clear();o.data.materials.append(fastmat if fast else stringmat)
for key in ['upper','lower']:
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=1,depth=1);o=bpy.context.object;o.name='Runtime_String_'+key
    for f in o.data.polygons:f.use_smooth=True
    strings.append(o)
place_string();objects=[body,grip,rest,lined,sight]+strings
data=bpy.data.cameras.new('PartsCamera');data.type='ORTHO';data.clip_start=.001;data.clip_end=100
cam=bpy.data.objects.new('PartsCamera',data);scene.collection.objects.link(cam);scene.camera=cam
cam.location=(0,3,0);cam.rotation_euler=Vector((0,-1,0)).to_track_quat('-Z','Y').to_euler()
lights=[]
for name,offset,power,size in [('Key',(-1,1.4,1.5),55,2),('Fill',(1,1.3,.2),30,1.5),('Edge',(0,-1,1.2),45,1)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);lights.append((o,Vector(offset)))
world=bpy.data.worlds.new('NeutralStudio');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.3,.3,.3,1);bg.inputs['Strength'].default_value=.12
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
scene.render.resolution_percentage=100;scene.render.use_compositing=False;scene.render.use_sequencer=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='None';scene.view_settings.exposure=0
records=[]
def render(name,subjects,size=(1024,1024),fill=.84):
    for o in objects:o.hide_render=o not in subjects
    bpy.context.view_layer.update();rot=cam.matrix_world.to_3x3();axes=[rot@Vector(a) for a in [(1,0,0),(0,1,0),(0,0,1)]]
    pts=[o.matrix_world@v.co for o in subjects for v in o.data.vertices]
    lo=[min(p.dot(a) for p in pts) for a in axes];hi=[max(p.dot(a) for p in pts) for a in axes]
    center=sum((a*((l+h)*.5) for a,l,h in zip(axes,lo,hi)),Vector())
    cam.location=center+axes[2]*3;data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*size[0]/size[1])/fill
    for o,offset in lights:o.location=center+offset;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x,scene.render.resolution_y=size;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True);records.append(dict(name=name,objects=[o.name for o in subjects],size=size,fill=fill));print('ICON_SAVED',name,flush=True)
render('bow_dark_riser_false',[body])
shutil.copy2(OUT/'bow_dark_riser_false.png',OUT/'bow_dark_riser_strong_draw.png')
render('bow_dark_grip_false',[grip]);grip.data.materials[0]=linen;render('bow_dark_grip_waxed_linen',[grip]);grip.data.materials[0]=original
place_string(True);render('bow_dark_string_false',strings)
place_string(True,True);render('bow_dark_string_fast_string',strings);place_string()
render('bow_dark_arrow_rest_false',[rest]);render('bow_dark_arrow_rest_lined_rest',[lined]);render('bow_dark_sight_false',[sight])
for slot in ['riser','grip','string','arrow_rest','sight']:shutil.copy2(OUT/('bow_dark_'+slot+'_false.png'),OUT/('bow_dark_category_'+slot+'.png'))
shutil.copy2(ROOT/'Content/ColdSteelData/AttachmentIcons20260913/optic_false.png',OUT/'bow_dark_sight_no_sight.png')
subjects=[body,grip,rest,sight]+strings
turn=Matrix.Rotation(-math.pi/2,4,'Y')
for o in subjects:o.matrix_world=turn@o.matrix_world
scene.view_settings.view_transform='Standard'
render('bow_dark_2x',subjects,(1280,640),.91)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ModularIcons.blend'))
(P/'icon-authoring.json').write_text(json.dumps(dict(records=records,part_orientation='installed: forward +X screen left, up +Z, camera on Blender +Y (UE -Y)',
    source_meshes=bow['bow_part_slots'],strong_draw='numerical tuning; same actual body image',string_icon='actual full-draw two-segment geometry',
    no_sight='shared neutral removal symbol optic_false.png',runtime_tested=False),indent=2),encoding='utf8')
print('BOW_MODULAR_ICONS_AUTHORED',flush=True)
