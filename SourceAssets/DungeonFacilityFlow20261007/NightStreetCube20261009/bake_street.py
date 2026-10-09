"""Author one continuous industrial street and bake six production cubemap faces.
The staging city is never imported into the gameplay map. No acceptance render.
"""
from pathlib import Path
import bpy,json,sys,math,random,hashlib,re
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent;FLOW=ROOT.parent;PROJECT=FLOW.parents[1]
OUT=ROOT/'Authored';FACES=OUT/'CubeFaces';FACES.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'));import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.engine='CYCLES'
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU';scene.cycles.samples=96;scene.cycles.use_adaptive_sampling=True
scene.cycles.adaptive_threshold=.018;scene.cycles.use_denoising=True
scene.cycles.max_bounces=6;scene.cycles.transparent_max_bounces=12;scene.cycles.volume_bounces=1
scene.render.resolution_x=2048;scene.render.resolution_y=2048;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.render.film_transparent=False
rng=random.Random(20261009);materials={}

def material(name,color,rough=.65,metal=0,noise=0,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    if emission:bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
    if noise:
        geo=n.new('ShaderNodeNewGeometry');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=noise;tex.inputs['Detail'].default_value=3
        l.new(geo.outputs['Position'],tex.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(v*.45 for v in color),1);ramp.color_ramp.elements[1].color=(*(v*1.25 for v in color),1)
        l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=.025
        l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    materials[name]=m;return m

material('Concrete',(.24,.235,.205),.87,noise=2.8)
material('DarkConcrete',(.11,.125,.13),.86,noise=3.2)
material('Rust',(.19,.07,.028),.7,.45,noise=4)
material('Steel',(.055,.065,.075),.37,.75,noise=6)
material('Frame',(.035,.055,.048),.56,.3,noise=5)
material('Window',(.008,.018,.024),.18,.4)
material('WindowLit',(.20,.27,.24),.30,emission=.5)
material('LampGlow',(1.,.48,.13),.25,emission=14)
material('Markings',(.47,.39,.18),.83,noise=12)
asphalt=material('Asphalt',(.043,.052,.060),.3,noise=85)
nt=asphalt.node_tree;n=nt.nodes;l=nt.links;bs=n.get('Principled BSDF')
geo=n.new('ShaderNodeNewGeometry');wet=n.new('ShaderNodeTexNoise');wet.inputs['Scale'].default_value=.33;wet.inputs['Detail'].default_value=4;wet.inputs['Roughness'].default_value=.7
l.new(geo.outputs['Position'],wet.inputs['Vector']);r=n.new('ShaderNodeMapRange');r.inputs['From Min'].default_value=.28;r.inputs['From Max'].default_value=.68;r.inputs['To Min'].default_value=.10;r.inputs['To Max'].default_value=.64
l.new(wet.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],bs.inputs['Roughness'])
material('Roof',(.035,.04,.044),.8,noise=5)
g.ROOM='StreetSource'
def box(c,size,mat='Concrete',kind='Architecture'):g.box(kind,c,size,mat)
def pipe(a,b,r=.04,mat='Steel',kind='Pipes'):g.cylinder(kind,a,b,r,mat,segments=16)
def area(name,p,target,energy,color,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

# The entire six-direction capture sees authored ground, buildings or sky.
box((0,70,-.12),(320,480,.24),'Asphalt','Ground')
for side in (-1,1):
    box((side*10.25,76,.08),(5,235,.16),'Concrete','Ground')
    for y in range(-38,193,2):box((side*7.80,y,.13),(.26,1.98,.26),'Concrete','Kerbs')
    for y in range(12,185,10):box((side*6.75,y,.008),(.10,4.5,.016),'Markings','RoadPaint')
for y in range(18,190,12):box((0,y,.01),(.10,3,.02),'Markings','RoadPaint')

for side in (-1,1):
    for index,y in enumerate((11,40,74,112,155)):
        length=(24,28,32,36,40)[index];height=(10,13,11,16,12)[(index+(side==1))%5]
        x=side*18;inner=side*12
        box((x,y,height/2),(12,length,height),'Concrete' if index%2==0 else 'DarkConcrete')
        box((x,y,height+.15),(12.4,length+.4,.3),'Roof','Roof')
        box((inner-side*.06,y,.35),(.18,length,.70),'DarkConcrete','Trim')
        for zz in (4.7,height-.2):box((inner-side*.09,y,zz),(.23,length+.1,.20),'Concrete','Trim')
        for yy in (y-length/2+.16,y+length/2-.16):
            box((inner-side*.12,yy,height/2),(.32,.34,height),'Concrete','Trim')
            pipe((inner-side*.34,yy,.2),(inner-side*.34,yy,height+.1),.075,'Rust')
        # Large loading shutter and its recessed steel surround.
        door_y=y-3.6
        box((inner-side*.07,door_y,2.25),(.17,4.1,4.5),'Steel','Shutters')
        for j in range(32):box((inner-side*.19,door_y,.09+j*.137),(.065,3.85,.075),'Frame','Shutters')
        for yy in (door_y-2.10,door_y+2.10):box((inner-side*.2,yy,2.3),(.24,.17,4.6),'Rust','Trim')
        box((inner-side*.23,door_y,4.63),(.32,4.45,.23),'Steel','Trim')
        box((inner-side*.38,door_y,4.92),(.53,.72,.14),'Frame','Lamps')
        box((inner-side*.39,door_y,4.84),(.4,.60,.018),'LampGlow','Lamps')
        area('Warehouse loading light',(inner-side*.50,door_y,4.70),(side*8,door_y,0),180,(1,.58,.24),.7)
        for yy in (y-7.8,y-2,y+3.8,y+8.8):
            for zz in (6.6,9.0):
                if zz+1>height:continue
                box((inner-side*.12,yy,zz),(.08,3.9,1.72),'WindowLit' if rng.random()<.12 else 'Window','Windows')
                for dy in (-2,-1,0,1,2):box((inner-side*.20,yy+dy,zz),(.09,.06,1.80),'Frame','Windows')
                for dz in (-.89,0,.89):box((inner-side*.20,yy,zz+dz),(.09,4.05,.06),'Frame','Windows')
        for yy in (y+length/2-2,y+length/2-3.8):
            box((inner-side*.45,yy,1.5),(.65,1.35,2.3),'Frame','Equipment')
            for z in (.8,1,1.2,1.4,1.6,1.8):box((inner-side*.79,yy,z),(.035,1.1,.04),'Steel','Equipment')

# Rear facade closes the world behind the capture without a blank colour panel.
box((0,-17,6),(38,8,12),'Concrete')
for x in range(-16,18,4):
    box((x,-12.94,5.3),(2.8,.08,2.6),'Window','Windows')
    for z in (4,5.3,6.6):box((x,-12.88,z),(2.9,.10,.07),'Frame','Windows')
box((0,-12.82,2),(5,.16,4),'Frame','Shutters')
for x in (-2.2,2.2):area('Rear reception lamp',(x,-11.9,4.5),(x,-6,0),110,(.55,.69,1),.65)

# Poles, drooping wires and overhead plant services make a layered skyline.
for side in (-1,1):
    for y in (5,34,66,103,143,186):
        x=side*8.7
        pipe((x,y,.1),(x,y,7.4),.095,'Steel','Streetlamps')
        pipe((x,y,7.25),(x-side*1.25,y,7.4),.048,'Steel','Streetlamps')
        box((x-side*1.3,y,7.36),(.83,.35,.16),'Steel','Streetlamps')
        box((x-side*1.3,y,7.26),(.72,.28,.015),'LampGlow','Streetlamps')
        area('Amber street lamp',(x-side*1.3,y,7.18),(x-side*2,y,0),420,(1,.55,.24),.65)
    for y in (20,58,96,134,172):
        pipe((side*11.3,y,0),(side*11.3,y,11),.11,'Rust','Utilities')
        box((side*11.3,y,10.2),(1.8,.14,.15),'Steel','Utilities')
        if y<172:
            for offset in (-.65,0,.65):
                ps=[(side*11.3+offset,y+t*38,10.5-1.25*math.sin(math.pi*t)) for t in (0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1)]
                g.tube('Utilities',ps,.022,'Steel',8)
for y in (58,111,169):
    for z in (7.9,8.8):pipe((-12,y,z),(12,y,z),.22,'Rust','PipeBridges')
    for x in (-11.5,11.5):pipe((x,y,0),(x,y,9.4),.2,'Steel','PipeBridges')
    for x in range(-11,12,2):box((x,y,8.35),(.11,.75,1.5),'Steel','PipeBridges')
for x,y,r,h in [(24,94,4,24),(-25,132,5,28),(19,171,4,21)]:
    g.cylinder('Silos',(x,y,0),(x,y,h),r,'Steel',64)
    for z in range(1,h,3):g.ring('Silos',(x,y,z),(0,0,1),r+.07,r-.02,.07,'Rust',64)
for x,y,h in [(-28,88,38),(28,155,45),(-20,192,33)]:
    g.cylinder('Stacks',(x,y,0),(x,y,h),1.2,'DarkConcrete',48)
    for z in range(h-9,h,3):g.cylinder('Stacks',(x,y,z),(x,y,z+1),1.24,'Rust',48)

for (room,kind),data in g.G.items():
    mesh=bpy.data.meshes.new(kind);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    o=bpy.data.objects.new(kind,mesh);scene.collection.objects.link(o)
    slots=list(dict.fromkeys(data['m']))
    for name in slots:mesh.materials.append(materials[name])
    for face,name,smooth in zip(mesh.polygons,data['m'],data['smooth']):face.material_index=slots.index(name);face.use_smooth=smooth
    if kind in ('Trim','Equipment','Streetlamps'):
        mod=o.modifiers.new('Small manufactured edge bevel','BEVEL');mod.width=.018;mod.segments=2

# Reuse the trees already exported for the ecology room, including their leaf
# alpha textures. Only this authoring scene holds the full vegetation geometry.
stock=PROJECT/'SourceAssets/DungeonEcology20261004/Sources/StockV4'
foliage=json.loads((ROOT/'Sources/Foliage/materials.json').read_text('utf8'))
for entry in foliage:
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(stock/('SM_'+entry['name']+'.fbx')),use_custom_normals=True)
    objs=[o for o in set(bpy.data.objects)-before if o.type=='MESH']
    for o in list(objs):
        lod=re.search(r'lod[ _.\-]?(\d+)',o.name,re.I)
        if lod and int(lod.group(1))>0:objs.remove(o);bpy.data.objects.remove(o,do_unlink=True)
    all_bounds=[o.matrix_world@Vector(c) for o in objs for c in o.bound_box]
    bottom=min(p.z for p in all_bounds);height=max(p.z for p in all_bounds)-bottom;factor=8/max(height,.1)
    for o in objs:
        o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
        for i,row in enumerate(entry['slots']):
            if i>=len(o.data.materials):continue
            m=bpy.data.materials.new('Reused_'+entry['name']+'_'+str(i));m.use_nodes=True
            bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.88
            colors=[t for t in row['textures'] if t['srgb']]
            chosen=next((t for t in colors if any(k in t['parameter'].lower() for k in ('base','color','albedo','diffuse'))),colors[0] if colors else None)
            if chosen:
                tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(chosen['file'],check_existing=True)
                m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
                if row['slot'].lower() in ('leaves','billboard'):m.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
            else:bs.inputs['Base Color'].default_value=(.06,.09,.035,1)
            o.data.materials[i]=m
        # FBX scene-unit conversion is retained; normalize one source tree to an
        # 8 m street-tree height and clone its geometry/materials as linked data.
        o.scale*=factor;o.location.z-=bottom*factor
        for j,(x,y) in enumerate([(-10.5,2),(-10.5,30),(10.6,13),(10.5,47),(-10.7,80),(10.5,117)]):
            if (j%2==0)!=(entry['name']=='Tree_M_01'):continue
            clone=o.copy();clone.data=o.data;scene.collection.objects.link(clone)
            clone.location.x+=x;clone.location.y+=y;clone.rotation_euler.z+=rng.uniform(-math.pi,math.pi)
        bpy.data.objects.remove(o,do_unlink=True)

