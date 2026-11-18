"""Background Blender authoring of simple oak village furnishings; no rendering."""
import bpy, math, json, random
from pathlib import Path
from mathutils import Matrix

out=Path(__file__).resolve().parents[3]/'SourceAssets/HillsVillageBlacksmith20261117/Authored'
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
rng=random.Random(171117)
materials={name:bpy.data.materials.new(name) for name in ('Oak','Iron','Linen','Stone','Sign','Closed')}
parts=[];manifest=[]

def box(name,center,size,material='Oak',bevel=.35,angle=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(center[0]/100,-center[1]/100,center[2]/100))
    o=bpy.context.object;o.name=name;o.dimensions=[d/100 for d in size]
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('Worn edges','BEVEL');m.width=bevel/100;m.segments=2
        bpy.ops.object.modifier_apply(modifier=m.name)
    o.rotation_euler.z=-math.radians(angle)
    o.data.materials.append(materials[material]);parts.append(o)
    return o

def export(name):
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    o=parts[0];o.name='SM_Village'+name
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
    uv=o.data.uv_layers.active or o.data.uv_layers.new(name='SurfaceMetres')
    for f in o.data.polygons:
        axis=max(range(3),key=lambda i:abs(f.normal[i]))
        for idx in f.loop_indices:
            x,y,z=o.data.vertices[o.data.loops[idx].vertex_index].co
            uv.data[idx].uv=(y,z) if axis==0 else ((x,z) if axis==1 else (x,y))
    # Sign faces use a full, non-mirrored label on both sides.
    if name in ('BlacksmithSign','ClosedPlaque'):
        width,height=(100,44) if name=='BlacksmithSign' else (48,20)
        for f in o.data.polygons:
            if o.data.materials[f.material_index].name in ('Sign','Closed'):
                for idx in f.loop_indices:
                    x,y,z=o.data.vertices[o.data.loops[idx].vertex_index].co
                    uv.data[idx].uv=(x*100/width+.5,z*100/height+.5)
    bpy.ops.export_scene.fbx(filepath=str(out/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    manifest.append(dict(name=o.name,slots=[m.name for m in o.data.materials],pieces=len(parts)))
    o.location=((len(manifest)-1)%4*3.5,(len(manifest)-1)//4*3.5,0);parts.clear()

def legs(width,depth,height):
    for x in (-width/2+8,width/2-8):
        for y in (-depth/2+8,depth/2-8):
            box('tapered post',(x,y,height/2),(7,7,height))
            for z in (10,height-10):box('square nail',(x,y-3.6,z),(1.1,.4,1.1),'Iron',.1)

# 130 x 72 cm dining/work table with individual planks, trestles and pegged braces.
for y in range(4):box('table plank',(0,(y-1.5)*18,74),(130,17.5,5),bevel=.55)
legs(120,64,72)
box('long apron',(0,-27,65),(110,5,12));box('long apron',(0,27,65),(110,5,12))
box('stretcher',(0,0,26),(112,6,8));export('OakTable')

# Open 150 x 42 x 170 cm storage rack, no modern fittings.
for x in (-70,70):
    for y in (-17,17):box('shelf post',(x,y,85),(6,6,170))
for z in (12,64,116,164):
    for y in (-10,10):box('shelf board',(0,y,z),(150,19.5,3))
    box('front shelf bearer',(0,-18,z-4),(144,5,5))
box('rear rail',(0,18,96),(144,3,10));export('OakShelf')

# Low timber bed: 205 x 106 cm, worn linen mattress with a separate pillow.
legs(197,98,38)
for x in (-49,49):box('bed side rail',(x,0,33),(7,205,14))
for y in range(9):box('bed slat',(0,-88+y*22,36),(95,18,4))
for z in (42,58):box('headboard',(0,98,z),(106,6,14))
box('mattress',(0,0,45),(94,191,13),'Linen',4)
box('pillow',(0,66,55),(66,36,11),'Linen',5)
for y in (-72,-48,-23,4):box('blanket soft fold',(0,y,52),(93,3.4,2),'Linen',1.2)
export('TimberBed')

legs(40,36,43)
for y in (-10,10):box('stool seat',(0,y,44),(46,19.7,4),bevel=.7)
export('OakStool')

# Stock bundles stay outside the work surface and forge operating clearance.
for row in range(3):
    for col in range(4-row):box('iron bar',((col-(3-row)/2)*9,0,3+row*5),(7,72-rng.random()*10,4),'Iron',.5)
export('IronStock')
for i in range(6):box('fallen offcut',(rng.uniform(-25,25),rng.uniform(-15,15),2+i*2),
    (rng.uniform(55,85),rng.uniform(8,15),3),'Oak',.6,rng.uniform(-28,28))
export('AbandonedTimber')
for x in (-80,0,80):
    for y in (-45,45):box('stone hearth slab',(x,y,3),(79.5,89.5,6),'Stone',.8)
export('HearthPad')

# Board faces are geometry, not decals, so they never project onto players/weapons.
for name,width,height,slot in [('BlacksmithSign',100,44,'Sign'),('ClosedPlaque',48,20,'Closed')]:
    box('sign backing',(0,0,0),(width,4,height),'Oak',.8)
    box('lettered face',(0,-2.15,0),(width-.8,.2,height-.8),slot,0)
    for x in (-width/2+4,width/2-4):
        for z in (-height/2+4,height/2-4):box('forged pin',(x,-2.45,z),(1.2,.5,1.2),'Iron',.15)
    if name=='BlacksmithSign':
        for x in (-30,30):box('hanger',(x,1,29),(2,2,18),'Iron',.2)
        box('wall hanging rail',(0,8,38),(80,18,3),'Iron',.3)
    export(name)
(out/'furniture-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'VillageFurniture.blend'))
