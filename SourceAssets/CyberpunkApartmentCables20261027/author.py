"""Strip retired cable islands and author local connectors, trays and edge guides.
No preview, test scene or render is produced.
"""
from pathlib import Path
import sys,json,math,bpy,bmesh
from mathutils import Vector
R=Path(__file__).resolve().parent;P=R.parents[1];BASE=R.parent/'CyberpunkApartmentRebuild20261022'
sys.path[:0]=[str(R),str(BASE/'KitchenPilot20261024')]
import layout as l,model as g
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
OUT=R/'FBX';OUT.mkdir(exist_ok=True)
records=[]

def export(ob,key,source_actor=None,removed=0):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    ob.name='SM_AC_'+key
    tri=ob.modifiers.new('ExportTriangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    fbx=OUT/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',add_leaf_bones=False)
    records.append(dict(key=key,fbx=str(fbx),source_actor=source_actor,removed_cable_faces=removed,materials=[m.name for m in ob.data.materials],triangles=sum(len(f.vertices)-2 for f in ob.data.polygons)))

def strip(key,source,object_name,actor):
    with bpy.data.libraries.load(str(source),link=False) as (a,b):b.objects=[object_name]
    ob=b.objects[0];bpy.context.collection.objects.link(ob)
    # A wire is one disconnected island. Removing the entire selected island
    # preserves feet, mats, mouse wheels and unrelated rubber parts.
    bm=bmesh.new();bm.from_mesh(ob.data);remaining=set(bm.verts);deleted=[]
    while remaining:
        seed=remaining.pop();todo=[seed];verts=[seed]
        while todo:
            v=todo.pop()
            for e in v.link_edges:
                w=e.other_vert(v)
                if w in remaining:remaining.remove(w);todo.append(w);verts.append(w)
        faces={f for v in verts for f in v.link_faces}
        if not faces:continue
        materials={ob.data.materials[f.material_index].name for f in faces}
        rubber=all('Rubber' in s for s in materials);dark=all('Dark' in s for s in materials)
        lo=[min(v.co[i] for v in verts) for i in range(3)];hi=[max(v.co[i] for v in verts) for i in range(3)]
        remove=False
        if key in ('WritingDesk','CyberWorkstation'):remove=rubber and lo[1]>.24 and lo[2]>.65 and hi[2]>1.1
        elif key=='DeskCableTray':remove=rubber or (lo[2]>.66 and hi[2]<.71 and hi[0]-lo[0]>.16 and hi[0]-lo[0]<.18)
        elif key=='Headphones':remove=rubber and lo[2]<.03 and hi[2]<.12 and hi[0]>.12
        elif key=='Treadmill':
            remove=rubber and ((lo[1]>.75 and hi[1]>1.04 and hi[2]<.16) or (lo[1]>.25 and hi[1]<.40 and lo[2]>.93 and hi[2]>1.15 and hi[2]<1.17))
        elif key=='PracticalLights':remove=dark and lo[2]>2.41 and hi[2]>3.68 and hi[0]-lo[0]<.011 and lo[1]>10.27
        if remove:deleted.extend(faces)
    removed=len(deleted)
    if not removed:raise RuntimeError('Source cable islands not found: '+key)
    bmesh.ops.delete(bm,geom=deleted,context='FACES');bm.to_mesh(ob.data);bm.free();ob.data.update()
    ob['CableRevision']='ApartmentPhysicalCables20261027';export(ob,key,actor,removed)
    print('CABLE_SOURCE_REPLACED',key,removed,flush=True)

for key,actor in [('WritingDesk','AP_Bed2_Desk'),('CyberWorkstation','AP_Office_Workstation'),('Treadmill','AP_Gym_Treadmill')]:
    strip(key,BASE/'RefinementV3/CyberpunkApartment_Rebuild.blend','SM_AP_'+key,actor)
for key,actor in [('Headphones','BP_Headphones'),('DeskCableTray','BP_DeskCableTray')]:
    strip(key,BASE/'BedroomPilot20261024/RefinementV3/BedroomPilot_Source.blend','SM_BP_'+key,actor)
strip('PracticalLights',BASE/'RefinementV2/CyberpunkApartment_Rebuild.blend','SM_AP_PracticalLights','AP_PracticalLights')

g.G.clear();g.M={}
for role,color in [('Rubber',(.016,.019,.023,1)),('Graphite',(.035,.042,.05,1)),('Steel',(.35,.39,.42,1))]:
    m=bpy.data.materials.new('KP_'+role);m.diffuse_color=color;g.M[role]=m

def port(k,p,n,width=.014):
    """Ribbed plug with flush collar; p is the wire's exact outgoing centre."""
    p=Vector(p);n=Vector(n).normalized()
    g.cyl(k,p-n*.040,p-n*.018,width,'Graphite',24)
    g.cyl(k,p-n*.020,p-n*.009,width*.70,'Rubber',24)
    for t in (.004,.008,.012):g.ring(k,p-n*t,n,width*.47,width*.30,.0016,'Rubber',24)
    g.cyl(k,p-n*.013,p,width*.32,'Rubber',20)