world=bpy.data.worlds.new('Continuous cloudy night');world.use_nodes=True;scene.world=world
wn=world.node_tree.nodes;wl=world.node_tree.links;bg=wn.get('Background');bg.inputs['Strength'].default_value=.3
coord=wn.new('ShaderNodeTexCoord');cloud=wn.new('ShaderNodeTexNoise');cloud.inputs['Scale'].default_value=5;cloud.inputs['Detail'].default_value=5
wl.new(coord.outputs['Normal'],cloud.inputs['Vector']);ramp=wn.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.30;ramp.color_ramp.elements[0].color=(.018,.027,.048,1)
ramp.color_ramp.elements[1].position=.73;ramp.color_ramp.elements[1].color=(.12,.16,.23,1)
wl.new(cloud.outputs['Fac'],ramp.inputs[0]);wl.new(ramp.outputs['Color'],bg.inputs['Color'])
sun=bpy.data.lights.new('Moonlight','SUN');sun.energy=.22;sun.color=(.48,.64,1);sun.angle=.055
so=bpy.data.objects.new('Moonlight',sun);scene.collection.objects.link(so);so.rotation_euler=Vector((-.35,-.8,-.45)).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=5.5,location=(90,255,170));moon=bpy.context.object
moon.data.materials.append(material('Moon',(.66,.76,1),.9,emission=2))
fog=material('Street haze',(1,1,1));fog.node_tree.nodes.clear();out=fog.node_tree.nodes.new('ShaderNodeOutputMaterial');vol=fog.node_tree.nodes.new('ShaderNodeVolumeScatter');vol.inputs['Color'].default_value=(.52,.62,.75,1);vol.inputs['Density'].default_value=.0025;vol.inputs['Anisotropy'].default_value=.2;fog.node_tree.links.new(vol.outputs[0],out.inputs['Volume'])
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,65,28));o=bpy.context.object;o.name='Low night haze';o.scale=(300,450,60);o.data.materials.append(fog)

