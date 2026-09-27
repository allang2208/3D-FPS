"""Meshy natural wood + exact retained grip + authored quartz/hemp interfaces.
Background model production/export only. All mesh coordinates are UE cm.
"""
import bpy, bmesh, json, math, statistics, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Export';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
from solid_geometry import close_mesh,wood_uv,wood_material,repair_degenerate_uvs
bpy.ops.import_scene.gltf(filepath=str(ROOT.parent/'BranchCrystalV18/Meshy/staff/downloads/model_urls_glb.glb'))
imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
def join(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    if len(objects)>1:bpy.ops.object.join()
    obj=objects[0];obj.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return obj

raw=join(imported,'Meshy_OriginalMaster')
lo=Vector([min(v.co[i] for v in raw.data.vertices) for i in range(3)])
hi=Vector([max(v.co[i] for v in raw.data.vertices) for i in range(3)])
axis=max(range(3),key=lambda i:hi[i]-lo[i])
turn=Vector([int(i==axis) for i in range(3)]).rotation_difference(Vector((0,0,1)))
for v in raw.data.vertices:v.co=turn@v.co
zlo=min(v.co.z for v in raw.data.vertices);zhi=max(v.co.z for v in raw.data.vertices)
scale=160/(zhi-zlo)
center=Vector((statistics.median(v.co.x for v in raw.data.vertices),statistics.median(v.co.y for v in raw.data.vertices),0))
for v in raw.data.vertices:v.co=Vector(((v.co.x-center.x)*scale,(v.co.y-center.y)*scale,(v.co.z-(zlo+zhi)*.5)*scale))
top=statistics.median(v.co.xy.length for v in raw.data.vertices if v.co.z>60)
bottom=statistics.median(v.co.xy.length for v in raw.data.vertices if v.co.z<-60)
if bottom>top:
    for v in raw.data.vertices:v.co.z=-v.co.z
raw['provider']='Meshy 7.1';raw['task_id']=json.loads((ROOT.parent/'BranchCrystalV18/Meshy/staff/task.json').read_text())['task_id']
wood_mat=wood_material(ROOT,'M_Staff_BranchWoodV19')
raw.data.materials.clear();raw.data.materials.append(wood_mat)
for p in raw.data.polygons:p.material_index=0
close_mesh(raw)

def copy(obj,name):
    result=obj.copy();result.data=obj.data.copy();bpy.context.collection.objects.link(result);result.name=name;return result
def clip(obj,zmin,zmax):
    close_mesh(obj)
    bm=bmesh.new();bm.from_mesh(obj.data)
    for z,normal in [(zmin,(0,0,1)),(zmax,(0,0,-1))]:
        cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,
            plane_co=(0,0,z),plane_no=normal,clear_inner=True,clear_outer=False)
        edges=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
        if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
    close_mesh(obj)
    return obj

# The generated rope/crystal remain in the source master; precision replacements
# occupy the existing neck interface. Bare generated wood stops below its rope.
shaft=clip(copy(raw,'AuthoredBranchShaft'),-81,43)
for v in shaft.data.vertices:v.co.z=-80+(v.co.z+80)*(144.65/123)
# Meshy's long bark triangles must be split at the deformation stations so
# fitted sections bend continuously instead of cutting across the neck/grip.
bm=bmesh.new();bm.from_mesh(shaft.data)
for z in sorted(set(list(range(-78,65,2))+[14,22,42,50,54,61,62])):
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,
        plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=False,clear_outer=False)
bm.to_mesh(shaft.data);bm.free();shaft.data.update()
# Keep the natural centerline bends small enough for the existing radial
# attachment lanes; lateral generation drift is not part of the grip contract.
stations=[]
shaft.data.calc_loop_triangles()
segments=[]
for edge in shaft.data.edges:
    a,b=[shaft.data.vertices[i].co.copy() for i in edge.vertices]
    if abs(a.z-b.z)>.00001:segments.append((min(a.z,b.z),max(a.z,b.z),a,b))
for z in range(-80,66):
    height=max(-79.999,min(64.649,z))
    ring=[a.lerp(b,(height-a.z)/(b.z-a.z)) for low,high,a,b in segments if low<=height<=high]
    if not ring:ring=[min(shaft.data.vertices,key=lambda v:abs(v.co.z-z)).co]
    stations.append(Vector(((min(p.x for p in ring)+max(p.x for p in ring))*.5,(min(p.y for p in ring)+max(p.y for p in ring))*.5,0)))
