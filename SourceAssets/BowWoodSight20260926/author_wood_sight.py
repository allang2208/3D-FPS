"""Carved wood sight with a saddle fitted to the retained bow, authored in cm.

Reference: BV1jGdDBkEkc, 33-48 s, small open mechanical aperture. Geometry is
original; wood texture/normal are reused from the project's retained longbow.
No rendering, editor startup or gameplay test is performed by this script.
"""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

P=Path(__file__).parent; OUT=P/'Export'; OUT.mkdir(exist_ok=True)
BASE=P.parent/'DarkBow20260925/WoodLongbow20260925'
bpy.ops.wm.open_mainfile(filepath=str(BASE/'WoodLongbow_Editable.blend'))
src=bpy.data.objects['SM_DarkBow_WoodLongbow']
scale=100 if max(src.dimensions)<5 else 1
vv=[src.matrix_world@v.co*scale for v in src.data.vertices]
vv=[Vector((v.x,-v.y,v.z)) for v in vv]
adj=[[] for _ in vv]
for e in src.data.edges:
    a,b=e.vertices;adj[a].append(b);adj[b].append(a)
unseen=set(range(len(vv)));islands=[]
while unseen:
    root=unseen.pop();stack=[root];group=[root]
    while stack:
        for i in adj[stack.pop()]:
            if i in unseen:unseen.remove(i);stack.append(i);group.append(i)
    islands.append(group)
body=set(max(islands,key=lambda g:max(vv[i].z for i in g)-min(vv[i].z for i in g)))
src.data.calc_loop_triangles()
tri=[t for t in src.data.loop_triangles if t.vertices[0] in body]
source_tree=BVHTree.FromPolygons(vv,[list(t.vertices) for t in tri],all_triangles=True)
source_uv=[[Vector((*src.data.uv_layers.active.data[l].uv,0)) for l in t.loops] for t in tri]

def source_point(x,z):
    hit,n,index,d=source_tree.ray_cast(Vector((x,-12,z)),Vector((0,1,0)),24)
    if hit is None:raise RuntimeError('Saddle outside wooden riser '+str((x,z)))
    t=tri[index]
    uv=barycentric_transform(hit,*(vv[i] for i in t.vertices),*source_uv[index])
    return hit,(uv.x,uv.y)

# Retain source measurements in Python before starting the independent asset.
samples=[]
for iz in range(65):
    t=iz/64;z=12.1+7.2*t
    half=.15+1.25*math.sin(math.pi*t)**.55
    row=[]
    for ix in range(25):
        s=ix/24;x=-.65+(s*2-1)*half
        point,uv=source_point(x,z)
        # The perimeter laps just into the original wood; the feathered edge
        # merges naturally instead of leaving a rectangular clamp silhouette.
        thick=.055+.55*math.sin(math.pi*t)**.7*math.sin(math.pi*s)**.8
        row.append((point,uv,thick))
    samples.append(row)

# Actual wooden cross-sections for the two fine retention lashings.
cord_centres=[];dowel_centres=[]
for z in (13.9,17.4):
    p,_=source_point(-.65,z);t=(z-12.1)/7.2
    p.y-=.055+.55*math.sin(math.pi*t)**.7
    dowel_centres.append(p)
for zbase in (12.95,18.15):
    points=[]
    for i in range(193):
        t=i/192;angle=t*math.tau*3
        z=zbase+(t-.5)*.60
        radial=Vector((math.cos(angle),math.sin(angle),0))
        centre=Vector((-.7,0,z))
        hit,n,index,d=source_tree.ray_cast(centre+radial*12,-radial,24)
        if hit is None:raise RuntimeError('Cannot fit lashing to riser')
        # Follow the saddle on its exposed left side, and the wood elsewhere.
        if hit.y<0 and 12.1<hit.z<19.3:
            tz=(hit.z-12.1)/7.2;half=.15+1.25*math.sin(math.pi*tz)**.55
            sx=(hit.x+.65)/half
            if abs(sx)<1:
                thick=.055+.55*math.sin(math.pi*tz)**.7*math.cos(sx*math.pi/2)**.8
                hit.y-=thick*min(1.,-radial.y*1.5)
        points.append(hit+radial*.075)
    cord_centres.append(points)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
materials=[]
for name,color,rough in [('CarvedBowWood',(.19,.058,.023,1),.48),
                         ('WaxedLinen',(.105,.068,.038,1),.83),
                         ('PaleWoodInlay',(.48,.31,.145,1),.60)]:
    mat=bpy.data.materials.new(name);mat.diffuse_color=color;mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=color;bsdf.inputs['Roughness'].default_value=rough
    materials.append(mat)
