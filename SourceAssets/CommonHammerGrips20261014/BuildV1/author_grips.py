"""Replace only the wrapping surface; preserve the factory end geometry and UVs."""
import bpy,bmesh,math,json,runpy
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
OPTIONS=runpy.run_path(str(P/'catalog.py'))['OPTIONS']
for folder in ('Export','Textures','Icons'):(P/folder).mkdir(exist_ok=True)
runpy.run_path(str(P/'author_textures.py'),run_name='__main__')
source=ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'
with bpy.data.libraries.load(str(source),link=False) as (a,b):b.objects=['SM_Warhammer_grip_factory']
factory=b.objects[0];original=factory.data;original.calc_loop_triangles()
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.context.preferences.filepaths.save_version=0
old=original.materials[0]
def material(name,kind,tint=(1,1,1)):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links
    bs=next(v for v in n if v.type=='BSDF_PRINCIPLED');uv=n.new('ShaderNodeUVMap');uv.uv_map='UVMap'
    samples={}
    for channel in ('BaseColor','Normal','ORM'):
        image=bpy.data.images.load(str(P/'Textures'/('T_HammerGrip_'+kind+'_'+channel+'.png')),check_existing=True)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';image.reload()
        node=n.new('ShaderNodeTexImage');node.image=image;l.new(uv.outputs[0],node.inputs['Vector']);samples[channel]=node
    mult=n.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;mult.inputs[2].default_value=(*tint,1)
    l.new(samples['BaseColor'].outputs['Color'],mult.inputs[1]);l.new(mult.outputs[0],bs.inputs['Base Color'])
    sep=n.new('ShaderNodeSeparateColor');l.new(samples['ORM'].outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness'])
    normal=n.new('ShaderNodeNormalMap');normal.uv_map='UVMap';l.new(samples['Normal'].outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
    bs.inputs['Metallic'].default_value=0
    return mat
fabric=material('M_HammerGripWoven','Woven')
leather=material('M_HammerGripLeather','Leather')
dark=material('M_HammerGripDarkLeather','Leather',(.29,.38,.48))
MATS=[old,fabric,leather,dark]
ZB=-.465;ZT=-.025;CX=-.00085;CY=-.00090;TILE=.12
sections=json.loads((P/'factory_geometry.json').read_text(encoding='utf-8'))['sections']
z_axis=np.array([s['z'] for s in sections]);radii=np.array([[(s['max'][j]-s['min'][j])*.5 for j in range(2)] for s in sections])
for j in range(2):radii[:,j]=np.array([np.median(radii[max(0,i-2):i+3,j]) for i in range(len(radii))])
def shape(z,theta,offset=0):
    rx=float(np.interp(z,z_axis,radii[:,0]))+offset;ry=float(np.interp(z,z_axis,radii[:,1]))+offset
    return Vector((CX+rx*math.cos(theta),CY+ry*math.sin(theta),z))
def uv_of(p):return Vector(((math.atan2(p.y-CY,p.x-CX)%(2*math.pi))*.015/TILE,(p.z-ZB)/TILE))
def clip(poly,limit,positive):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0].z-limit)*(1 if positive else -1);db=(b[0].z-limit)*(1 if positive else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):out.append(tuple(x.lerp(y,da/(da-db)) for x,y in zip(a,b)))
    return out
class Builder:
    def __init__(self):self.vertices=[];self.faces=[];self.uvs=[];self.normals=[];self.materials=[]
    def face(self,points,uvs,mat,normals=None):
        start=len(self.vertices);self.vertices.extend(points);self.faces.append(tuple(range(start,start+len(points))))
        self.uvs.extend(uvs);self.normals.extend(normals or [Vector((0,0,0))]*len(points));self.materials.append(mat)
    def object(self,name):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.vertices,[],self.faces);mesh.update()
        for mat in MATS:mesh.materials.append(mat)
        uv=mesh.uv_layers.new(name='UVMap');stored=mesh.attributes.new('FactoryNormals',type='FLOAT_VECTOR',domain='CORNER')
        for face,mat in zip(mesh.polygons,self.materials):
            face.use_smooth=True;face.material_index=mat
            for k in face.loop_indices:
                i=mesh.loops[k].vertex_index;uv.data[k].uv=self.uvs[i];stored.data[k].vector=self.normals[i]
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
        uv_layer=bm.loops.layers.uv['UVMap']
        # Solid ribbon thickness and stitch caps need their own two-dimensional UV area.
        # Keep every valid factory/tape UV and repair only collapsed face mappings.
        for face in bm.faces:
            tex=[loop[uv_layer].uv for loop in face.loops]
            area=abs((tex[1]-tex[0]).cross(tex[2]-tex[0]))
            if area<1e-10:
                drop=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=drop]
                for loop in face.loops:loop[uv_layer].uv=(loop.vert.co[axes[0]]/TILE,loop.vert.co[axes[1]]/TILE)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
        geometric=[n.vector.copy() for n in mesh.corner_normals]
        mesh.normals_split_custom_set([tuple(n.vector.normalized() if n.vector.length>.5 else geometric[i]) for i,n in enumerate(mesh.attributes['FactoryNormals'].data)])
        obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);return obj