for v in shaft.data.vertices:
    f=min(145,max(0,v.co.z+80));i=min(144,int(f));c=stations[i].lerp(stations[i+1],f-i)
    keep=Vector((.55*math.sin(v.co.z*.047),.3*math.sin(v.co.z*.035+.7),0))
    v.co.x+=keep.x-c.x;v.co.y+=keep.y-c.y
grip_points=[v.co for v in shaft.data.vertices if 22<=v.co.z<=42]
offset=Vector((.55*math.sin(32*.047),.3*math.sin(32*.035+.7),0))
radial_scale=2.98/statistics.median((p-offset).xy.length for p in grip_points)
for v in shaft.data.vertices:
    v.co.x=(v.co.x-offset.x)*radial_scale;v.co.y=(v.co.y-offset.y)*radial_scale

# Keep each accepted grip variant's actual exterior geometry. Only close its
# open ends and assign continuous wood UVs; the hand/rig remains unchanged.
grip_names=['SM_Staff_grip_lining_'+s for s in ('false','alloy_grip','pine_grip','sandalwood_grip')]
with bpy.data.libraries.load(str(ROOT.parent/'apprentice_staff_modular.blend'),link=False) as (src,dst):
    dst.objects=list(grip_names)
grips={obj.name:obj for obj in dst.objects}
for obj in grips.values():
    bpy.context.collection.objects.link(obj);close_mesh(obj)
    # Explicit central fans avoid UE rejecting the skinny collinear triangles
    # made by generic ngon tessellation of the irregular original cut rings.
    bm=bmesh.new();bm.from_mesh(obj.data)
    caps=[f for f in bm.faces if len(f.verts)>4 and abs(f.normal.z)>.999]
    if caps:bmesh.ops.poke(bm,faces=caps,center_mode='MEAN_WEIGHTED')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
factory=grips[grip_names[0]]

grip_tree=BVHTree.FromPolygons([v.co.copy() for v in factory.data.vertices],[list(p.vertices) for p in factory.data.polygons])
def grip_radius(angle,z):
    d=Vector((math.cos(angle),math.sin(angle),0))
    hit=grip_tree.ray_cast(d*20+Vector((0,0,min(41.999,max(22.001,z)))),-d,40)[0]
    return hit.xy.length if hit is not None else 2.98
def smooth(x):x=min(1,max(0,x));return x*x*(3-2*x)
for v in shaft.data.vertices:
    z=v.co.z;a=math.atan2(v.co.y,v.co.x);r=v.co.xy.length
    weight=smooth((z-14)/8)*(1-smooth((z-42)/8))
    target=grip_radius(a,z)
    r=r*(1-weight)+target*weight
    # A centered circular neck joins all element heads and crown options.
    neck=smooth((z-48)/6)
    r=r*(1-neck)+2.98*neck
    v.co.x=r*math.cos(a);v.co.y=r*math.sin(a)
shaft.data.update()
# Reconstruct a continuous closed radial shell from the fitted Meshy silhouette.
# Every station has the same indexed ring; source cracks cannot propagate into
# the replacement. The accepted grip is still kept as its original mesh.
tree=BVHTree.FromPolygons([v.co.copy() for v in shaft.data.vertices],[list(p.vertices) for p in shaft.data.polygons])
count=96
levels=sorted(set([-80.,64.65,14.,22.,42.,48.,54.,62.]+[-79.5+i*.75 for i in range(193) if -79.5+i*.75<64.65]))
vertices=[];faces=[]
for z in levels:
    for i in range(count):
        a=i*math.tau/count;d=Vector((math.cos(a),math.sin(a),0))
        zz=min(64.60,max(-79.85,z))
        hit=tree.ray_cast(d*25+Vector((0,0,zz)),-d,50)[0]
        radius=hit.xy.length if hit is not None else 2.98
        if 22<=z<=42:radius=grip_radius(a,z)
        if z>=54:radius=2.98
        vertices.append((radius*d.x,radius*d.y,z))
for j in range(len(levels)-1):
    for i in range(count):faces.append((j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i))
faces.extend([tuple(reversed(range(count))),tuple((len(levels)-1)*count+i for i in range(count))])
source_shaft=shaft;source_shaft.name='FittedMeshySilhouette'
data=bpy.data.meshes.new('ClosedBranchShell');data.from_pydata(vertices,[],faces);data.materials.append(wood_mat);data.update()
for polygon in data.polygons:polygon.use_smooth=len(polygon.vertices)==4
shaft=bpy.data.objects.new('AuthoredBranchShaft',data);bpy.context.collection.objects.link(shaft)
close_mesh(shaft)

