"""Refit the V6 bench in its authored metre-space. Run with Blender in background."""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector, kdtree

OUT = Path(__file__).resolve().parent
ASSETS = OUT.parent
SOURCE = ASSETS / 'WoodworkingBenchV6Controls20261013'
GAME = ASSETS.parent / 'Saved/WoodworkingCrystalBench/GeometryBake'
GAME.mkdir(parents=True,exist_ok=True)
DEST = OUT / 'GameReady'
DEST.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'GameReady/WoodworkingBench_NoGuard_RedEdge.blend'))
record = json.loads((SOURCE / 'layout_manifest.json').read_text())
original = json.loads((ASSETS / 'WoodworkingBenchV4/ProductionRecords/blend_inspection.json').read_text())
scene = bpy.context.scene
wood, end, iron, steel, leather, brass, gem = (
    'WSBench_BenchWood', 'WSBench_EndGrain', 'WSDetail_RackPaint', 'WSSculpt_Machined',
    'WSSculpt_RubberGrip', 'CrystalBrass', 'CrystalCore')
for name, color in [(brass,(.36,.20,.07,1)),(gem,(.035,.34,.27,1))]:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color

# Mesh components authored in metre space; surface UVs follow each part's local axes.
parts = []
def piece(name, verts, faces, material, transform=None, bevel=0., caps=None):
    transform = transform or Matrix.Identity(4)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(bpy.data.materials[material])
    if caps:
        mesh.materials.append(bpy.data.materials[caps])
    mesh.update()
    if bevel:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2,
                        affect='EDGES', profile=.5, clamp_overlap=True)
        bm.normal_update()
        bm.to_mesh(mesh)
        bm.free()
    uv = mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        normal = face.normal
        axis = max(range(3), key=lambda j: abs(normal[j]))
        if caps and abs(normal.x) > .985:
            face.material_index = 1
        a, b = [(1,2),(0,2),(0,1)][axis]
        for li in face.loop_indices:
            p = mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv = ((p[a] * 2.2)+.13, (p[b] * 2.2)+.39)
    mesh.transform(transform)
    ob = bpy.data.objects.new(name,mesh)
    scene.collection.objects.link(ob)
    parts.append(ob)
    return ob

def oriented(p, q, track):
    a,b = Vector(p),Vector(q)
    normal_axis = 'Y' if track == 'Z' else 'Z'
    rot = (b-a).to_track_quat(track,normal_axis).to_matrix().to_4x4()
    return Matrix.Translation((a+b)*.5) @ rot, (b-a).length

def bar(name, p, q, w, h, mat, chamfer, ends=None):
    t, length = oriented(p,q,'X')
    x,y,z = length*.5,w*.5,h*.5
    verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return piece(name,verts,faces,mat,t,chamfer,ends)

def revolved(name, p, q, profile, mat, n=24, open_center=False):
    # Axial fraction, outside radius. A ring returns through its inner profile.
    t,length = oriented(p,q,'Z')
    verts=[(r*math.cos(math.tau*j/n),r*math.sin(math.tau*j/n),(k-.5)*length)
           for k,r in profile for j in range(n)]
    steps=len(profile)
    faces=[(i*n+j,i*n+(j+1)%n,((i+1)%steps)*n+(j+1)%n,((i+1)%steps)*n+j)
           for i in range(steps if open_center else steps-1) for j in range(n)]
    if not open_center:
        faces.extend([tuple(reversed(range(n))),tuple(range((steps-1)*n,steps*n))])
    return piece(name,verts,faces,mat,t)

def pin(name,p,q,r,mat,n=16):
    return revolved(name,p,q,[(0,r*.88),(.08,r),(.92,r),(1,r*.88)],mat,n)

def collar(name,p,q,r,mat,facets=32):
    return revolved(name,p,q,[(0,r*.91),(.14,r),(.86,r),(1,r*.91),(1,r*.76),(0,r*.76)],mat,facets,True)