normals=[n.vector.copy() for n in original.corner_normals]
ends=[];segments={ZB:[],ZT:[]}
for tri in original.loop_triangles:
    poly=[(original.vertices[original.loops[i].vertex_index].co.copy(),original.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops]
    for z,positive in ((ZB,False),(ZT,True)):
        clipped=clip(poly,z,positive)
        if len(clipped)>=3:
            for i in range(1,len(clipped)-1):
                t=[clipped[0],clipped[i],clipped[i+1]]
                if (t[1][0]-t[0][0]).cross(t[2][0]-t[0][0]).length>1e-12:ends.append(t)
        cross=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if (a[0].z<=z<b[0].z) or (b[0].z<=z<a[0].z):cross.append(a[0].lerp(b[0],(z-a[0].z)/(b[0].z-a[0].z)))
        if len(cross)==2 and (cross[0]-cross[1]).length>1e-7:segments[z].append(cross)
def boundary(z):
    unique={}
    for seg in segments[z]:
        for p in seg:unique[tuple(round(c,7) for c in p)]=p
    result=sorted(unique.values(),key=lambda p:math.atan2(p.y-CY,p.x-CX)%(2*math.pi))
    return result
rings={z:boundary(z) for z in (ZB,ZT)}
def quad(builder,a,b,c,d,mat,uvs=None):
    tex=uvs or [uv_of(p) for p in (a,b,c,d)]
    if not uvs and max(t.x for t in tex)-min(t.x for t in tex)>.4:
        for t in tex:
            if t.x<.15:t.x+=2*math.pi*.015/TILE
    builder.face([a,b,c,d],tex,mat)
def bridge(builder,source_ring,z_target,offset,mat):
    # One-to-one ring loft from the untouched factory cut to the new surface.
    target=[shape(z_target,math.atan2(p.y-CY,p.x-CX),offset) for p in source_ring]
    for i in range(len(target)):
        j=(i+1)%len(target);quad(builder,source_ring[i],source_ring[j],target[j],target[i],mat)
    return target
def connect(builder,a,b,mat):
    # Zipper unequal vertex rings by angular parameter; no resampling of factory cuts.
    angle=lambda p:math.atan2(p.y-CY,p.x-CX)%(2*math.pi)
    aa=sorted(a,key=angle);bb=sorted(b,key=angle);i=j=0
    while i<len(aa) or j<len(bb):
        ai=aa[i%len(aa)];bj=bb[j%len(bb)]
        an=angle(aa[(i+1)%len(aa)])+(2*math.pi if i+1>=len(aa) else 0)
        bn=angle(bb[(j+1)%len(bb)])+(2*math.pi if j+1>=len(bb) else 0)
        if i<len(aa) and (j>=len(bb) or an<=bn):points=[ai,aa[(i+1)%len(aa)],bj];i+=1
        else:points=[ai,bb[(j+1)%len(bb)],bj];j+=1
        uv=[uv_of(p) for p in points]
        if max(p.x for p in uv)-min(p.x for p in uv)>.4:
            for t in uv:
                if t.x<.15:t.x+=2*math.pi*.015/TILE
        builder.face(points,uv,mat)
def shell(builder,kind):
    base=-.00075 if kind==0 else -.00125 if kind==2 else 0
    mat=1 if kind==0 else 3 if kind==2 else 2
    count=144 if kind==1 else 32
    inner_z=[ZB+.008+(ZT-ZB-.016)*j/count for j in range(count+1)]
    previous=bridge(builder,rings[ZB],inner_z[0]-.002,base,mat)
    for z in inner_z:
        phase=(z-(ZB+.008))/(ZT-ZB-.016)*9
        offset=base if kind!=1 else -.00115+.00105*(max(0,math.sin(math.pi*(phase%1)))**.30)
        current=[shape(z,2*math.pi*i/64,offset) for i in range(64)]
        connect(builder,previous,current,mat);previous=current
    last=bridge(builder,rings[ZT],inner_z[-1]+.002,base,mat);connect(builder,previous,last,mat)
    return inner_z[0],inner_z[-1]
def ribbon(builder,kind,z0,z1,direction=1,index=0):
    # Fully solid ribbons with modeled thickness, beveled edges and closed ends.
    steps=1300 if kind==0 else 360;wide=6;mat=1 if kind==0 else 3
    pitch=.0205 if kind==0 else .155
    def point(t,w,back=False):
        z=z0+(z1-z0)*t
        if kind==0:
            theta=2*math.pi*(z-z0)/pitch;zz=z+w*.022
            theta+=0;zz=max(z0,min(z1,zz))
            offset=-.00032-.00012*(abs(w)*2)**6-(.00040 if back else 0)
        else:
            theta=direction*2*math.pi*(z-z0)/pitch+index*math.pi+w*2.12;zz=z
            envelope=min(1,(z-z0)/.008,(z1-z)/.008);envelope=max(0,envelope)
            offset=-.00063+direction*.00048*math.cos(4*math.pi*(z-z0)/pitch)*envelope
            offset-=.00010*(abs(w)*2)**6+(.00048 if back else 0)
        return shape(zz,theta,offset)
    def uv(t,w):return Vector(((w+.5)*(.022 if kind==0 else .030)/TILE,t*(z1-z0)*math.sqrt(1+(2*math.pi*.015/pitch)**2)/TILE))
    for step in range(steps):
        t0=step/steps;t1=(step+1)/steps
        for j in range(wide):
            w0=j/wide-.5;w1=(j+1)/wide-.5
            for back in (False,True):
                pts=[point(t0,w0,back),point(t0,w1,back),point(t1,w1,back),point(t1,w0,back)]
                tex=[uv(t0,w0),uv(t0,w1),uv(t1,w1),uv(t1,w0)]
                if back:pts.reverse();tex.reverse()
                # Clamped tape ends can collapse to a line; they are under the retained collar.
                if sum((pts[i]-pts[0]).cross(pts[i+1]-pts[0]).length for i in range(1,3))>1e-12:builder.face(pts,tex,mat)
        for w in (-.5,.5):quad(builder,point(t0,w),point(t1,w),point(t1,w,True),point(t0,w,True),mat,[uv(t0,w),uv(t1,w),uv(t1,w),uv(t0,w)])
    for t in (0,1):
        for j in range(wide):
            w0=j/wide-.5;w1=(j+1)/wide-.5
            quad(builder,point(t,w0),point(t,w1),point(t,w1,True),point(t,w0,True),mat,[uv(t,w0),uv(t,w1),uv(t,w1),uv(t,w0)])
def stitches(builder,z0,z1):
    # Two recessed side seams, with short arched thread segments.
    for angle in (0,math.pi):
        for z in np.arange(z0+.004,z1-.004,.0048):
            center=shape(float(z),angle,-.0009)
            normal=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-math.sin(angle),math.cos(angle),0))
            samples=[]
            for k in range(7):
                t=k/6;p=center+side*((t-.5)*.00165)+Vector((0,0,(t-.5)*.0017))+normal*(math.sin(math.pi*t)*.00035)
                samples.append([p+normal*(math.cos(a*math.pi/3)*.00012)+Vector((0,0,math.sin(a*math.pi/3)*.00012)) for a in range(6)])
            for a,b in zip(samples,samples[1:]):
                for j in range(6):quad(builder,a[j],a[(j+1)%6],b[(j+1)%6],b[j],1)
            builder.face(samples[0],[uv_of(v) for v in samples[0]],1);builder.face(samples[-1],[uv_of(v) for v in samples[-1]],1)
