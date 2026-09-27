"""Render current bow parts in a neutral grayscale catalog finish, in Blender only."""
import bpy, math, json, shutil, sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;S=P.parent;ROOT=P.parents[1];OUT=P/'Icons';OUT.mkdir(exist_ok=True)
bow=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8-sig'))['bow_dark']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene; objects=[]; sources={};records=[];copied_materials={}
def append(path,name):
    with bpy.data.libraries.load(str(S/path),link=False) as (a,b):b.objects=[name]
    o=b.objects[0];scene.collection.objects.link(o);o.data=o.data.copy()
    mat=o.matrix_world.copy();o.parent=None;o.modifiers.clear()
    o.data.transform(Matrix.Scale(.01,4)@mat);o.matrix_world=Matrix.Identity(4)
    o.hide_render=True;o.hide_viewport=False;o.hide_set(False)
    # Resolve linked-library relative paths before saving the new author scene.
    for m in o.data.materials:
        if m and m.use_nodes:
            for node in m.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image:
                    im=node.image
                    path_abs=bpy.path.abspath(im.filepath,library=im.library)
                    if not Path(path_abs).exists():
                        raw=im.filepath.removeprefix('//').replace('\\','/')
                        path_abs=str(((S/path).parent/raw).resolve())
                    if not Path(path_abs).exists():raise RuntimeError('Missing source texture '+path_abs)
                    im.filepath=path_abs
    for i,m in enumerate(o.data.materials):
        if m is None:continue
        if m not in copied_materials:
            c=m.copy();c.name='IconGray_'+m.name;copied_materials[m]=c
            if c.use_nodes:
                n=c.node_tree.nodes;links=c.node_tree.links
                for bsdf in [n for n in n if n.type=='BSDF_PRINCIPLED']:
                    inp=bsdf.inputs['Base Color']
                    if inp.is_linked:
                        source=inp.links[0].from_socket
                        gray=n.new('ShaderNodeRGBToBW');links.new(source,gray.inputs[0]);value=gray.outputs[0]
                    else:
                        rgb=inp.default_value;value=n.new('ShaderNodeValue').outputs[0]
                        value.default_value=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
                    power=n.new('ShaderNodeMath');power.operation='POWER';power.inputs[1].default_value=.25;links.new(value,power.inputs[0])
                    scale=n.new('ShaderNodeMath');scale.operation='MULTIPLY_ADD';scale.inputs[1].default_value=.45;scale.inputs[2].default_value=.16
                    links.new(power.outputs[0],scale.inputs[0]);links.new(scale.outputs[0],inp)
                    bsdf.inputs['Coat Tint'].default_value=(1,1,1,1)
        o.data.materials[i]=copied_materials[m]
    sources[o.name]=dict(blend=str(S/path),object=name);objects.append(o);return o
bodypath='BowSurfaceRepair20260927/Bow_ElasticBodies_Outward.blend'
bodies=[append(bodypath,'SK_Bow_Flex_'+r) for r in ['Original','Swift','Heavy','Steady']]
grip=append('BowGripContact20260927/Bow_GripContact.blend','SM_Bow_GripWrap_Fitted')
grips=[append('BowGripSeries20260927/Bow_GripSeries.blend','SM_Bow_Grip_'+r) for r in ['WovenLinen','SlimLeather','PaddedLeather']]
rests=[append('BowModular20260926/Bow_ModularParts.blend','SM_Bow_ArrowRest'+r) for r in ['Wood','Lined']]
sight=append('BowWoodBracket20260927/Bow_WoodBracketSight.blend','SM_Bow_WoodBracketSight')
def constant(name,value,rough=.78,emission=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(value,value,value,1);p.inputs['Roughness'].default_value=rough
    if emission:p.inputs['Emission Color'].default_value=(value,value,value,1);p.inputs['Emission Strength'].default_value=.6
    return m
linen=constant('IconGray_WaxedLinen',.40,.84)
# The retained rest mesh contains author placeholders; UE binds carved wood PBR.
# Restore that binding before rendering, using the same current longbow maps.
restwood=bodies[0].data.materials[0].copy();restwood.name='IconGray_RuntimeCarvedWood'
nodes=restwood.node_tree.nodes;links=restwood.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for link in list(bsdf.inputs['Metallic'].links):links.remove(link)
bsdf.inputs['Metallic'].default_value=0
rough=bsdf.inputs['Roughness']
if rough.is_linked:
    source=rough.links[0].from_socket;minimum=nodes.new('ShaderNodeMath');minimum.operation='MAXIMUM';minimum.inputs[1].default_value=.42
    links.new(source,minimum.inputs[0]);links.new(minimum.outputs[0],rough)
for n in nodes:
    if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.55
for o in rests:
    for i,m in enumerate(o.data.materials):o.data.materials[i]=linen if 'Leather' in m.name else restwood
line=constant('IconGray_ThinLine',.65,.78,True)
symbol=constant('IconGray_RemoveSymbol',.52,.75,True)
def point(key):
    x,y,z=map(float,bow[key].split(','));return Vector((x,-y,z))*.01
strings=[]
for key in ['nock_upper_cm','nock_lower_cm']:
    a,b=point(key),point('draw_anchor_cm');d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=1,depth=1)
    o=bpy.context.object;o.name='Icon_Line_'+key;o.location=(a+b)*.5;o.rotation_mode='QUATERNION'
    o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized());o.scale=(.0009,.0009,d.length)
    for f in o.data.polygons:f.use_smooth=True
    o.data.materials.append(line);strings.append(o);objects.append(o);o.hide_render=True