def mineral(name, rings, mat, n, rotation):
    # Separate uneven termination faces, with stepped shoulders and a split point.
    verts=[]
    for i,(x,y,z,r) in enumerate(rings):
        for j in range(n):
            a=rotation+math.tau*j/n+(.022 if i%3==1 else 0.)
            scale=1+.075*math.sin(j*2.31+.8)
            verts.append((x+math.cos(a)*r*scale,y+math.sin(a)*r*.82*scale,
                          z+r*.095*math.sin(j*1.91+.4*i)))
    faces=[tuple(reversed(range(n)))]
    for i in range(len(rings)-1):
        for j in range(n):
            a,b=i*n+j,i*n+(j+1)%n
            c,d=b+n,a+n
            if i==len(rings)-2 or (i==1 and j%3==0):
                faces.extend([(a,b,c),(a,c,d)])
            else:
                faces.append((a,b,c,d))
    faces.append(tuple(range((len(rings)-1)*n,len(rings)*n)))
    return piece(name,verts,faces,mat)

# The treadle-era joinery is carried by the existing frame. Broad rails tuck just
# behind the worktop arris. Each shoulder is pinned to the stiles below the top.
for x in (.499,1.161):
    bar('Saw side oak apron',(x,-1.247,.833),(x,1.229,.833),.058,.102,wood,.004,end)
    for y in (-1.236,1.225):
        tip = y + (.195 if y<0 else -.195)
        bar('Housed knee',(x,y,.642),(x,tip,.802),.039,.051,wood,.0028,end)
    for y in (-1.215,-1.178,1.197,1.158):
        direction = -1 if x<.6 else 1
        side=x+direction*.029
        for z in (.812,.852):
            pin('Drawbored oak peg',(side-direction*.004,y,z),(side+direction*.001,y,z),.0058,end,10)
for y in (-1.25,-.676):
    bar('Tool wing apron',(-1.166,y,.830),(.405,y,.830),.043,.085,wood,.0035,end)
    for x in (-1.144,.372):
        inner=x+(.152 if x<0 else -.152)
        bar('Tool wing knee',(x,y,.686),(inner,y,.801),.034,.043,wood,.002,end)
        for z in (.809,.847):
            pin('Wing peg',(x,y-.018,z),(x,y-.025,z),.0052,end,10)
# Small wrought corner straps share the physical post faces, with upset heads.
for x,y in ((.499,1.235),(1.162,1.235),(-1.158,-1.252)):
    sign=1 if y>0 else -1
    face=y+sign*.033
    bar('Corner shoe',(x-.025,face,.839),(x+.025,face,.839),.005,.079,iron,.0016)
    for z in (.817,.858):
        pin('Peened nail',(x,face,z),(x,face+sign*.005,z),.005,steel,7)

# The carriage is hung below the original saw assembly. The crystal clears the
# control face and the stored fence. Its collar transfers power to the arbor.
cx,cy=.623,-.014
for x in (.535,.728):
    for y in (-.112,.098):
        bar('Suspension lug',(x,y-.023,.867),(x,y+.023,.867),.036,.016,iron,.0025)
        pin('Lug rivet',(x,y,.856),(x,y,.866),.009,brass,10)
    bar('Rear hanger',(x,.100,.873),(x,.097,.488),.020,.017,iron,.002)
    bar('Forward diagonal hanger',(x,-.108,.868),(x,-.119,.487),.013,.016,iron,.002)
    bar('Cradle side rail',(x,-.136,.481),(x,.12,.481),.024,.022,iron,.002)
for y in (-.112,.098):
    bar('Cradle crossbeam',(.523,y,.483),(.744,y,.483),.033,.030,wood,.003,end)
bar('Crystal plinth',(cx,-.124,.502),(cx,.107,.502),.175,.026,wood,.004,end)
revolved('Stepped bronze socket',(cx,cy,.512),(cx,cy,.548),
         [(0,.073),(.13,.08),(.25,.08),(.39,.063),(.67,.06),(.84,.068),(1,.065)],brass,12)
mineral('Master crystal',[(cx,cy,.531,.048),(cx,cy,.558,.066),
                         (cx-.009,cy+.002,.688,.065),(cx-.013,cy+.006,.707,.055),
                         (cx-.028,cy+.003,.764,.006)],gem,7,.28)