lower=clip(copy(shaft,'BranchLower'),-81,22)
upper=clip(copy(shaft,'BranchUpper'),42,62)
for obj,edge_z in [(lower,22),(upper,42)]:
    for v in obj.data.vertices:
        if abs(v.co.z-edge_z)<.001:
            a=math.atan2(v.co.y,v.co.x);r=grip_radius(a,edge_z)
            v.co.x=r*math.cos(a);v.co.y=r*math.sin(a)
body=join([lower,upper],'SM_Staff_Body')
neck=clip(copy(shaft,'FactoryWoodNeck'),62,64.65)

def material(name,color,rough=.5,transmission=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Transmission Weight'].default_value=transmission
    bs.inputs['IOR'].default_value=1.544 if transmission else 1.45
    return m
rope_mat=material('M_Staff_HempV19',(.22,.14,.065),.84)
import runpy
quartz_mat=runpy.run_path(str(ROOT.parent/'QuartzMilkV20/blender_quartz_material.py'))['create_quartz_material']()

def mesh(name,verts,faces,mat,smooth=False,uvs=None):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    data.materials.append(mat)
    for p in data.polygons:p.use_smooth=smooth
    uv=data.uv_layers.new(name='UVMap')
    for loop in data.loops:
        co=data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=uvs[loop.vertex_index] if uvs else ((math.atan2(co.y,co.x)/math.tau)%1,co.z/12)
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);return obj
def tube(name,points,radius,sides=6):
    verts=[];faces=[];uv=[];length=0
    points=[Vector(p) for p in points]
    for i,p in enumerate(points):
        if i:length+=(p-points[i-1]).length
        t=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        n=t.cross(Vector((0,0,1)))
        if n.length<.001:n=t.cross(Vector((0,1,0)))
        n.normalize();b=t.cross(n).normalized()
        r=radius*(1-.55*max(0,(i/(len(points)-1)-.94)/.06))
        for j in range(sides):
            a=j*math.tau/sides;verts.append(p+r*(n*math.cos(a)+b*math.sin(a)));uv.append((j/sides,length/4))
        if i:
            for j in range(sides):faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,verts,faces,rope_mat,True,uv)
def rope(name,points,radius=.38):
    points=[Vector(p) for p in points];parts=[];dist=0
    tracks=[[] for _ in range(3)]
    for i,p in enumerate(points):
        if i:dist+=(p-points[i-1]).length
        t=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        n=t.cross(Vector((0,0,1)))
        if n.length<.001:n=t.cross(Vector((0,1,0)))
        n.normalize();b=t.cross(n).normalized()
        for s in range(3):
            a=dist*math.tau/1.55+s*math.tau/3
            tracks[s].append(p+radius*.47*(n*math.cos(a)+b*math.sin(a)))
    for s,track in enumerate(tracks):parts.append(tube(name+str(s),track,radius*.58))
    return parts

rope_parts=[]
for k in range(2):
    # Irregular doubled coils, all between z=57 and 62.3; no lower wrapping.
    points=[]
    for i in range(192):
        t=i/191;a=(t*2.6+k*.6)*math.tau
        z=57.7+t*3.6+.15*math.sin(a*1.7+k)
        r=3.18+.09*math.sin(a*2.2+k)
        points.append((r*math.cos(a),r*math.sin(a),z))
    rope_parts+=rope('HempCoil',points,.38)
# A small tied bight and two short frayed ends remain at the upper collar.
for k in range(2):
    points=[(3.3+(.72+k*.18)*math.sin(t*math.tau),-.4+(1-k*.25)*math.cos(t*math.tau),59.7+1.45*math.sin(t*math.tau+.4)) for t in [i/64 for i in range(65)]]
    rope_parts+=rope('HempKnot',points,.38)
for k in range(2):
    points=[(3.3+t*(1.45+k*.6),-.3+t*(k-.5),59.2-t*(2.3-k*.5)-.4*math.sin(t*math.pi)) for t in [i/40 for i in range(41)]]
    rope_parts+=rope('ShortTail',points,.34)
    end=Vector(points[-1])
    for s in range(7):
        a=s*math.tau/7
        rope_parts.append(tube('FrayedFiber',[end+Vector((.08*math.cos(a)*i,.065*math.sin(a)*i,-.08*i)) for i in range(9)],.026,4))
hemp=join(rope_parts,'TopHempBinding')

