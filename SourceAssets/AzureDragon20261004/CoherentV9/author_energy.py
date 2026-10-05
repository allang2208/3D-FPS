"""Closed 3D crystal, sculpted dragon crest, solid rune helix and flame tongues.

No image projection, screen-facing sheet, render or gameplay test.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'Export'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .01
materials = {n:bpy.data.materials.new(n) for n in ('Column','Crest','Helix','Flame')}
parts = {n:[] for n in materials}


def mesh(name, vertices, faces, kind, tag=.2, smooth=False, attrs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(materials[kind])
    uv = data.uv_layers.new(name='UVMap')
    color = data.color_attributes.new(name='FlameData', type='FLOAT_COLOR', domain='CORNER')
    for poly in data.polygons:
        poly.use_smooth = smooth
        for loop in poly.loop_indices:
            index = data.loops[loop].vertex_index
            p = data.vertices[index].co
            uv.data[loop].uv = (tag, 1.-(p.z+20.)/36.)
            color.data[loop].color = attrs[index] if attrs else (0,0,0,1)
    parts[kind].append(obj)
    return obj


def curve(points, radii, steps=6):
    p = [Vector(x) for x in points]
    positions, widths = [], []
    for i in range(len(p)-1):
        a,b,c,d = p[max(0,i-1)], p[i], p[i+1], p[min(len(p)-1,i+2)]
        for j in range(steps):
            t = j/steps
            positions.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
            widths.append(radii[i]*(1.-t)+radii[i+1]*t)
    return positions+[p[-1]], widths+[radii[-1]]


def tube(name, positions, radii, kind, tag=.75, sides=8, soften=True, ratio=1., fire_seed=None):
    positions, radii = curve(positions, radii) if soften else ([Vector(p) for p in positions], radii)
    vertices, faces, attrs = [], [], []
    for i, p in enumerate(positions):
        tangent = (positions[min(i+1,len(positions)-1)]-positions[max(i-1,0)]).normalized()
        reference = Vector((1,0,0)) if abs(tangent.x)<.9 else Vector((0,0,1))
        a = tangent.cross(reference).normalized()
        b = tangent.cross(a).normalized()
        for j in range(sides):
            angle = math.tau*j/sides
            vertices.append(p+(a*math.cos(angle)*ratio+b*math.sin(angle))*radii[i])
            attrs.append(((positions[0].z+24.)/60., i/(len(positions)-1), fire_seed or 0., 1.))
        if i:
            for j in range(sides):
                k = (j+1)%sides
                faces.append(((i-1)*sides+j,(i-1)*sides+k,i*sides+k,i*sides+j))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(positions)-1)*sides+j for j in range(sides))])
    return mesh(name, vertices, faces, kind, tag, True, attrs)


def ellipsoid(name, center, scale, tag=.22, smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # Bake translations to vertices: all four runtime layers share the same origin.
    for v in obj.data.vertices:
        v.co += obj.location
    obj.location = (0,0,0)
    obj.data.materials.append(materials['Crest'])
    uv = obj.data.uv_layers.active
    for poly in obj.data.polygons:
        poly.use_smooth = smooth
        for loop in poly.loop_indices:
            p = obj.data.vertices[obj.data.loops[loop].vertex_index].co
            uv.data[loop].uv = (tag, 1.-(p.z+20.)/36.)
    parts['Crest'].append(obj)
    return obj


def diamond(name, center, width, height, thickness, kind, tag):
    x,y,z = center
    vertices = [(x,y-width,z),(x,y,z+height),(x,y+width,z),(x,y,z-height),
                (x-thickness,y,z),(x+thickness,y,z)]
    faces = [(4,0,1),(4,1,2),(4,2,3),(4,3,0),(5,1,0),(5,2,1),(5,3,2),(5,0,3)]
    return mesh(name,vertices,faces,kind,tag)


# Hollow-looking twelve-sided vessel with a closed, bevelled physical surface.
rings = [(-23.5,.025),(-20.0,.90),(-18.8,1.),(15.8,1.),(17.0,.76),(18.2,.04)]
vertices = [(math.cos(math.tau*j/12)*1.55*r,math.sin(math.tau*j/12)*2.4*r,z)
            for z,r in rings for j in range(12)]
faces = [(i*12+j,i*12+(j+1)%12,(i+1)*12+(j+1)%12,(i+1)*12+j)
         for i in range(len(rings)-1) for j in range(12)]
faces += [tuple(range(11,-1,-1)),tuple((len(rings)-1)*12+j for j in range(12))]
mesh('CrystalVessel',vertices,faces,'Column',.12)
for j in range(6):
    angle = math.tau*j/6
    path = [(math.cos(angle)*1.57*r,math.sin(angle)*2.42*r,z) for z,r in rings]
    tube('CrystalEdge'+str(j),path,[.015,.035,.034,.034,.03,.008],'Column',.76,soften=False,sides=6)
for tier in range(9):
    z = -20.+tier*4.
    # Separate inset prisms make the nine levels readable in perspective.
    zs = [(z+.13,.70),(z+.43,.84),(z+3.55,.84),(z+3.85,.70)]
    points = [(math.cos(math.tau*j/8+math.pi/8)*1.45*r,
               math.sin(math.tau*j/8+math.pi/8)*2.20*r,h) for h,r in zs for j in range(8)]
    polys = [(i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j) for i in range(3) for j in range(8)]
    polys += [tuple(range(7,-1,-1)),tuple(24+j for j in range(8))]
    mesh('EnergyCell'+str(tier),points,polys,'Column',.34)
    # Full circumferential bevel ring, no flat horizontal line on a card.
    ring = [(math.cos(math.tau*j/48)*1.56,math.sin(math.tau*j/48)*2.43,z+.10) for j in range(49)]
    tube('TierRim'+str(tier),ring,[.039]*49,'Column',.85,sides=6,soften=False)
    for side in (-1,1):
        diamond('CellRune',(-1.52,side*.8,z+1.96),.28,.54,.055,'Column',.62)

# Long dragon neck, open jaw and ornate anatomy follow the approved silhouette.
neck_points = [(0,0,16.),(0,-.4,18.),(0,-2.05,20.1),(0,-2.55,22.4),(0,-1.65,24.7),(0,.15,25.8)]
tube('DragonNeck',neck_points,[.85,.95,1.05,1.0,1.14,1.05],'Crest',.22,sides=16,ratio=.75)
ellipsoid('DragonCranium',(0,.35,25.9),(.98,1.55,1.0))
ellipsoid('CheekMuscle',(0,.82,25.13),(.89,1.05,.72))
ellipsoid('LongUpperMuzzle',(0,2.11,25.48),(.65,1.67,.48))
ellipsoid('Nose',(0,3.53,25.48),(.48,.42,.40),.45)
tube('OpenLowerJaw',[(0,-.18,25.12),(0,.66,23.75),(0,2.19,23.72),(0,3.50,24.78)],
     [.49,.36,.29,.12],'Crest',.30,sides=12)
for side in (-1,1):
    x = side*.95
    ellipsoid('EyeSocket'+str(side),(x,.87,26.02),(.12,.43,.25),.50)
    ellipsoid('SlitEye'+str(side),(side*1.075,1.01,26.07),(.045,.26,.09),.98)
    tube('Brow'+str(side),[(side*.75,-.35,26.38),(side*1.04,.79,26.41),(side*.84,1.62,25.94)],
         [.10,.16,.04],'Crest',.80)
    tube('MuzzleRidge'+str(side),[(side*.79,.65,25.69),(side*.65,1.84,25.83),(side*.43,3.70,25.65)],
         [.075,.10,.018],'Crest',.78)
    tube('RearHorn'+str(side),[(side*.60,-.60,26.4),(side*.86,-1.70,27.77),
                              (side*.83,-2.15,29.39),(side*.63,-1.66,30.28)],
         [.28,.19,.085,.004],'Crest',.82,sides=10)
    tube('FrontHorn'+str(side),[(side*.33,.36,26.6),(side*.49,-.39,28.05),(side*.47,-.24,29.05)],
         [.19,.12,.005],'Crest',.82)
    tube('UpperWhisker'+str(side),[(side*.52,3.2,25.70),(side*.53,4.75,26.5),
                                  (side*.28,4.84,27.76),(side*.14,4.17,28.20)],
         [.06,.052,.025,.003],'Crest',.82)
    tube('LowerWhisker'+str(side),[(side*.32,2.5,23.9),(side*.40,4.46,23.22),
                                  (side*.17,5.15,24.06),(side*.10,5.05,25.1)],
         [.055,.04,.02,.003],'Crest',.78)
    for i in range(5):
        y = 1.20+i*.44
        tube('UpperFang',[(side*.43,y,25.16),(side*.40,y+.06,24.58)],
             [.093,.004],'Crest',.90,sides=8,soften=False)
        if i in (0,3):
            tube('LowerFang',[(side*.25,y,23.92),(side*.20,y+.03,24.39)],
                 [.07,.004],'Crest',.90,sides=8,soften=False)
# Sculpted scale plates on both sides of the S-neck, plus the glowing ridge.
centerline,_ = curve(neck_points,[1.]*len(neck_points),steps=5)
for i in range(1,len(centerline)-2,2):
    p = centerline[i]
    for side in (-1,1):
        for row in (-1,0,1):
            diamond('DragonScale',(side*.72,p.y+row*.54,p.z),.38,.43,.10,'Crest',.54)
for i in range(2,len(centerline)-4,3):
    p = centerline[i]
    tube('DorsalSpine',[(0,p.y-.88,p.z),(0,p.y-1.72,p.z+1.25),(0,p.y-1.34,p.z+.29)],
         [.19,.009,.10],'Crest',.84,soften=False)
for side in (-1,1):
    tube('NeckRidge',[(side*.77,p.y-.50,p.z) for p in centerline],
         [.046]*len(centerline),'Crest',.80,soften=False)

# The helix occupies a real cylinder. Edge rails and individual rune strokes have depth.
helix_points = []
for i in range(211):
    t = i/210
    theta = math.tau*2.60*t+.5
    helix_points.append(Vector((3.80*math.cos(theta),3.95*math.sin(theta),-19.+36.*t)))
for rail in (-1,1):
    points = [p+Vector((0,0,rail*.32)) for p in helix_points]
    tube('HelixRail',points,[.039]*len(points),'Helix',.72,sides=6,soften=False)
vertices, faces = [], []
for p in helix_points:
    radial = Vector((p.x,p.y,0)).normalized()
    for offset, height in ((-.035,-.32),(-.035,.32),(.035,.32),(.035,-.32)):
        vertices.append(p+radial*offset+Vector((0,0,height)))
for i in range(len(helix_points)-1):
    for j in range(4):
        faces.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
faces += [(3,2,1,0),tuple((len(helix_points)-1)*4+j for j in range(4))]
mesh('RuneRibbon',vertices,faces,'Helix',.18)
patterns = [[(-1,-1),(0,1),(1,-1),(0,0),(-1,.1)],
            [(-1,1),(1,1),(0,0),(1,-1),(-1,-1)],
            [(0,-1),(0,1),(1,.35),(0,0),(-1,.35)],
            [(-1,-1),(1,1),(0,0),(-1,1),(1,-1)]]
for i in range(44):
    t = (i+.5)/44
    theta = math.tau*2.60*t+.5
    center = Vector((3.86*math.cos(theta),4.01*math.sin(theta),-19.+36*t))
    tangent = Vector((-math.sin(theta),math.cos(theta),0))
    points = [center+tangent*(a*.24)+Vector((0,0,b*.22)) for a,b in patterns[i%4]]
    tube('RuneGlyph',points,[.026]*len(points),'Helix',.92,sides=6,soften=False)

# Closed, twisting fire tongues; per-strand vertex data controls independent motion.
for i in range(30):
    seed = (i*.61803398875)%1.
    angle = math.tau*seed
    z = -22.+(i%10)*4.9
    radius = 2.90+.9*math.sin(i*1.71)**2
    height = 4.2+3.4*((i*7)%11)/10
    positions=[]
    for j in range(6):
        t=j/5
        a=angle+.28*math.sin(t*4.0+i)
        r=radius+.65*math.sin(t*math.pi)+.28*math.sin(t*7+i)
        positions.append((math.cos(a)*r,math.sin(a)*r,z+height*t))
    tube('SpectralFlame'+str(i),positions,[.07,.35,.41,.29,.15,.003],
         'Flame',.25,sides=10,ratio=.70,fire_seed=seed)
for i in range(9):
    angle=math.tau*i/9
    positions=[(math.cos(angle)*1.7,math.sin(angle)*1.7,25),
               (math.cos(angle+.13)*2.2,math.sin(angle+.13)*2.2,28),
               (math.cos(angle-.14)*2.1,math.sin(angle-.14)*2.1,31),
               (math.cos(angle+.06)*2.6,math.sin(angle+.06)*2.6,34.3)]
    tube('CrownFlame'+str(i),positions,[.18,.38,.17,.003],'Flame',.25,sides=10,fire_seed=i/9)

manifest=[]
for kind, objects in parts.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
    obj=bpy.context.object
    obj.name='SM_AzureDragonEnergy'+kind+'V9'
    obj.data.materials.clear()
    obj.data.materials.append(materials[kind])
    for poly in obj.data.polygons:
        poly.material_index=0
    filename=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'MESH'},
                            axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',
                            use_tspace=False,apply_scale_options='FBX_SCALE_ALL',embed_textures=False)
    manifest.append(dict(name=obj.name,kind=kind,fbx=str(filename),
                         triangles=sum(len(p.vertices)-2 for p in obj.data.polygons)))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AzureDragonEnergy_SolidV9.blend'))
(OUT/'meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('AZURE_DRAGON_ENERGY_SOLID_V9_EXPORTED meshes=4 no_projected_image=true',flush=True)