mineral('Growth along main prism',[(cx+.036,cy-.013,.537,.020),
                                  (cx+.05,cy-.026,.599,.023),
                                  (cx+.069,cy-.036,.638,.004)],gem,5,.7)
for i in range(3):
    a=.40 + math.tau*i/3
    def point(r,z):return (cx+r*math.cos(a),cy+r*math.sin(a),z)
    bar('Forged talon root',point(.051,.52),point(.079,.575),.015,.014,brass,.002)
    bar('Recurved claw',point(.079,.575),point(.064,.615),.014,.011,brass,.0018)
    pin('Retaining tip',point(.064,.615),point(.059,.620),.006,steel,8)
# An open three-legged collector cups the tip; rear foot is a through-pin into
# the hung frame. Unequal lengths follow the off-axis natural point.
for i in range(3):
    a=math.tau*i/3+.5
    p=(.604+.047*math.cos(a),cy+.047*math.sin(a),.723)
    q=(.604+.053*math.cos(a),cy+.053*math.sin(a),.750)
    r=(.604+.017*math.cos(a),cy+.017*math.sin(a),.782)
    bar('Collector petal',p,q,.013,.010,brass,.002)
    bar('Collector shoulder',q,r,.013,.010,brass,.002)
revolved('Collector stem',(.604,cy,.774),(.604,cy,.805),
         [(0,.022),(.1,.025),(.35,.025),(.48,.014),(.83,.014),(1,.018)],steel,18)
bar('Collector support',(.603,.099,.791),(.604,cy,.791),.029,.025,iron,.003)
pin('Driven spindle',(.592,cy,.806),(.759,cy,.806),.011,steel)
pin('Arbor stub',(.712,0,.888),(.856,0,.888),.012,steel)
for z,y in ((.806,cy),(.888,0)):
    revolved('Grooved pulley',(.707,y,z),(.739,y,z),
             [(0,.026),(.09,.031),(.17,.031),(.24,.026),(.76,.026),(.83,.031),(.92,.031),(1,.026)],brass)
    pin('Shaft end key',(.701,y,z),(.71,y,z),.009,steel,6)
# An endless leather strap follows the tangent of both wheels.
def belt():
    x=.723
    dy,dz=-cy,.888-.806
    angle=math.atan2(dz,dy)
    verts=[]
    for xx,r in ((x-.007,.029),(x+.007,.029),(x+.007,.026),(x-.007,.026)):
        for y,z,start in ((0.,.888,angle-math.pi/2),(cy,.806,angle+math.pi/2)):
            for j in range(13):
                a=start+math.pi*j/12
                verts.append((xx,y+r*math.cos(a),z+r*math.sin(a)))
    size=26
    faces=[(i*size+j,((i+1)%4)*size+j,((i+1)%4)*size+(j+1)%size,i*size+(j+1)%size)
           for i in range(4) for j in range(size)]
    piece('Endless arbor strap',verts,faces,leather)
belt()
# Replace the lathe's secondary electric unit with a scaled reserve crystal.
xx,yy=.692,-.802
revolved('Reserve lathe cup',(xx,yy,.249),(xx,yy,.286),
         [(0,.037),(.12,.041),(.23,.041),(.43,.032),(.8,.029),(1,.034)],brass,12)
mineral('Lathe reserve prism',[(xx,yy,.28,.024),(xx,yy,.295,.033),
        (xx+.011,yy,.350,.032),(xx+.018,yy-.002,.382,.003)],gem,6,.6)
bar('Lathe contact bridge',(.621,yy,.342),(.686,yy,.342),.017,.019,iron,.0018)
for dr in (-1,1):
    bar('Reserve socket claw',(xx+dr*.023,yy,.275),(xx+dr*.031,yy,.314),.008,.009,brass,.0013)
