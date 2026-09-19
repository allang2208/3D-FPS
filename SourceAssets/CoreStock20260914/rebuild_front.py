"""Replace the uneven front of the selected stock with a local hard-surface shell."""
import bpy,bmesh,json,math,shutil
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
OLD=P.parent/'ReferenceSkeletonStock5080_20260913/Refined'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(OLD/'SkeletonStock_Game_Low_Editable.blend'))
body=bpy.data.objects['SkeletonStock_Game_Low'];body.hide_set(False);body.hide_render=False
body.data.validate(clean_customdata=False);body.data.update()
frozen=body.copy();frozen.data=body.data.copy();bpy.context.collection.objects.link(frozen);frozen.name='Prior_Front_Source';frozen.hide_set(True);frozen.hide_render=True
body.name='CoreStock_Retained_Body'

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def flat_material(name,color,rough,metal):
    m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    return m
poly=flat_material('StockFrontPolymer',(.025,.026,.028),.56,0)
metal=flat_material('StockFrontMetal',(.026,.030,.035),.52,.8)
body.data.materials.append(poly);body.data.materials.append(metal)

# Remove the actual irregular front geometry, including fused protrusions.
# A narrow overlapped collar marks the interface with the retained housing.
cut=-.300
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(cut,0,0),plane_no=(1,0,0),clear_inner=True)
boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.x-cut)<1e-5 for v in e.verts)]
if boundary:
    caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    for f in caps['faces']:f.material_index=1;f.smooth=False
bm.to_mesh(body.data);bm.free();body.data.update()
parts=[]

def make(name,verts,faces,material,smooth_sides=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.data.materials.append(material)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    for i,f in enumerate(me.polygons):f.use_smooth=i<smooth_sides
    for uvname in ['SourceProjectionUV','GameBakeUV1']:
        layer=me.uv_layers.new(name=uvname)
        for f in me.polygons:
            axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(f.normal[a]))]
            for li in f.loop_indices:
                co=me.vertices[me.loops[li].vertex_index].co;layer.data[li].uv=(co[axes[0]]*2,co[axes[1]]*2)
    parts.append(ob);return ob

# Smooth closed cross-section from the reference: rounded crown, broad lower
# shoulder and a flat underside. The inner socket remains a real cylindrical void.
anchors=[(0,.335),(.045,.325),(.080,.298),(.100,.263),(.107,.215),(.108,.157),(.094,.115),(.060,.096),(0,.096),(-.060,.096),(-.094,.115),(-.108,.157),(-.107,.215),(-.100,.263),(-.080,.298),(-.045,.325)]
profile=[]
for i in range(len(anchors)):
    p0,p1,p2,p3=[Vector(anchors[j%len(anchors)]) for j in [i-1,i,i+1,i+2]]
    for k in range(6):
        t=k/6.;v=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
        profile.append((v.x,v.y))
n=len(profile)
stations=[(-.50099456,.966),(-.4995,.984),(-.497,1.0),(-.486,1.0),(-.462,1.018),(-.438,1.036),(-.415,1.036),(-.386,1.025),(-.345,1.006),(-.306,1.0),(-.300,1.003),(-.294,1.003)]
vertices=[]
for x,s in stations:vertices.extend([(x,y*s,z) for y,z in profile])
outer_count=len(vertices)
for x,_ in stations:
    r=.080 if x==stations[0][0] else .078 if x==stations[1][0] else .077
    vertices.extend([(x,r*math.sin(i*2*math.pi/n),.239+r*math.cos(i*2*math.pi/n)) for i in range(n)])
faces=[]
for shell in [0,1]:
    off=shell*outer_count
    for row in range(len(stations)-1):
        for i in range(n):
            j=(i+1)%n;f=(off+row*n+i,off+row*n+j,off+(row+1)*n+j,off+(row+1)*n+i)
            faces.append(f if shell==0 else tuple(reversed(f)))
