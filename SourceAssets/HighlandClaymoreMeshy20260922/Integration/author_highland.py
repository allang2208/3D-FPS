"""Fit the selected Meshy sword and author compatible modular weapon assets.

Preserves source UVs and corner normals. Produces game assets, no review renders.
"""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
OUT=P/'Export';OUT.mkdir(exist_ok=True)
UE='/Game/Weapons/HighlandClaymore20260922'
WEAPON='ue_highland_claymore'
SOURCE=P.parent/'Meshy/candidate01/downloads'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'Highland_Original_Editable.blend'))
source=next(o for o in bpy.context.scene.objects if o.type=='MESH')
source.name='Highland_Selected_Source'
source.data.transform(source.matrix_world);source.matrix_world=Matrix.Identity(4)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def smooth(x):
    x=np.clip(x,0.,1.);return x*x*(3-2*x)

def fit(points):
    x,y,z=points.T
    # Guard and leather collars, measured in the generated model's coordinates.
    # The installed Frost standard grip is -5 .. -22.7 cm in WPN_root space.
    q=points.copy()
    q[:,2]=np.interp(z,[-.951524,-.825,-.490,-.345,.950502],[-.293,-.227,-.050,0.,.880])
    blade=smooth((z+.31)/.13)
    grip=smooth((z+.84)/.025)*(1-smooth((z+.51)/.025))
    sx=.680+(0.570-.680)*grip
    sy=.520+(0.710-.520)*grip
    sy=sy*(1-blade)+.140*blade
    q[:,0]=(x-.0008)*sx;q[:,1]=(y-.0004)*sy
    return q

def deform_mesh(mesh,fn):
    points=np.array([tuple(v.co) for v in mesh.vertices],dtype=np.float64)
    normals=np.array([tuple(n.vector) for n in mesh.corner_normals],dtype=np.float64)
    eps=1e-6;jac=np.empty((len(points),3,3),dtype=np.float64)
    for k in range(3):
        delta=np.zeros(3);delta[k]=eps
        jac[:,:,k]=(fn(points+delta)-fn(points-delta))/(2*eps)
    inv=np.linalg.inv(jac).transpose(0,2,1)
    inds=np.array([l.vertex_index for l in mesh.loops])
    normals=np.einsum('nij,nj->ni',inv[inds],normals)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-10)
    mesh.vertices.foreach_set('co',fn(points).astype(np.float32).ravel())
    for f in mesh.polygons:f.use_smooth=True
    mesh.update();mesh.normals_split_custom_set(normals.tolist())

deform_mesh(source.data,fit)
material=bpy.data.materials.new('M_HighlandClaymoreSurface');material.use_nodes=True
nt=material.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
for filename,socket in [('texture_0.png','Base Color'),('texture_0_metallic.png','Metallic'),('texture_0_roughness.png','Roughness'),('texture_0_normal.png','Normal')]:
    img=bpy.data.images.load(str(SOURCE/filename),check_existing=True)
    img.colorspace_settings.name='sRGB' if socket=='Base Color' else 'Non-Color'
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=img
    if socket=='Normal':
        normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],bs.inputs[socket])
    else:nt.links.new(tex.outputs['Color'],bs.inputs[socket])
source.data.materials.clear();source.data.materials.append(material)