# A pull lever and two roughly coin-sized indicators occupy the old control
# bracket, leaving the position of the original controls recognizable.
bar('Lever mounting block',(.445,-.215,.80),(.445,-.044,.80),.052,.102,wood,.004,end)
bar('Control bracket saddle',(.462,-.13,.817),(.472,-.13,.869),.047,.018,iron,.002)
revolved('Lever socket',(.423,-.166,.802),(.409,-.166,.802),
         [(0,.03),(.16,.034),(.45,.034),(.64,.024),(1,.023)],brass,16)
bar('Lever handle',(.410,-.166,.802),(.385,-.164,.839),.009,.012,steel,.001)
pin('Turned lever grip',(.388,-.164,.837),(.38,-.164,.847),.010,wood,10)
for y,r in ((-.082,.013),(-.118,.006)):
    pin('Indicator bezel',(.422,y,.805),(.415,y,.805),r,brass)
    pin('Indicator lens',(.415,y,.805),(.412,y,.805),r*.68,gem,8)
for y in (-.205,-.055):
    for z in (.765,.833):
        pin('Face fixing',(.421,y,z),(.417,y,z),.0045,brass,8)

# Source-part lookup is in world space because the V5 rearrangement moved the
# editable lower-shelf tools along with their baked vertices.
remove_names=[]
for entry in original['objects']:
    n=entry['name']
    group=entry.get('props',{}).get('layout_group')
    if group=='SawControls' or (group=='UnderTableDrive' and not n.startswith(('Enclosed blade chamber','Blade chamber','Chamber access'))):
        remove_names.append(n)
    elif group=='WoodLathe' and (n.startswith(('Covered motor','Motor ','Headstock belt cover','Belt cover bolt','Power switch','Lathe small serial plate','Lathe serial legend'))):
        remove_names.append(n)
deps=bpy.context.evaluated_depsgraph_get()
samples=[]
for n in remove_names:
    ob=bpy.data.objects[n]
    ev=ob.evaluated_get(deps)
    mesh=ev.to_mesh()
    samples.extend(ob.matrix_world@v.co for v in mesh.vertices)
    ev.to_mesh_clear()
lookup=kdtree.KDTree(len(samples))
for i,v in enumerate(samples):lookup.insert(v,i)
lookup.balance()

def strip_source(target):
    mesh=target.data
    removed={v.index for v in mesh.vertices if lookup.find(target.matrix_world@v.co)[2] < .000015}
    faces=[p for p in mesh.polygons if not all(i in removed for i in p.vertices)]
    count=len(mesh.polygons)-len(faces)
    used=sorted({j for p in faces for j in p.vertices})
    remap={old:i for i,old in enumerate(used)}
    loops=[li for p in faces for li in p.loop_indices]
    stripped=bpy.data.meshes.new(target.name+'_WithDriveRemoved')
    stripped.from_pydata([mesh.vertices[i].co for i in used],[],[[remap[i] for i in p.vertices] for p in faces])
    for mat in mesh.materials:stripped.materials.append(mat)
    for current,old in zip(stripped.polygons,faces):
        current.material_index=old.material_index
        current.use_smooth=old.use_smooth
    for layer in mesh.uv_layers:
        lay=stripped.uv_layers.new(name=layer.name)
        for i,old in enumerate(loops):lay.data[i].uv=layer.data[old].uv
    for attr in mesh.color_attributes:
        new=stripped.color_attributes.new(name=attr.name,type=attr.data_type,domain=attr.domain)
        for i,old in enumerate(used if attr.domain=='POINT' else loops):new.data[i].color=attr.data[old].color
    stripped.update()
    stripped.normals_split_custom_set([mesh.corner_normals[i].vector.copy() for i in loops])
    target.data=stripped
    return count

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]

def collision(name,box,i):
    low,hi=Vector(box['min']),Vector(box['max'])
    bpy.ops.mesh.primitive_cube_add(size=1,location=(low+hi)*.5)
    ob=bpy.context.object
    ob.name=f'UCX_{name}_{i:02}'
    ob.dimensions=[max(.003,b-a) for a,b in zip(low,hi)]
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return ob