rows=[]
for kind,option in enumerate(OPTIONS):
    builder=Builder()
    for triangle in ends:builder.face([p[0] for p in triangle],[p[1] for p in triangle],0,[p[2] for p in triangle])
    z0,z1=shell(builder,kind)
    if kind==0:ribbon(builder,kind,z0-.005,z1+.005)
    if kind==1:stitches(builder,z0,z1)
    if kind==2:
        for direction in (-1,1):
            for index in (0,1):ribbon(builder,kind,z0-.004,z1+.004,direction,index)
    name='SM_CommonHammerGrip_'+option['id']+'_V1';obj=builder.object(name)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
    obj.data.calc_loop_triangles();rows.append({'id':option['id'],'name':option['name'],'mesh':name,'triangles':len(obj.data.loop_triangles),'location_cm':[0,0,40.50000011920929],
        'materials':[m.name for m in obj.data.materials]})
    obj.location=(kind*.065,0,.405)
    print('GRIP_EXPORTED '+json.dumps(rows[-1],ensure_ascii=False),flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CommonHammerGrips_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'parts':rows,'source':str(source),'interface':'warhammer_factory_v1','factory_end_band_cm':2.5,
    'cut_planes_local_m':[ZB,ZT],'original_end_geometry_preserved':True,'stats_assigned':False,'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('COMMON_HAMMER_GRIPS_AUTHORED',flush=True)