# Neutral removal glyph, authored as curves; the former shared icon was a rifle sight.
def curve(name,pts,closed):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=.013;d.bevel_resolution=4
    sp=d.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts):p.co=(*co,1)
    sp.use_cyclic_u=closed
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);d.materials.append(symbol)
    bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o.select_set(False)
    objects.append(o);o.hide_render=True;return o
remove=[curve('RemoveCircle',[(.33*math.cos(i*math.tau/128),0,.33*math.sin(i*math.tau/128)) for i in range(128)],True),
        curve('RemoveMinus',[(-.18,0,0),(.18,0,0)],False)]
data=bpy.data.cameras.new('NeutralPartsCamera');data.type='ORTHO';data.clip_start=.001;data.clip_end=100
cam=bpy.data.objects.new('NeutralPartsCamera',data);scene.collection.objects.link(cam);scene.camera=cam
lights=[]
for name,offset,power,size in [('Key',(-1,1.4,1.5),70,2),('Fill',(1,1.3,.2),38,1.5),('Edge',(0,-1,1.2),45,1)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=(1,1,1)
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);lights.append((o,Vector(offset)))
w=bpy.data.worlds.new('NeutralStudio');w.use_nodes=True;scene.world=w
bg=w.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.3,.3,.3,1);bg.inputs['Strength'].default_value=.18
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.color_depth='8';scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.use_compositing=False;scene.render.use_sequencer=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='None';scene.view_settings.exposure=0
def render(name,subjects,angle=0,line_pixels=0):
    for o in objects:o.hide_render=o not in subjects
    direction=Vector((-math.sin(angle),math.cos(angle),0))
    cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update();rot=cam.matrix_world.to_3x3();axes=[rot@Vector(a) for a in [(1,0,0),(0,1,0),(0,0,1)]]
    pts=[o.matrix_world@v.co for o in subjects for v in o.data.vertices]
    lo=[min(p.dot(a) for p in pts) for a in axes];hi=[max(p.dot(a) for p in pts) for a in axes]
    center=sum((a*((l+h)*.5) for a,l,h in zip(axes,lo,hi)),Vector())
    cam.location=center+direction*3;data.ortho_scale=max(hi[0]-lo[0],hi[1]-lo[1])/.84
    oldscales=[o.scale.copy() for o in subjects]
    if line_pixels:
        for o in subjects:o.scale.x=o.scale.y=max(o.scale.x,data.ortho_scale*line_pixels/64/2)
    for o,offset in lights:o.location=center+offset;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    for o,s in zip(subjects,oldscales):o.scale=s
    records.append(dict(name=name,subjects=[sources.get(o.name,dict(object=o.name,procedural=True)) for o in subjects],
        camera_azimuth_degrees=math.degrees(angle),ortho_scale=data.ortho_scale,fill=.84,min_line_pixels_at_64=line_pixels))
    (P/'render-receipt.json').write_text(json.dumps(dict(records=records,gameplay_tested=False),indent=2),encoding='utf8')
    print('BOW_GRAY_ICON_SAVED',name,flush=True)
rest_only='--only-rests' in sys.argv
if rest_only:
    records=[r for r in json.loads((P/'render-receipt.json').read_text())['records'] if not r['name'].startswith('bow_dark_arrow_rest_')]
else:
    for o,suffix in zip(bodies,['false','swift_limb','heavy_limb','steady_limb']):render('bow_dark_riser_'+suffix,[o])
    shutil.copy2(OUT/'bow_dark_riser_false.png',OUT/'bow_dark_riser_strong_draw.png')
    render('bow_dark_grip_false',[grip]);old=grip.data.materials[0];grip.data.materials[0]=linen
    render('bow_dark_grip_waxed_linen',[grip]);grip.data.materials[0]=old
    for o,suffix in zip(grips,['woven_linen_grip','slim_leather_grip','padded_leather_grip']):render('bow_dark_grip_'+suffix,[o])
    render('bow_dark_string_false',strings,line_pixels=1.2)
    for o in strings:o.scale.x=o.scale.y=.00065
    render('bow_dark_string_fast_string',strings,line_pixels=1.0)
for o,suffix in zip(rests,['false','lined_rest']):render('bow_dark_arrow_rest_'+suffix,[o])
if not rest_only:
    render('bow_dark_sight_false',[sight],angle=math.radians(35))
    render('bow_dark_sight_no_sight',remove)
for slot in ['riser','grip','string','arrow_rest','sight']:shutil.copy2(OUT/('bow_dark_'+slot+'_false.png'),OUT/('bow_dark_category_'+slot+'.png'))
for o in objects:o.hide_render=True
sight.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_MonochromeAttachmentIcons.blend'))
print('BOW_GRAY_ICONS_COMPLETE',21,flush=True)