def export(obj,cols):
    records=[]
    for lod,ratio in ((0,1.),(1,.55),(2,.24)):
        part=obj
        if lod:
            part=obj.copy()
            part.data=obj.data.copy()
            scene.collection.objects.link(part)
            select([part])
            dec=part.modifiers.new('Distance only','DECIMATE')
            dec.ratio=ratio
            dec.use_collapse_triangulate=True
            dec.delimit={'MATERIAL','UV','NORMAL'}
            bpy.ops.object.modifier_apply(modifier=dec.name)
        select([part]+(cols if lod==0 else []))
        dest=GAME/f'{obj.name}_LOD{lod}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(dest),use_selection=True,object_types={'MESH'},
            axis_forward='-Y',axis_up='Z',global_scale=1,apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=True,mesh_smooth_type='FACE',
            use_tspace=True,use_triangles=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
        part.data.calc_loop_triangles()
        records.append({'file':dest.name,'triangles':len(part.data.loop_triangles)})
        if lod:bpy.data.objects.remove(part,do_unlink=True)
    return records

import shutil
targets=[]
products=[]
bounds=record['collision_boxes_m']
for r in record['meshes']:
    name=r['name']
    obj=bpy.data.objects[name]
    targets.append(obj)
    if name.endswith('SawBlade'):
        # The original independent blade already has all three authored LODs,
        # radial guide material and pivot-local geometry.
        files=[]
        for lod,count in enumerate(r['lod_triangles']):
            filename=f'{name}_LOD{lod}.fbx'
            shutil.copyfile(SOURCE/'GameReady'/filename,GAME/filename)
            files.append(dict(file=filename,triangles=count))
        products.append(dict(name=name,removed_faces=0,files=files,material_slots=r['material_slots']))
        continue
    removed=strip_source(obj)
    if removed==0:raise RuntimeError('Missing drive donor surface on '+name)
    # Append named slots consistently across the combined and body meshes.
    for slot in (gem,brass):obj.data.materials.append(bpy.data.materials[slot])
    extras=[]
    for part in parts:
        copy=part.copy()
        copy.data=part.data.copy()
        if obj.data.uv_layers and copy.data.uv_layers:
            copy.data.uv_layers[0].name=obj.data.uv_layers[0].name
        scene.collection.objects.link(copy)
        extras.append(copy)
    select([obj]+extras)
    bpy.ops.object.join()
    cols=[collision(name,b,i) for i,b in enumerate(bounds)]
    files=export(obj,cols)
    for col in cols:bpy.data.objects.remove(col,do_unlink=True)
    products.append(dict(name=name,removed_faces=removed,files=files,
                         material_slots=[m.name for m in obj.data.materials],
                         simple_collision_hulls=len(cols)))
# A separate hidden collection keeps the crystal cradle and woodwork editable.
details=bpy.data.collections.new('Crystal refit - editable parts')
scene.collection.children.link(details)
for ob in parts:
    for c in list(ob.users_collection):c.objects.unlink(ob)
    details.objects.link(ob)
details.hide_viewport=True
details.hide_render=True
for ob in list(bpy.data.objects):
    if ob not in targets and ob not in parts:bpy.data.objects.remove(ob,do_unlink=True)
for obj in targets:
    if not scene.collection in obj.users_collection:scene.collection.objects.link(obj)
    for coll in list(obj.users_collection):
        if coll != scene.collection:coll.objects.unlink(obj)
    inactive=obj!=targets[0]
    obj.hide_set(inactive)
    obj.hide_render=inactive
select(targets[:1])
bpy.data.orphans_purge(do_recursive=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(GAME/'WoodworkingCrystalBench.blend'),compress=True)
for output in GAME.iterdir():
    if output.suffix.lower() in ('.fbx','.blend'):
        output.replace(DEST/output.name)
receipt={'source':str(SOURCE.relative_to(ASSETS.parent)),'blade_pivot_cm':record['blade_pivot_cm'],
         'removed_source_parts':remove_names,'authored_parts':[p.name for p in parts],'meshes':products}
(OUT/'geometry-export.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('CRYSTAL_BENCH_EXPORTED',flush=True)
