"""Background precision authoring for the standalone furnace-side casting station.

Centimetre design coordinates are UE-local (+X longitudinal, +Y rear, +Z up).
Export a placeable assembly plus reusable anvil, tongs and open cooling barrel.
No preview rendering or gameplay tests.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Authored'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0

SLOTS = ['Masonry', 'DarkSteel', 'PolishedSteel', 'Wood', 'Water']
COLORS = [(0.25,.23,.20,1),(.12,.105,.085,1),(.36,.39,.41,1),(.25,.13,.055,1),(.035,.095,.10,1)]
MATS = []
for name, color in zip(SLOTS, COLORS):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    MATS.append(mat)
GROUPS = {}


def co(p):
    return Vector((p[0]*.01, -p[1]*.01, p[2]*.01))


def finish(obj, name, slot, group, bevel=.15):
    obj.name = name
    obj.data.materials.clear()
    for mat in MATS:
        obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.material_index = SLOTS.index(slot)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new('Machined edges', 'BEVEL')
        mod.width = bevel*.01
        mod.segments = 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    GROUPS.setdefault(group, []).append(obj)
    return obj


def box(name, center, size, slot='DarkSteel', group='Stand', bevel=.15):
    bpy.ops.mesh.primitive_cube_add(size=1, location=co(center))
    obj = bpy.context.object
    obj.dimensions = Vector(size)*.01
    return finish(obj, name, slot, group, bevel)


def mesh(name, verts, faces, slot, group, bevel=.12):
    data = bpy.data.meshes.new(name)
    data.from_pydata([co(v) for v in verts], [], [tuple(reversed(f)) for f in faces])
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    return finish(obj, name, slot, group, bevel)


def beam(name, a, b, radius, slot='DarkSteel', group='Stand', vertices=12):
    start, end = co(a), co(b)
    direction = end-start
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius*.01,
                                      depth=direction.length, location=(start+end)*.5)
    obj = bpy.context.object
    obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    return finish(obj, name, slot, group, .06)


def ring_mesh(name, center, outer, inner, height, slot, group, segments=64):
    verts = []
    x,y,z = center
    for radius, zz in [(outer,z-height*.5),(outer,z+height*.5),
                       (inner,z-height*.5),(inner,z+height*.5)]:
        verts.extend([(x+radius*math.cos(i*math.tau/segments),
                       y+radius*math.sin(i*math.tau/segments),zz) for i in range(segments)])
    faces = []
    for i in range(segments):
        j=(i+1)%segments
        faces.extend([(i,j,segments+j,segments+i),(2*segments+j,2*segments+i,3*segments+i,3*segments+j),
                      (segments+i,segments+j,3*segments+j,3*segments+i),(j,i,2*segments+i,2*segments+j)])
    return mesh(name,verts,faces,slot,group,.08)


def cut_hole(obj, center, size, round_hole=False):
    if round_hole:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=size[0]*.005,
                                          depth=size[2]*.01, location=co(center))
    else:
        bpy.ops.mesh.primitive_cube_add(size=1, location=co(center))
        bpy.context.object.dimensions=Vector(size)*.01
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    cutter=bpy.context.object
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Through hole','BOOLEAN')
    mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)


# A 180 x 120 cm base is the explicit building footprint, not a hidden collision extension.
box('Stone bed', (0,0,2), (180,120,4), 'Masonry', bevel=.8)
for x in [-87,87]:
    box('Bed edge', (x,0,5), (6,120,6), 'Masonry', bevel=.45)
for y in [-57,57]:
    box('Bed edge', (0,y,5), (168,6,6), 'Masonry', bevel=.45)

# Low receiver with four lanes. No chest or transport mechanism is added.
for x in [-78,-36]:
    for y in [-43,43]:
        box('Receiver leg',(x,y,18),(4,4,28), bevel=.18)
box('Receiver lower brace',(-57,0,12),(48,90,3), bevel=.18)
box('Receiver pan',(-57,0,33),(50,100,2.4), bevel=.25)
for x in [-81,-33]:
    box('Receiver side rim',(x,0,36),(2,100,5),bevel=.15)
for y in [-49,-24.5,0,24.5,49]:
    box('Receiver lane divider',(-57,y,36),(46,1.5,5),bevel=.12)
box('Receiver toe lip',(-83,0,32),(4,100,4),bevel=.25)

# Timber anvil stand with grain-aligned separate timbers, straps and anchoring bolts.
for x in [13,27,41]:
    box('Anvil stand timber',(x,22,33),(13.4,40,58),'Wood','AnvilStand',.4)
for z in [14,51]:
    box('Stand front strap',(27,.9,z),(44,1.6,5),'DarkSteel','AnvilStand',.12)
    box('Stand rear strap',(27,43.1,z),(44,1.6,5),'DarkSteel','AnvilStand',.12)
    for x in [10,44]:
        beam('Stand rivet',(x,-.3,z),(x,2,z),.9,'DarkSteel','AnvilStand',8)

# Forged anvil: wide foot, waisted web, shoulder and a genuine tapered round horn.
box('Anvil foot',(27,22,65),(40,27,6),'DarkSteel','Anvil',.65)
levels=[(68,17,11),(73,11,7),(81,12,7.5),(85,21,10)]
verts=[]
for z,rx,ry in levels:
    verts.extend([(27-rx,22-ry,z),(27+rx,22-ry,z),(27+rx,22+ry,z),(27-rx,22+ry,z)])
faces=[(3,2,1,0)]
for k in range(len(levels)-1):
    for i in range(4):
        j=(i+1)%4;faces.append((4*k+i,4*k+j,4*(k+1)+j,4*(k+1)+i))
faces.append((12,13,14,15))
mesh('Anvil waisted body',verts,faces,'DarkSteel','Anvil',.4)
face=box('Anvil working face',(29,22,88),(48,21,6),'PolishedSteel','Anvil',.23)
cut_hole(face,(47,23.8,88),(3.4,3.4,15))
cut_hole(face,(42,17,88),(1.7,1.7,15),True)
verts=[];rings=[(5,8,6.8,85),(0,7,6,84.8),(-7,5.3,4.6,84.5),(-14,3.3,2.9,84),(-22,.5,.5,83)]
for x,ry,rz,z in rings:
    verts.extend([(x,22+ry*math.cos(i*math.tau/24),z+rz*math.sin(i*math.tau/24)) for i in range(24)])
faces=[tuple(reversed(range(24)))]
for k in range(len(rings)-1):
    for i in range(24):
        j=(i+1)%24;faces.append((k*24+i,k*24+j,(k+1)*24+j,(k+1)*24+i))
faces.append(tuple(range((len(rings)-1)*24,len(rings)*24)))
mesh('Anvil round horn',verts,faces,'PolishedSteel','Anvil',.06)

# Open cooling barrel: 24 individual curved staves with interior wall and a real bottom.
cx,cy=42,-30
for i in range(24):
    angles=[(i+.035)*math.tau/24,(i+.5)*math.tau/24,(i+.965)*math.tau/24]
    verts=[]
    for z,r in [(5,20),(29,24),(54,22)]:
        for radius in [r,r-2.2]:
            verts.extend([(cx+radius*math.cos(a),cy+radius*math.sin(a),z) for a in angles])
    faces=[]
    for k in range(2):
        for j in range(2):
            a=k*6+j;b=(k+1)*6+j
            faces.extend([(a,a+1,b+1,b),(a+3,b+3,b+4,a+4)])
        faces.extend([(k*6,(k+1)*6,(k+1)*6+3,k*6+3),
                      (k*6+2,k*6+5,(k+1)*6+5,(k+1)*6+2)])
    faces.extend([(0,3,4,5,2,1),(12,13,14,17,16,15)])
    mesh('Cooling barrel stave %02d'%i,verts,faces,'Wood','CoolingBarrel',.08)
for z,r in [(11,21.6),(28,24.4),(48,23.1)]:
    ring_mesh('Barrel iron hoop',(cx,cy,z),r,r-.9,3.5,'DarkSteel','CoolingBarrel')
beam('Barrel bottom',(cx,cy,5),(cx,cy,7),19.5,'Wood','CoolingBarrel',48)
beam('Cooling water',(cx,cy,45.7),(cx,cy,46),20.5,'Water','CoolingWater',64)
for sign in [-1,1]:
    for j in range(8):
        a=math.pi*j/8;b=math.pi*(j+1)/8
        beam('Barrel handle',(cx+sign*24,cy+5*math.cos(a),36+7*math.sin(a)),
             (cx+sign*24,cy+5*math.cos(b),36+7*math.sin(b)),.7,group='CoolingBarrel')

# Tool rail and forged tongs with two separate jaws/handles and a pivot pin.
for x in [1,63]:
    box('Tool rail upright',(x,50,53),(3,3,94),bevel=.2)
box('Tool rail',(32,50,97),(65,4,6),bevel=.2)
tx,ty,tz=7,46,73
for sign in [-1,1]:
    path=[(tx+sign*6,ty,tz+21),(tx+sign*4.3,ty,tz+10),(tx+sign*1.2,ty,tz),
          (tx-sign*2.5,ty,tz-7),(tx-sign*4.8,ty,tz-12),(tx-sign*2.0,ty,tz-17)]
    for j,(a,b) in enumerate(zip(path,path[1:])):
        beam('Tong handle' if j<2 else 'Tong jaw',a,b,.62 if j<2 else .9,group='Tongs')
beam('Tong hinge',(tx,ty-1.4,tz),(tx,ty+1.4,tz),1.6,'PolishedSteel','Tongs',20)
beam('Tong hook',(tx,50,94),(tx,44,94),.6)

# Every exported face receives UVs at a consistent 50 cm texel scale.
for objs in GROUPS.values():
    for obj in objs:
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        uv=obj.data.uv_layers.new(name='UVMap')
        for face in obj.data.polygons:
            axes=sorted(range(3),key=lambda a:abs(face.normal[a]))[:2]
            for li in face.loop_indices:
                v=obj.data.vertices[obj.data.loops[li].vertex_index].co
                uv.data[li].uv=(v[axes[0]]/.5,v[axes[1]]/.5)

ASSETS={}
def export(name, groups, pivot):
    copies=[]
    for group in groups:
        for original in GROUPS[group]:
            obj=original.copy();obj.data=original.data.copy()
            bpy.context.collection.objects.link(obj);copies.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in copies:obj.select_set(True)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join()
    result=bpy.context.object;result.name=name
    bpy.context.scene.cursor.location=co(pivot)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    result.location=Vector((0,0,0))
    triangulate=result.modifiers.new('Export triangles','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
    ASSETS[name]={'fbx':str(path),'pivot_ue_cm':pivot,'material_slots':SLOTS,
                  'triangles':sum(len(p.vertices)-2 for p in result.data.polygons)}
    bpy.data.objects.remove(result,do_unlink=True)

export('SM_CastingStation',list(GROUPS),(0,0,0))
export('SM_CastingAnvil',['Anvil'],(27,22,62))
export('SM_BlacksmithTongs',['Tongs'],(tx,ty,tz))
export('SM_CoolingBarrel',['CoolingBarrel'],(cx,cy,4))
export('SM_CoolingWater',['CoolingWater'],(cx,cy,46))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CastingStation_Source.blend'))
manifest={'id':'casting_station','name':'铸造台','footprint_cells':[9,6,5],
          'dimensions_cm':[180,120,100],'assets':ASSETS,
          'sockets_ue_cm':{'IngotReceiver':[-57,0,34.2],'AnvilFace':[29,22,91],
              'TongGrip':[tx,ty,tz+14],'TongPivot':[tx,ty,tz],
              'QuenchSurface':[cx,cy,46],'DockLeft':[-90,0,34]},
          'receiver_slots_ue_cm': [[x,y,34.2] for y in [-36.75,-12.25,12.25,36.75] for x in [-72,-57,-42]],
          'future_gameplay':['forging','tongs gripping','quenching'],
          'current_gameplay':'casting output buffer only; existing storage chests remain manual',
          'rendered':False,'runtime_tested':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('CASTING_STATION_AUTHORED',json.dumps({k:v['triangles'] for k,v in ASSETS.items()}),flush=True)
