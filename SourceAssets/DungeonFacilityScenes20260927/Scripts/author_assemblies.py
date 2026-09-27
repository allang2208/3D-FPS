"""Nine reusable facility assemblies. Metres in Blender; foot pivots and authored UCX boxes.
No scene rebuild, asset downloads, render or runtime simulation.
"""
import json, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Authored'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
PATHS = {
    'Paint': '/Game/Dungeons/AtmosphereV2/Services/Materials/M_Service_Paint',
    'Steel': '/Game/Dungeons/AtmosphereV2/Materials/M_BareSteel',
    'Rubber': '/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber',
    'Timber': '/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Timber',
    'Yellow': '/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_YellowPaint',
    'Dial': '/Game/Dungeons/AtmosphereV2/Materials/M_IvoryTile',
}
MATS = {k: bpy.data.materials.new('Facility_' + k) for k in PATHS}
V, F, MATERIALS, SMOOTH = [], [], [], []
records = []

def poly(vertices, faces, mat, smooth=False):
    offset = len(V)
    V.extend(tuple(v) for v in vertices)
    F.extend(tuple(offset + i for i in face) for face in faces)
    MATERIALS.extend([mat] * len(faces))
    SMOOTH.extend([smooth] * len(faces))

def box(c, size, mat='Paint', yaw=0):
    x,y,z=c; a,b,d=(s*.5 for s in size); co,si=math.cos(yaw),math.sin(yaw)
    vertices=[(x+dx*co-dy*si,y+dx*si+dy*co,z+dz) for dx,dy,dz in
              [(-a,-b,-d),(a,-b,-d),(a,b,-d),(-a,b,-d),(-a,-b,d),(a,-b,d),(a,b,d),(-a,b,d)]]
    poly(vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def basis(a,b):
    n=(Vector(b)-Vector(a)).normalized()
    u=n.cross(Vector((0,0,1)) if abs(n.z)<.95 else Vector((0,1,0))).normalized()
    return n,u,n.cross(u).normalized()

def cylinder(a,b,r,mat='Steel',segments=24):
    n,u,v=basis(a,b)
    vertices=[Vector(p)+r*(math.cos(i*math.tau/segments)*u+math.sin(i*math.tau/segments)*v)
              for p in (a,b) for i in range(segments)]
    faces=[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    poly(vertices,faces,mat,True)
    poly(vertices,[tuple(reversed(range(segments))),tuple(range(segments,2*segments))],mat)

def ring(c, normal, radius, thickness, mat='Steel',segments=24):
    c=Vector(c); n,u,v=basis(c,c+Vector(normal)); vertices=[]
    for i in range(segments):
        radial=math.cos(i*math.tau/segments)*u+math.sin(i*math.tau/segments)*v
        for j in range(8):vertices.append(c+radial*(radius+thickness*math.cos(j*math.tau/8))+n*thickness*math.sin(j*math.tau/8))
    poly(vertices,[(i*8+j,((i+1)%segments)*8+j,((i+1)%segments)*8+(j+1)%8,i*8+(j+1)%8)
                   for i in range(segments) for j in range(8)],mat,True)

def gauge(x,y,z):
    cylinder((x,y,z),(x,y-.055,z),.07,'Steel')
    cylinder((x,y-.056,z),(x,y-.060,z),.058,'Dial')
    cylinder((x,y-.063,z),(x+.027,y-.063,z+.035),.0025,'Rubber',8)

def pump():
    box((0,0,.11),(2.2,.95,.16),'Steel')
    for x in (-.68,.68):
        for y in (-.31,.31):box((x,y,.025),(.24,.18,.05),'Rubber')
        box((x,0,.25),(.44,.62,.16),'Paint')
        cylinder((x,-.25,.60),(x,.13,.60),.27,'Paint',32)
        cylinder((x,.18,.60),(x,.39,.60),.22,'Paint',32)
        for j in range(6):cylinder((x,.19+j*.034,.60),(x,.198+j*.034,.60),.235,'Steel')
        cylinder((x,-.33,.59),(x,-.14,.59),.105,'Steel')
        cylinder((x,-.19,.70),(x,-.19,1.15),.068,'Paint')
        for z in (.93,1.11):cylinder((x,-.19,z-.018),(x,-.19,z+.018),.115,'Steel')
        ring((x,-.19,1.26),(0,0,1),.16,.014,'Yellow')
        for a in (0,math.pi/2):
            cylinder((x-math.cos(a)*.15,-.19-math.sin(a)*.15,1.26),(x+math.cos(a)*.15,-.19+math.sin(a)*.15,1.26),.008)
        gauge(x,-.29,.94)

def rack():
    for x in (-.85,.85):
        for y in (-.29,.29):box((x,y,.9),(.045,.045,1.8),'Steel')
    for z in (.14,.78,1.43):box((0,0,z),(1.8,.65,.045),'Paint')
    for x in (-.56,0,.56):
        for z in (.46,1.10,1.62):
            box((x,0,z),(.48,.50,.37),'Steel')
            box((x,-.258,z),(.40,.025,.29),'Rubber')
            for j in range(7):box((x-.18+j*.06,-.277,z),(.016,.018,.29),'Paint')
    box((0,.293,.9),(1.74,.02,.035),'Steel')

def cabinet():
    box((0,0,.10),(1.6,.68,.2),'Steel')
    box((0,.04,1.04),(1.6,.6,1.7),'Paint')
    for x in (-.4,.4):
        box((x,-.272,1.05),(.765,.025,1.57),'Paint')
        box((x+.25,-.305,1.0),(.028,.045,.20),'Steel')
        for z in (.41,.48,.55,.62):box((x,-.29,z),(.51,.015,.02),'Rubber')
        gauge(x,-.305,1.51)
        for xx in (x-.14,x+.14):cylinder((xx,-.299,1.28),(xx,-.319,1.28),.022,'Yellow',16)
        box((x,-.298,1.7),(.30,.007,.075),'Yellow')

def bench():
    for x in (-.81,.81):
        for y in (-.28,.28):box((x,y,.44),(.06,.06,.88),'Steel')
    box((0,0,.91),(1.8,.75,.07),'Timber')
    box((.48,0,.55),(.60,.60,.64),'Paint')
    for z in (.34,.55,.76):
        box((.48,-.314,z),(.53,.025,.17),'Paint')
        box((.48,-.340,z),(.21,.03,.02),'Steel')
    box((-.54,-.12,1.01),(.24,.22,.13),'Steel')
    box((-.54,-.12,1.12),(.31,.09,.09),'Steel')
    cylinder((-.73,-.12,1.1),(-.36,-.12,1.1),.013)
    for x in (-.20,.08):cylinder((x,0,.986),(x,.24,.986),.035,'Paint',20)
    box((0,.30,1.21),(1.76,.035,.55),'Paint')
    for i in range(5):cylinder((-.65+i*.21,.273,1.16),(-.65+i*.21,.273,1.40),.014,'Steel',12)

def cargo():
    for x in (-.75,0,.75):box((x,0,.10),(.15,1.12,.2),'Timber')
    for y in (-.49,-.245,0,.245,.49):box((0,y,.225),(1.9,.18,.05),'Timber')
    for x,y,z,sx,sy,sz in [(-.48,0,.70,.85,.99,.90),(.48,0,.61,.83,.99,.72),(-.40,.03,1.32,.70,.79,.34)]:
        box((x,y,z),(sx,sy,sz),'Timber')
        for xx in (x-sx*.36,x+sx*.36):
            box((xx,y,z+sz*.5+.003),(.055,sy+.012,.012),'Steel')
            for yy in (y-sy*.5-.005,y+sy*.5+.005):box((xx,yy,z),(.055,.012,sz),'Steel')
        box((x,y-sy*.5-.012,z),(.28,.012,.14),'Yellow')

def ducts():
    for y in (-.30,.30):box((0,y,.09),(1.8,.10,.18),'Steel')
    for x in (-.48,.48):
        # Hollow rectangular duct sections, including actual end flanges.
        for z in (.22,.84):box((x,0,z),(.73,.88,.025),'Paint')
        for xx in (x-.352,x+.352):box((xx,0,.53),(.025,.88,.60),'Paint')
        for y in (-.455,.455):
            for z in (.20,.86):box((x,y,z),(.81,.035,.04),'Steel')
            for xx in (x-.39,x+.39):box((xx,y,.53),(.04,.035,.70),'Steel')

def spares():
    box((0,0,.028),(.78,.48,.04),'Steel')
    for y in (-.22,.22):box((0,y,.065),(.78,.025,.08),'Paint')
    for x in (-.25,.05):cylinder((x,-.15,.12),(x,.16,.12),.065,'Steel')
    ring((.20,.06,.08),(0,0,1),.12,.02,'Rubber')
    box((-.15,-.02,.22),(.22,.22,.12),'Paint')

def panels():
    box((0,0,.018),(.86,.56,.03),'Paint',.08)
    box((.05,.04,.052),(.72,.47,.03),'Steel',-.22)
    for i in range(6):box((-.27+i*.105,-.01,.075),(.024,.30,.018),'Rubber',-.22)
    cylinder((-.32,-.23,.12),(.24,.14,.12),.045,'Paint')
    ring((.23,.16,.075),(0,0,1),.10,.011,'Steel')

def isolation():
    for x in (-.32,.32):
        cylinder((x,-.22,.018),(x,0,.83),.018,'Steel',16)
        cylinder((x,.22,.018),(x,0,.83),.018,'Steel',16)
    box((0,0,.64),(.74,.038,.28),'Yellow')
    for i in range(5):box((-.27+i*.135,-.026,.64),(.055,.012,.25),'Rubber',-.25)
    ring((.15,.13,.035),(0,0,1),.13,.017,'Rubber')

SPECS = [
    ('PumpSkid',pump,[((0,0,.65),(2.2,.95,1.30))]),
    ('FilterRack',rack,[((0,0,.90),(1.8,.65,1.80))]),
    ('PowerCabinet',cabinet,[((0,0,.96),(1.6,.68,1.92))]),
    ('RepairBench',bench,[((.48,0,.55),(.64,.64,.75)),((0,0,.91),(1.8,.75,.10))]),
    ('CargoStack',cargo,[((0,0,.64),(1.9,1.12,1.28)),((-.4,.03,1.32),(.7,.79,.34))]),
    ('DuctCradle',ducts,[((0,0,.46),(1.8,.94,.92))]),
    ('ServiceSpares',spares,[]),('AbandonedPanels',panels,[]),('IsolationStand',isolation,[]),
]
for index,(key,build,colliders) in enumerate(SPECS):
    V.clear();F.clear();MATERIALS.clear();SMOOTH.clear();build()
    name='SM_Facility_'+key
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(V,[],F);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    names=list(dict.fromkeys(MATERIALS))
    for mat in names:mesh.materials.append(MATS[mat])
    uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face,mat,smooth in zip(mesh.polygons,MATERIALS,SMOOTH):
        face.material_index=names.index(mat);face.use_smooth=smooth
        dims=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[dims[0]],p[dims[1]])
            age.data[li].color=(.18+.30*max(0,math.sin(p.x*7+p.y*3+p.z*11)),0,0,1)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bevel=obj.modifiers.new('Manufactured edge highlights','BEVEL');bevel.width=.003;bevel.segments=2;bevel.limit_method='ANGLE'
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    # Bevel interpolation may collapse an edge face's UV triangle. Author those
    # UVs on the final face plane so imported tangent space remains well defined.
    mesh=obj.data;uv=mesh.uv_layers.active.data
    for face in mesh.polygons:
        loops=list(face.loop_indices);a,b,c=(uv[i].uv.copy() for i in loops)
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1.e-10:continue
        dims=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
        for li in loops:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv[li].uv=(p[dims[0]],p[dims[1]])
    collision_objects=[]
    for number,(center,size) in enumerate(colliders):
        bpy.ops.mesh.primitive_cube_add(size=1,location=center)
        collision=bpy.context.object;collision.name=f'UCX_{name}_{number:02d}';collision.dimensions=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);collision_objects.append(collision)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for collision in collision_objects:collision.select_set(True)
    bpy.context.view_layer.objects.active=obj
    fbx=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(name=name,key=key,fbx=str(fbx),materials={'Facility_'+n:PATHS[n] for n in names},
                        collision_boxes=len(colliders),triangles=len(mesh.polygons),collision=bool(colliders)))
    obj.location=(index%3*3.2,index//3*3.2,0)
    for collision in collision_objects:collision.location+=obj.location;collision.hide_viewport=True;collision.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FacilityAssemblies.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,units='metres; imported as UE centimetres',
    source='Project-authored geometry; reuse existing facility material assets',tests_run=False),indent=2),encoding='utf-8')
print('FACILITY_ASSEMBLIES_AUTHORED',len(records),flush=True)