wood=materials[0];nodes=wood.node_tree.nodes;links=wood.node_tree.links
bsdf=nodes.get('Principled BSDF')
for filename,target in [('Image_0.png','Base Color'),('Image_1.png','Roughness'),('Image_2.png','Normal')]:
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(BASE/'Textures'/filename))
    if target=='Base Color':links.new(tex.outputs['Color'],bsdf.inputs[target])
    else:
        tex.image.colorspace_settings.name='Non-Color'
        if target=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.55
            links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
        else:
            sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs['Color'])
            mx=nodes.new('ShaderNodeMath');mx.operation='MAXIMUM';mx.inputs[1].default_value=.42
            links.new(sep.outputs['Green'],mx.inputs[0]);links.new(mx.outputs[0],bsdf.inputs['Roughness'])

parts=[]
def mesh(name,vertices,faces,uvs,mat=0):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    data.materials.append(materials[mat]);uv=data.uv_layers.new(name='UVMap')
    for p in data.polygons:
        p.use_smooth=True
        for l in p.loop_indices:uv.data[l].uv=uvs[data.loops[l].vertex_index]
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    parts.append(obj);return obj

def catmull(points,steps=12):
    q=[Vector(p) for p in points];out=[]
    for i in range(len(q)-1):
        a=q[max(0,i-1)];b=q[i];c=q[i+1];d=q[min(len(q)-1,i+2)]
        for j in range(steps):
            t=j/steps
            out.append((2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5)
    return out+[q[-1]]

def sweep(name,points,radii,mat=0,sides=16,vstart=.40,vspan=.20):
    points=[Vector(p) for p in points];vertices=[];uv=[];faces=[]
    for i,p in enumerate(points):
        t=i/(len(points)-1)
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        across=Vector((1,0,0));across=(across-tangent*across.dot(tangent)).normalized()
        if across.length<.5:across=tangent.cross(Vector((0,1,0))).normalized()
        side=tangent.cross(across).normalized();rx,ry=radii(t)
        for j in range(sides+1):
            a=j/sides*math.tau
            vertices.append(p+across*(rx*math.cos(a))+side*(ry*math.sin(a)))
            uv.append((.15+.052*j/sides,vstart+vspan*t))
    w=sides+1
    for i in range(len(points)-1):
        for j in range(sides):a=i*w+j;faces.append((a,a+1,a+w+1,a+w))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*w+j for j in range(sides))])
    return mesh(name,vertices,faces,uv,mat)

# Closed conformal saddle; the hidden underside sinks 0.08 cm into the riser.
vertices=[];uv=[];faces=[];nz=len(samples);nx=len(samples[0]);layer=nz*nx
for top in (False,True):
    for row in samples:
        for p,tuv,thick in row:
            vertices.append((p.x,p.y-thick if top else p.y+.08,p.z));uv.append(tuv)
for k in (0,layer):
    for i in range(nz-1):
        for j in range(nx-1):a=k+i*nx+j;faces.append((a,a+1,a+nx+1,a+nx))
border=list(range(nx))+[i*nx+nx-1 for i in range(1,nz)]+list(range(layer-2,layer-nx-1,-1))+[i*nx for i in range(nz-2,0,-1)]
for a,b in zip(border,border[1:]+border[:1]):faces.append((a,b,b+layer,a+layer))
saddle=mesh('Feathered_conformal_saddle',vertices,faces,uv)

branch=catmull([(-.65,-2.85,16.2),(-1.25,-3.5,15.1),(-2.3,-4.7,13.55),
               (-3.2,-6.5,13.2),(-3.5,-8.65,13.65),(-3.5,-10.1,14.85)],16)
sweep('Carved_swept_arm',branch,lambda t:(.70*(1-t)+.25*t,.72*(1-t)+.28*t),vstart=.43,vspan=.20)
cx,cy,cz=-3.5,-10.1,16.5
guard=[]
for i in range(113):
    angle=math.radians(46+268*i/112)
    guard.append((cx,cy+1.65*math.sin(angle),cz+1.65*math.cos(angle)))
sweep('Continuous_open_aperture',guard,lambda t:(.20*(.65+.35*math.sin(math.pi*t)**.35),.175*(.65+.35*math.sin(math.pi*t)**.35)),vstart=.40,vspan=.24)
# Tapered wooden front post grows directly out of the lower aperture.
sweep('Tapered_wood_post',[(cx,cy,14.78+i*1.69/24) for i in range(25)],lambda t:(.14-.077*t,.14-.077*t),sides=16,vspan=.05)