def export(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    loc=obj.location.copy();obj.location=Vector()
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    obj.location=loc

source.name='SM_HighlandClaymore';export(source)
PIVOT={'blade_1':Vector(),'guard':Vector(),'grip':Vector((0,0,-.05)),'pommel':Vector((0,0,-.227))}
A=lambda p:p.z-.005-.95*p.x
B=lambda p:p.z-.005+.95*p.x
TOP=lambda p:p.z+.05
BOTTOM=lambda p:p.z+.227
objects={};interfaces={};rows=[]

def clip(poly,fn,inside=True):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=fn(a[0])*(1 if inside else -1);db=fn(b[0])*(1 if inside else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out

def build_part(slot):
    mesh=source.data;mesh.calc_loop_triangles();uv=mesh.uv_layers[0].data
    normals=[n.vector.copy() for n in mesh.corner_normals]
    vertices=[];faces=[];corners=[]
    for tri in mesh.loop_triangles:
        poly=[(mesh.vertices[mesh.loops[i].vertex_index].co.copy(),uv[i].uv.copy(),normals[i].copy()) for i in tri.loops]
        if slot=='blade_1':groups=[clip(clip(poly,A),B)]
        elif slot=='guard':
            poly=clip(poly,TOP);groups=[clip(poly,A,False),clip(clip(poly,A),B,False)] if poly else []
        elif slot=='grip':groups=[clip(clip(poly,TOP,False),BOTTOM)]
        else:groups=[clip(poly,BOTTOM,False)]
        for polygon in groups:
            for k in range(1,len(polygon)-1):
                t=[polygon[0],polygon[k],polygon[k+1]]
                if (t[1][0]-t[0][0]).cross(t[2][0]-t[0][0]).length<1e-12:continue
                face=[]
                for point in t:face.append(len(vertices));vertices.append(point[0]-PIVOT[slot]);corners.append(point)
                faces.append(face)
    name='SM_Highland_'+('Blade' if slot=='blade_1' else slot.title())+'_factory'
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.materials.append(material);data.update()
    layer=data.uv_layers.new(name='UVMap');normal=data.attributes.new('SurfaceNormal',type='FLOAT_VECTOR',domain='CORNER')
    for f in data.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            point=corners[data.loops[li].vertex_index];layer.data[li].uv=point[1];normal.data[li].vector=point[2].normalized()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000003)
    cuts={'blade_1':[A,B],'guard':[A,B,TOP],'grip':[TOP,BOTTOM],'pommel':[BOTTOM]}[slot]
    edges=[e for e in bm.edges if e.is_boundary and any(all(abs(fn(v.co+PIVOT[slot]))<.000003 for v in e.verts) for fn in cuts)]
    graph={}
    for e in edges:
        for v in e.verts:graph.setdefault(v,[]).append(e.other_vert(v))
    unused=set(graph);rings=[];nl=bm.loops.layers.float_vector['SurfaceNormal'];ul=bm.loops.layers.uv[0]
    while unused:
        start=min(unused,key=lambda v:tuple(v.co));current=start;previous=None;loop=[]
        for _ in range(len(graph)+1):
            loop.append(current);unused.discard(current)
            nexts=[v for v in graph[current] if v!=previous]
            if not nexts:break
            nxt=nexts[0]
            if nxt==start or nxt in loop:break
            previous,current=current,nxt
        if len(loop)<3:continue
        rings.append([list(v.co) for v in loop]);center=bm.verts.new(sum((v.co for v in loop),Vector())/len(loop))
        for a,b in zip(loop,loop[1:]+loop[:1]):
            face=bm.faces.new((b,a,center));face.smooth=False;face.normal_update()
            for l in face.loops:l[nl]=face.normal;l[ul].uv=(.02,.02)
    bm.to_mesh(data);bm.free();data.update();data.normals_split_custom_set([tuple(v.vector) for v in data.attributes['SurfaceNormal'].data])
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=PIVOT[slot]
    objects[(slot,'factory')]=obj;interfaces[slot]={'pivot_m':list(PIVOT[slot]),'cut_boundary_loops_local_m':rings}
    return obj

for slot in PIVOT:build_part(slot)

def variant(slot,option,fn):
    base=objects[(slot,'factory')]
    obj=base.copy();obj.data=obj.data.copy();obj.name=base.name.replace('factory',option)
    scene.collection.objects.link(obj);deform_mesh(obj.data,fn);objects[(slot,option)]=obj

for option in ['extended_edge','heavy_spine','feather_edge']:
    def shape(p,option=option):
        q=p.copy();x,y,z=p.T;t=np.clip((z-.13)/(.88-.13),0,1);s=smooth(t/.20);edge=smooth((np.abs(x)-.01)/.018)
        if option=='extended_edge':q[:,2]+=.15*(.88-.025)*smooth(t);q[:,0]*=1-.035*smooth((t-.45)/.55)*edge
        elif option=='heavy_spine':
            body=s*(1-.72*smooth((t-.6)/.4));q[:,0]*=1+.14*body*edge;q[:,1]*=1+body*(.14+.26*np.exp(-(x/.024)**2))
        else:
            body=s*(1-.25*smooth((t-.82)/.18));q[:,0]*=1-.145*body*edge;q[:,1]*=1-body*(.05+.19*edge)
        return q
    variant('blade_1',option,shape)
for option in ['bastion_guard','riposte_guard','light_guard']:
    def shape(p,option=option):
        q=p.copy();w=smooth((np.abs(p[:,0])-.055)/.055)
        if option=='bastion_guard':q[:,0]*=1+.10*w;q[:,1]*=1+.22*w;q[:,2]-=.014*w
        elif option=='riposte_guard':q[:,2]+=.035*w;q[:,0]*=1-.10*w
        else:q[:,0]*=1-.20*w;q[:,1]*=1-.23*w;q[:,2]*=1-.18*w
        return q
    variant('guard',option,shape)
for option in ['shock_wrap','swift_grip','long_twohand']:
    def shape(p,option=option):
        q=p.copy();x,y,z=p.T;w=smooth((-z-.014)/.016)*smooth((z+.163)/.016)
        if option=='long_twohand':q[:,2]-=.028*smooth((-z-.020)/.137)
        else:
            a=np.arctan2(y,x);wave=.5+.5*np.cos((z/.01+a/(math.tau))*math.tau if option=='shock_wrap' else a*8)
            d=(-.00045 if option=='shock_wrap' else -.00030)*w*wave**6;r=np.maximum(np.hypot(x,y),.001)
            q[:,0]*=1+d/r;q[:,1]*=1+d/r
        return q
    variant('grip',option,shape)

# Two adapters join the generated hilt's actual cut rim to the shared pommel families.
def append(file,name):
    with bpy.data.libraries.load(str(file),link=False) as (a,b):b.objects=[name]
    obj=b.objects[0];scene.collection.objects.link(obj);obj.matrix_world=Matrix.Identity(4);obj.hide_render=True;obj.hide_set(True)
    return obj
shared=append(ROOT/'SourceAssets/RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_Meteor')
frost=append(ROOT/'SourceAssets/FrostSwordModules20260915/FrostSword_Modular_Editable.blend','SM_FrostSword_Pommel_factory')
def rim(obj):
    points=set()
    for face in obj.data.polygons:
        coords=[obj.data.vertices[i].co for i in face.vertices]
        if not any(p.z<-.000002 for p in coords):continue
        for p in coords:
            if abs(p.z)<.000003 and math.hypot(p.x,p.y)>.003:points.add((round(p.x,8),round(p.y,8)))
    return sorted([Vector(p) for p in points],key=lambda p:math.atan2(p.y,p.x))
def cross(a,b):return a.x*b.y-a.y*b.x
def radial(poly,angle):
    ray=Vector((math.cos(angle),math.sin(angle)));hits=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        edge=b-a;den=cross(ray,edge)
        if abs(den)<1e-12:continue
        dist=cross(a,edge)/den;along=cross(a,ray)/den
        if dist>0 and -1e-6<=along<=1.000001:hits.append(dist)
    if not hits:raise RuntimeError('No radial mount boundary')
    return ray*max(hits)
metal=bpy.data.materials.new('M_HighlandMountMetal');metal.use_nodes=True
mb=next(n for n in metal.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
mb.inputs['Base Color'].default_value=(.18,.13,.075,1);mb.inputs['Metallic'].default_value=.85;mb.inputs['Roughness'].default_value=.36
adapters={};top=rim(objects[('pommel','factory')])
for key,donor,scale in [('shared_sword_pommel_v1',shared,.90),('frost_hilt_v1',frost,.85)]:
    bottom=rim(donor);angles=sorted(set(round(math.atan2(p.y,p.x),9) for p in top+bottom))
    verts=[];faces=[];n=len(angles);steps=10;depth=.008
    for j in range(steps+1):
        t=j/steps;s=float(smooth(t))
        for angle in angles:
            a=radial(top,angle);b=radial(bottom,angle)*scale;v=a.lerp(b,s);verts.append((v.x,v.y,-depth*t))
    for j in range(steps):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i;faces.extend([(a,c,b),(a,d,c)])
    name='SM_HighlandMount_'+('Shared' if donor==shared else 'Frost')
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(metal);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
    for f in mesh.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            vi=mesh.loops[li].vertex_index;uv.data[li].uv=(vi%n/n,vi//n/steps)
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.location=PIVOT['pommel'];export(obj);obj.hide_render=True;obj.hide_set(True)
    adapters[key]={'mesh':name,'scale':scale,'depth_cm':depth*100}
for (slot,option),obj in objects.items():
    export(obj);obj.hide_render=option!='factory';obj.hide_set(option!='factory')
    row={'slot':slot,'id':option,'mesh':obj.name,'location_cm':[float(v*100) for v in PIVOT[slot]],'triangles':len(obj.data.polygons)}
    if slot=='blade_1':row.update(trace_base_cm=[0,0,3],trace_tip_cm=[0,0,88],rune_dimensions_cm=[6.4*(1.14 if option=='heavy_spine' else .855 if option=='feather_edge' else 1),12,69*(1.15 if option=='extended_edge' else 1)])
    if slot=='grip':
        row['pommel_offset_cm']=[0,0,-2.8 if option=='long_twohand' else 0]
        if option=='long_twohand':row['animation_folder']='/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'
    rows.append(row)
source.hide_render=True;source.hide_set(True)
for slot,pivot in PIVOT.items():
    obj=bpy.data.objects.new('Mount_'+slot,None);scene.collection.objects.link(obj);obj.location=pivot;obj.empty_display_type='ARROWS';obj.empty_display_size=.025
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'HighlandClaymore_Modular_Editable.blend'))
(P/'interfaces.json').write_text(json.dumps({'units':'metres; blade +Z, width X, thickness Y','interface':'highland_hilt_v1','blade_v':'z=.005+.95*abs(x)','parts':interfaces},indent=2),encoding='utf-8')
(P/'exports.json').write_text(json.dumps({'weapon':WEAPON,'ue_root':UE,'parts':rows,'adapters':adapters,'world_mesh':source.name,'source':str(SOURCE/'model.glb'),'arms_mesh':'/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms.SK_FrostSword_Arms','animation_folder':'/Game/Weapons/AzureRunesword20260913','fit':{'grip_top_cm':-5,'grip_bottom_cm':-22.7,'blade_tip_cm':88,'native_triangle_count':56724},'testing':'Not run; user will test.'},ensure_ascii=False,indent=2),encoding='utf-8')
print('HIGHLAND_MODULAR_EXPORT_COMPLETE '+str(P/'exports.json'),flush=True)