camera=bpy.data.cameras.new('Cubemap capture');camera.type='PERSP';camera.lens=18;camera.sensor_width=36;camera.clip_end=1200
cam=bpy.data.objects.new('Cubemap capture',camera);scene.collection.objects.link(cam);scene.camera=cam;cam.location=(0,0,1.65)
# DDS camera convention: q=(Blender X, Blender Z, Blender Y). Pixels are top-down.
views=[('PX',(1,0,0),(0,0,1)),('NX',(-1,0,0),(0,0,1)),('PY',(0,0,1),(0,-1,0)),('NY',(0,0,-1),(0,1,0)),('PZ',(0,1,0),(0,0,1)),('NZ',(0,-1,0),(0,0,1))]
# FBX carries unused author-machine texture references. Pack only the actual
# project exports assigned above, rather than those stale original paths.
for mat in list(bpy.data.materials):
    if mat.users==0:bpy.data.materials.remove(mat)
for image in list(bpy.data.images):
    if image.users==0:bpy.data.images.remove(image)
    elif image.source=='FILE' and Path(bpy.path.abspath(image.filepath)).is_file():image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'IndustrialNightStreetSource.blend'))
receipt=dict(stage='baking',kind='production cubemap texture bake',resolution=2048,samples=96,faces=[],game_run=False,acceptance_rendered=False)
def record():(ROOT/'bake-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
record()
for name,forward,up in views:
    f=Vector(forward);u=Vector(up);right=f.cross(u);cam.rotation_euler=Matrix((right,u,-f)).transposed().to_euler()
    scene.render.filepath=str(FACES/(name+'.png'));bpy.ops.render.render(write_still=True)
    receipt['faces'].append(dict(name=name,file=scene.render.filepath,forward=forward,up=up));record()
    print('STREET_CUBE_FACE_SAVED',name,flush=True)
receipt['stage']='six_faces_baked';record();print('STREET_CUBEMAP_BAKED',flush=True)