verts=[];rings=[]
for level,(z,r) in enumerate([(64.25,2.67),(65.1,3.35),(66.1,4.45),(75.2,4.0),(78.0,2.05)]):
    ring=[]
    for i in range(6):
        a=i*math.tau/6+math.pi/6
        rr=r*(1+.07*math.sin(i*2.4))
        ring.append(len(verts));verts.append((rr*math.cos(a)+.1*(level-1),rr*math.sin(a),z+(0 if level<2 else .55*math.sin(i*1.8))))
    rings.append(ring)
apex=len(verts);verts.append((.65,-.28,80))
faces=[tuple(reversed(rings[0]))]
for a,b in zip(rings,rings[1:]):
    faces.extend([(a[i],a[(i+1)%6],b[(i+1)%6],b[i]) for i in range(6)])
faces.extend([(rings[-1][i],rings[-1][(i+1)%6],apex) for i in range(6)])
quartz=mesh('ClearQuartzCrystal',verts,faces,quartz_mat)
head=join([neck,quartz],'SM_Staff_head_crystal_false')
body=join([body,hemp],'SM_Staff_Body')
factory.data.materials.clear();factory.data.materials.append(wood_mat)
for p in factory.data.polygons:p.material_index=0
base=join([copy(body,'b'),copy(factory,'g'),copy(head,'h')],'SM_Staff_Base')

from modular_parts import build_modifications
mods=build_modifications(base,factory,32.0,neck_master=shaft)
# Replace regenerated grip options with their unchanged original meshes.
for option in ('alloy_grip','pine_grip','sandalwood_grip'):
    prefix='SM_Staff_grip_lining_'+option
    generated=next(o for o in mods if o.name.startswith(prefix))
    mats=list(generated.data.materials)
    mods.remove(generated);bpy.data.objects.remove(generated,do_unlink=True)
    old=grips[prefix];old.name=prefix
    old.data.materials.clear()
    for m in mats:old.data.materials.append(m)
    for p in old.data.polygons:p.material_index=0
    mods.append(old)
objects=[base,body,head,factory]+mods
pine=wood_material(ROOT,'M_Staff_PineV19',(.76,.55,.29))
sandal=wood_material(ROOT,'M_Staff_SandalV19',(.39,.18,.08))
for obj in objects:
    for i,m in enumerate(obj.data.materials):
        if m and m.name.startswith('M_Staff_Pine'):obj.data.materials[i]=pine
        elif m and m.name.startswith('M_Staff_Sandal'):obj.data.materials[i]=sandal
    wood_uv(obj)
    # UE consumes UV channel 0; Blender renders the active layer. Eliminate the
    # inactive empty layer inherited when joining the previously UV-less wood.
    active_name=obj.data.uv_layers.active.name
    for layer in list(obj.data.uv_layers):
        if layer.name!=active_name:obj.data.uv_layers.remove(layer)
    obj.data.uv_layers.active_index=0
    obj.data.uv_layers[0].name='UVMap';obj.data.uv_layers[0].active_render=True
    obj["uv_repaired_faces"]=repair_degenerate_uvs(obj)
for o in objects:
    for m in o.data.materials:
        if m and m.name.startswith('M_Staff_PineV2'):m.name='M_Staff_PineV19'
        if m and m.name.startswith('M_Staff_SandalV2'):m.name='M_Staff_SandalV19'
    o['revision']=19

# Keep generated source and all editable replacement meshes in the artist file.
for obj in bpy.context.scene.objects:
    obj.hide_render=obj!=base
    obj.hide_set(obj!=base)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
for image in bpy.data.images:
    if image.packed_file is None and image.source=='FILE':
        try:image.pack()
        except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Staff_SolidCrystal_V19.blend'))
manifest=[]
for obj in objects:
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,apply_scale_options='FBX_SCALE_ALL',path_mode='AUTO',embed_textures=False)
    manifest.append({'name':obj.name,'fbx':str(path),'materials':[m.name for m in obj.data.materials if m],
                     'uv_repaired_faces':obj['uv_repaired_faces'],'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons)})
    obj.hide_set(obj!=base)
(OUT/'meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'anchors.json').write_text(json.dumps({'revision':19,'units':'cm','length':160,'grip':[0,0,32],
    'grip_limits_z':[22,42],'head_interface':[0,0,62],'tip':[0,0,80],
    'grip_source':'Original exterior vertices retained; welded seams and closed end caps; continuous cylindrical wood UV','rope':'Top collar only, no lower wraps',
    'rune_centers_z':[45.5,50,54.5],'mana_end_z':55.5,'source_reference':'User image plus user no-lower-rope correction',
    'tested':False,'rendered':False},indent=2),encoding='utf-8')
print('STAFF_SOLID_V19_EXPORTED '+str(len(manifest))+' meshes',flush=True)