# Fuse the four wooden pieces, so their junctions are carved fillets instead
# of intersections of separately shaded rods. Transfer wood UVs from the
# authored precursor surfaces after remeshing.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=saddle;bpy.ops.object.join();wood_obj=bpy.context.object
wood_obj.data.calc_loop_triangles()
uvlayer=wood_obj.data.uv_layers.active
raw_vertices=[v.co.copy() for v in wood_obj.data.vertices]
raw_triangles=[list(t.vertices) for t in wood_obj.data.loop_triangles]
raw_uv=[[Vector((*uvlayer.data[l].uv,0)) for l in t.loops] for t in wood_obj.data.loop_triangles]
uv_tree=BVHTree.FromPolygons(raw_vertices,raw_triangles,all_triangles=True)
wood_obj.data.remesh_voxel_size=.045;bpy.ops.object.voxel_remesh()
smooth=wood_obj.modifiers.new('Carved fillets','SMOOTH');smooth.factor=.65;smooth.iterations=5
bpy.ops.object.modifier_apply(modifier=smooth.name)
dec=wood_obj.modifiers.new('Preserve curved silhouette','DECIMATE');dec.ratio=.40
bpy.ops.object.modifier_apply(modifier=dec.name)
data=wood_obj.data;uvlayer=data.uv_layers.active or data.uv_layers.new(name='UVMap')
for poly in data.polygons:
    poly.use_smooth=True
    # One precursor triangle per destination face avoids mixing opposite
    # sides of the UV seam inside a single rasterised face.
    center=sum((data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices)
    _,_,idx,_=uv_tree.find_nearest(center);abc=raw_triangles[idx]
    for l in poly.loop_indices:
        point=data.vertices[data.loops[l].vertex_index].co
        tuv=barycentric_transform(point,*(raw_vertices[i] for i in abc),*raw_uv[idx])
        uvlayer.data[l].uv=(max(.135,min(.217,tuv.x)),max(.09,min(.92,tuv.y)))
wood_obj.name='Carved_wood_continuous_body';parts=[wood_obj]

# Fine, warm waxed cord follows the measured riser/saddle cross-sections.
# Three twisted strands remain actual geometry, not a faceted thick band.
for k,path in enumerate(cord_centres):
    for strand in range(3):
        twisted=[]
        for i,p in enumerate(path):
            tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
            across=tangent.cross(Vector((0,0,1))).normalized();side=tangent.cross(across).normalized()
            a=i/192*math.tau*36+strand*math.tau/3
            twisted.append(p+.022*(math.cos(a)*across+math.sin(a)*side))
        sweep('Twisted_linen_%d_%d'%(k,strand),twisted,lambda t:(.023,.023),1,6)

# A tiny pale wood end-grain insert is the non-emissive aiming point.
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.075,location=(cx,cy,cz))
tip=bpy.context.object;tip.name='Pale_wood_pin';tip.scale=(.70,1,1)
tip.data.materials.append(materials[2]);parts.append(tip)
for p in tip.data.polygons:p.use_smooth=True
# Two small dowel end-grains at the saddle's exposed ends give a credible
# handmade construction detail without bulky fasteners.
for p in dowel_centres:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.105,location=p)
    o=bpy.context.object;o.name='Wood_dowel_end';o.scale=(1,.27,1);o.data.materials.append(materials[2]);parts.append(o)
    for f in o.data.polygons:f.use_smooth=True

bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=wood_obj;bpy.ops.object.join();obj=bpy.context.object
obj.name='SM_Bow_CarvedWoodSight';bpy.context.scene.cursor.location=(0,0,0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# Export uses the same proven cm / handedness route as the retained bow.
for v in obj.data.vertices:v.co.y=-v.co.y
bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_CarvedWoodSight.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
(P/'authoring.json').write_text(json.dumps({'sight_pin_cm':[cx,cy,cz],'triangles':len(obj.data.polygons),
    'material_slots':[m.name for m in obj.data.materials],'saddle_z_cm':[12.1,19.3],
    'saddle_source':'retained WoodLongbow_Editable.blend, connected wooden shell, ray-fitted surface',
    'wood_texture_source':'retained WoodLongbow20260925/Textures/Image_0,1,2.png',
    'reference':'BV1jGdDBkEkc 33-48 s; open mechanical sight and continuous ADS adaptation',
    'runtime_tested':False,'rendered':False},indent=2),encoding='utf8')
print('BOW_WOOD_SIGHT_AUTHORED',len(obj.data.polygons))