def edge(k,x,h):
    # Begins 2 cm above the slab, follows a 3 cm radius around the rear lip,
    # then opens below the underside. The live cable never cuts a slab corner.
    pts=[]
    for j in range(17):
        t=j/16;pts.append((x,h-.018+.023*t,.8125+.010*(3*t*t-2*t*t*t)))
    for j in range(1,33):
        a=j*math.pi/64;pts.append((x,h+.005+.030*math.sin(a),.7925+.030*math.cos(a)))
    pts.append((x,h+.035,.715));g.tube(k,pts,.0021,'Rubber',20)
    # Clamp attached to the desk's lower rear lip; no invisible oversize blocker.
    g.box(k,(x,h-.002,.754),(.022,.022,.015),'Graphite',.004)
    g.cyl(k,(x,h+.010,.754),(x,h+.016,.754),.004,'Steel',20)

for d in l.DESKS:
    k=d['room']+'DeskRouting';h=d['half'];w=d['w']
    # Small dock and enclosed power strip in the rear service channel.
    g.box(k,(-.25,h+.013,.69),(.38,.044,.038),'Graphite',.008)
    g.box(k,(-.25,h+.018,.65),(.42,.054,.020),'Graphite',.005)
    for x in (-.42,-.08):
        g.box(k,(x,h-.035,.729),(.019,.12,.012),'Steel',.003)
        g.box(k,(x,h+.016,.712),(.019,.018,.047),'Steel',.003)
    for i,x in enumerate(d['xs']):
        x+=.075;port(k,(x,.255,1.12),(0,1,0),.009);edge(k,x,h)
        port(k,(-.36+i*.08,h+.035,.690),(0,1,0),.009)
    for side,x in [('L',-w/2+.13),('R',w/2-.13)]:
        port(k,(x,.237,.86),(0,1,0),.009);edge(k,x,h)
    for x in (-.40,-.25,-.18,-.10):port(k,(x,h+.045,.67),(0,1,0),.011)
    port(k,(-.03,h+.035,.69),(0,1,0),.009)
    if d['room']=='Bed2':edge(k,.56,h);port(k,(-.25,.385,.65),(0,1,0),.008)
    # Slim tray under the new channel; the detailed existing Bed2 tray remains.
    if d['room']!='Bed2':g.box(k,(-.25,h-.04,.638),(.50,.15,.012),'Graphite',.004)

port('PCPorts',(-.06,.265,.40),(0,1,0),.011)
port('PCPorts',(.06,.265,.12),(0,1,0),.014)
port('HeadphoneSocket',(.092,0,.085),(0,0,-1),.007)
port('WasherSocket',(-.24,.345,.70),(0,1,0),.014)
port('FridgeSocket',(.21,.409,.23),(0,1,0),.015)
port('GymRouting',(-.46,.77,.14),(-1,0,0),.014)
g.pipe('GymRouting',[(-.46,.77,.14),(-.50,.78,.14),(-.50,.85,.09)],.00325,'Rubber',20)
port('GymRouting',(.27,.38,1.16),(0,-1,0),.008)
port('GymRouting',(.17,.382,1.14),(0,-1,0),.008)
g.box('GymRouting',(.17,.407,1.14),(.027,.015,.028),'Graphite',.005)

# World terminals share a mesh at the world origin. Points converted from UE cm
# to Blender metres once; door/desk attachments above remain local.
def bp(p):return (p[0]/100,-p[1]/100,p[2]/100)
def bn(n):return (n[0],-n[1],n[2])
def wallbox(p,n):
    c=Vector(bp(p));v=Vector(bn(n));dims=(.018,.092,.11) if abs(v.x)>.5 else (.092,.018,.11)
    g.box('WorldTerminals',c,dims,'Graphite',.006)
    # screw heads and one moulded plug, ending 3.8 cm in front of plate.
    for z in (-.037,.037):g.cyl('WorldTerminals',c+Vector((0,0,z)),c+Vector((0,0,z))+v*.012,.003,'Steel',20)
    port('WorldTerminals',c+v*.038,v,.016)
for d in l.DESKS:wallbox(d['wall'],d['normal'])
wallbox([24.2,-1330,110],[1,0,0]);wallbox([1120,-2038.5,125],[0,1,0])
g.box('WorldTerminals',bp([2113.3,-652.5,55]),(.018,.14,.11),'Graphite',.006)
for p in ([2109.5,-650,55],[2109.5,-655,55]):port('WorldTerminals',bp(p),(-1,0,0),.011)
for p in ([2103,-630,89],[2103,-635,89]):port('WorldTerminals',bp(p),(0,0,-1),.011)
g.box('WorldTerminals',bp([285,-2160,.7]),(.09,.12,.014),'Steel',.005)
port('WorldTerminals',bp([285,-2160,3.4]),(0,0,1),.018)

# g.finish supplies metre UVs and triangulation while retaining compact groups.
collection=bpy.data.collections.new('KIT_Source');bpy.context.scene.collection.children.link(collection)
new=g.finish(g.M,R)
for row in new:
    ob=bpy.data.objects['KIT_'+row['key']]
    # Export under scoped names, avoiding accidental use of the kitchen assets.
    export(ob,row['key'])
(R/'geometry.json').write_text(json.dumps(dict(meshes=records,routes=l.ROUTES,hardware=l.HARDWARE,replacements=l.REPLACEMENTS),indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ApartmentCables_Source.blend'))
print('APARTMENT_CABLE_SOURCE_SAVED',len(records),len(l.ROUTES),flush=True)