smooth=len(faces)
for row in [0,len(stations)-1]:
    for i in range(n):
        j=(i+1)%n;f=(row*n+i,outer_count+row*n+i,outer_count+row*n+j,row*n+j)
        faces.append(f if row==0 else tuple(reversed(f)))
make('CoreFront_Regular_Sleeve',vertices,faces,poly,smooth)

# A clean clevis replaces the lumpy hanging front details and meets the retained
# diagonal brace. New surfaces use their own geometric normals and material.
outline=[(-.465,.097),(-.435,.065),(-.345,.024),(-.292,.012),(-.292,.099)]
verts=[(x,y,z) for y in [-.035,.035] for x,z in outline];count=len(outline)
faces=[tuple(range(count-1,-1,-1)),tuple(range(count,count*2))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
clevis=make('CoreFront_Clean_Clevis',verts,faces,metal)
active(clevis);mod=clevis.modifiers.new('Clevis edge radius','BEVEL');mod.width=.004;mod.segments=4;bpy.ops.object.modifier_apply(modifier=mod.name)
mod=clevis.modifiers.new('Clevis weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
for side in [-1,1]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.013,depth=.004,location=(-.358,side*.037,.068),rotation=(math.pi/2,0,0))
    pin=bpy.context.object;pin.name='CoreFront_Pin';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);pin.data.materials.append(metal)
    for f in pin.data.polygons:f.use_smooth=len(f.vertices)==4
    pin.data.uv_layers[0].name='SourceProjectionUV'
    baked_uv=pin.data.uv_layers.new(name='GameBakeUV1')
    for dst,original in zip(baked_uv.data,pin.data.uv_layers[0].data):dst.uv=original.uv
    active(pin);mod=pin.modifiers.new('Pin rim','BEVEL');mod.width=.001;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name);parts.append(pin)

# Keep a parts-level editable source before joining the engine low mesh.
for o in list(bpy.context.scene.objects):
    if o not in [body,*parts]:o.hide_set(True);o.hide_render=True
active(body)
for o in parts:o.select_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CoreStock_FrontParts_Editable.blend'))
bpy.ops.object.join();body.name='SkeletonStock_Game_Low'

# Exact retained triangles recover their previous corner normals and both UVs.
def key(v):return tuple(round(a,7) for a in v.co)
src=frozen.data;src.calc_loop_triangles();old={};old_norm=[n.vector.copy() for n in src.corner_normals]
for tri in src.loop_triangles:
    corners={key(src.vertices[src.loops[i].vertex_index]):(old_norm[i],*[layer.data[i].uv.copy() for layer in src.uv_layers]) for i in tri.loops}
    old[tuple(sorted(corners))]=corners
newnorm=[n.vector.copy() for n in body.data.corner_normals];kept=0
for f in body.data.polygons:
    keys=[key(body.data.vertices[body.data.loops[i].vertex_index]) for i in f.loop_indices];ref=old.get(tuple(sorted(keys)))
    if ref:
        for li,k in zip(f.loop_indices,keys):
            newnorm[li]=ref[k][0]
            for layer,data in zip(body.data.uv_layers,ref[k][1:]):layer.data[li].uv=data
        kept+=1
body.data.normals_split_custom_set(newnorm)
body.data.uv_layers.active_index=1;body.data.uv_layers[1].active_render=True
active(body);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CoreStock_Canonical_Editable.blend'))
tex=P/'Textures';tex.mkdir(exist_ok=True)
for name in ['BaseColor','MetalRough','Normal']:shutil.copy2(OLD/'Textures'/(name+'.png'),tex/(name+'.png'))
(P/'front_authoring.json').write_text(json.dumps({'source':str(OLD/'SkeletonStock_Game_Low_Editable.blend'),'cut_x_generator':cut,'front_rebuilt_length_generator':.20099456,'retained_original_triangles':kept,'front_old_texture_normal_reused':False,'front_surface':'regular smooth loft, beveled clevis and pins','retained_body_bakes_reused':True,'rendered':False,'tested':False},indent=2))
print('CORE_FRONT_REBUILT',flush=True)
