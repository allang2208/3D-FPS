"""Author Chixiao's seated loft, recessed inlay, fuller, relief and game LODs."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P/'Export';TEX=P/'Textures'
OUT.mkdir(parents=True,exist_ok=True);TEX.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;S.unit_settings.system='METRIC'
reference=json.loads((P.parent/'exports.json').read_text(encoding='utf-8'))
seat=json.loads((P.parent/'TangDaoBladesV1/blade_exports.json').read_text(encoding='utf-8'))['options'][0]
ROOT=reference['cuts_z_cm']['blade_guard']/100-.0006;TIP=reference['blade_tip_cm']/100
CX,CY=np.array(seat['trace_base_cm'][:2])/100
RW,RT=np.array(seat['seat_size_cm'])/100
# Local +Z is the weapon's longitudinal axis; -X is its curved spine.
KEY=np.array([0,.025,.06,.15,.28,.45,.62,.77,.88,.95,.985,1.])
C=np.array([CX,CX,.0005,.004,.004,.000,-.010,-.030,-.060,-.090,-.119,-.139])
W=np.array([RW,RW,.073,.084,.092,.094,.091,.078,.059,.037,.014,.00016])
H=np.array([RT/2,RT/2,.0062,.0055,.0050,.0046,.0041,.0036,.0029,.0020,.0011,.00008])
def hermite(xs,ys,q):
    d=np.diff(ys)/np.diff(xs);m=np.zeros_like(ys);m[0]=d[0];m[-1]=d[-1]
    for i in range(1,len(ys)-1):
        if d[i-1]*d[i]>0:m[i]=2/(1/d[i-1]+1/d[i])
    k=np.minimum(np.maximum(np.searchsorted(xs,q)-1,0),len(xs)-2)
    h=xs[k+1]-xs[k];s=np.clip((q-xs[k])/h,0,1)
    return (2*s**3-3*s**2+1)*ys[k]+(s**3-2*s**2+s)*h*m[k]+(-2*s**3+3*s**2)*ys[k+1]+(s**3-s**2)*h*m[k+1]
def shape(t):return float(hermite(KEY,C,t)),float(hermite(KEY,W,t)),float(hermite(KEY,H,t))
def smooth(a,b,x):
    s=np.clip((x-a)/(b-a),0,1);return s*s*(3-2*s)
def surface(t,u):
    c,w,h=shape(t);base=float(np.interp(u,[0,.025,.05,.13,.15,.17,.19,.215,.24,.72,.77,1],[.52,.90,1,1,1,.88,.80,.88,1,.92,.82,.018]))
    fuller=float(smooth(.28,.38,t)*(1-smooth(.86,.92,t)))
    if .15<u<.24:base=1-(1-base)*fuller
    base-=.05*float(smooth(.05,.058,u)*(1-smooth(.122,.13,u)))*float(smooth(.065,.10,t)*(1-smooth(.92,.96,t)))
    return c+(u-.5)*w,h*base
def image(name,array,colorspace):
    a=np.asarray(array,dtype=np.float32)
    im=bpy.data.images.new(name,width=a.shape[1],height=a.shape[0],alpha=True)
    im.colorspace_settings.name=colorspace;im.pixels.foreach_set(a.ravel())
    im.filepath_raw=str(TEX/(name+'.png'));im.file_format='PNG';im.save();return im
# One longitudinal PBR atlas for both broad faces; geometry owns the large bevels.
NX,NY=1024,4096
u=np.linspace(0,1,NX,dtype=np.float32)[None,:];t=np.linspace(0,1,NY,dtype=np.float32)[:,None]
rng=np.random.default_rng(181018)
grain=(np.sin(u*2950+np.sin(t*13)*1.1)+.45*np.sin(u*7411+t*9))*.007
noise=rng.normal(0,.004,(NY,NX)).astype(np.float32)
cloud=(np.sin(u*51+t*37)+np.sin(u*17-t*58))*.008
variation=grain+noise+cloud
col=np.empty((NY,NX,3),dtype=np.float32);col[:]=[.20,.22,.235];col+=variation[:,:,None]
silver=smooth(.755,.773,u)+(1-smooth(.025,.045,u))
col=col*(1-silver[:,:,None])+np.clip(np.array([.59,.61,.63])+variation[:,:,None]*1.5,0,1)*silver[:,:,None]
band=smooth(.052,.056,u)*(1-smooth(.122,.128,u))*smooth(.065,.10,t)*(1-smooth(.92,.96,t))
red=np.clip(np.array([.25,.038,.033])+variation[:,:,None]*np.array([2,.4,.4]),.006,1)
col=col*(1-band[:,:,None])+red*band[:,:,None]
rail=(np.exp(-((u-.048)/.0016)**2)+np.exp(-((u-.132)/.0016)**2))*smooth(.065,.10,t)*(1-smooth(.92,.96,t))
col=col*(1-rail[:,:,None])+np.array([.51,.34,.135])*rail[:,:,None]
alpha=np.ones((NY,NX,1),dtype=np.float32)
color=image('Chixiao_BaseColor',np.concatenate([np.clip(col,0,1),alpha],axis=2),'sRGB')
rough=np.clip(.40+noise*2+cloud*.8-silver*.12-band*.13,.18,.6)
metal=np.clip(np.ones((NY,NX),dtype=np.float32)*.98-band*.25,0,1)
ao=np.ones((NY,NX),dtype=np.float32)
orm=image('Chixiao_ORM',np.stack([ao,rough,metal,ao],axis=2),'Non-Color')
height=(grain*.00010+noise*.000045)
gy,gx=np.gradient(height,(TIP-ROOT)/NY,.09/NX)
norm=np.stack([-gx,-gy,np.ones_like(gx)],axis=2);norm/=np.linalg.norm(norm,axis=2,keepdims=True)
normal=image('Chixiao_Normal',np.concatenate([norm*.5+.5,alpha],axis=2),'Non-Color')
mat=bpy.data.materials.new('M_Chixiao_BladeSurface');mat.use_nodes=True
n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF')
bc=n.new('ShaderNodeTexImage');bc.image=color;l.new(bc.outputs['Color'],bs.inputs['Base Color'])
mr=n.new('ShaderNodeTexImage');mr.image=orm;sep=n.new('ShaderNodeSeparateColor');l.new(mr.outputs['Color'],sep.inputs['Color'])
l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
nm=n.new('ShaderNodeTexImage');nm.image=normal;node=n.new('ShaderNodeNormalMap');l.new(nm.outputs['Color'],node.inputs['Color']);l.new(node.outputs['Normal'],bs.inputs['Normal'])
gold=bpy.data.materials.new('M_Chixiao_Brass');gold.use_nodes=True
g=gold.node_tree.nodes.get('Principled BSDF');g.inputs['Base Color'].default_value=(.35,.19,.052,1);g.inputs['Metallic'].default_value=.92;g.inputs['Roughness'].default_value=.34
def create_lod(level,steps,cross_steps,cloud_steps):
    ts=sorted(set(np.linspace(0,1,steps).tolist()+KEY.tolist()))
    us=sorted(set(np.linspace(0,1,cross_steps).tolist()+[.025,.05,.13,.15,.17,.19,.215,.24,.72,.77]))
    verts=[];faces=[];uvs=[];mats=[]
    def face(ids,tex,material=0):faces.append(ids);uvs.append(tex);mats.append(material)
    # Each station is a clockwise closed cross-section with actual spine/edge thickness.
    ring=[(u,-1) for u in us]+[(u,1) for u in reversed(us)];N=len(ring)
    for t in ts:
        for u,side in ring:
            x,h=surface(t,u);verts.append((x,CY+side*h,ROOT+t*(TIP-ROOT)))
    for j in range(len(ts)-1):
        for k in range(N):
            q=(k+1)%N;a=ring[k][0];b=ring[q][0]
            # Thickness edges receive a real UV span instead of collapsed UVs.
            if abs(a-b)<1e-9:b=a+.004 if a<.5 else a-.004
            face((j*N+k,j*N+q,(j+1)*N+q,(j+1)*N+k),[(a,ts[j]),(b,ts[j]),(b,ts[j+1]),(a,ts[j+1])])
    for j in [0,len(ts)-1]:
        ids=tuple(j*N+k for k in range(N))
        face(ids,[(.5+verts[k][0]/.2,.5+verts[k][1]/.03) for k in ids])
    # Low relief clouds at the reinforced blade root, on both faces.
    paths=[]
    for z0,u0,size in [(.085,.33,.042),(.125,.54,.037),(.16,.38,.028)]:
        path=[]
        for k in range(cloud_steps):
            a=k/(cloud_steps-1)*math.pi*2.05;r=size*(1-.82*k/(cloud_steps-1))
            path.append((z0+math.cos(a)*r*.47,u0+math.sin(a)*r*5))
        paths.append(path)
    for side in [-1,1]:
        for path in paths:
            start=len(verts);B=6
            points=[]
            for t,u0 in path:
                x,h=surface(t,u0);points.append(Vector((x,CY+side*(h+.00018),ROOT+t*(TIP-ROOT))))
            for j,point in enumerate(points):
                tangent=(points[min(j+1,len(points)-1)]-points[max(0,j-1)]).normalized()
                across=Vector((tangent.z,0,-tangent.x)).normalized()
                for k in range(B):
                    a=k/B*math.tau;v=point+across*math.cos(a)*.00045+Vector((0,side*math.sin(a)*.00024,0));verts.append(tuple(v))
            for j in range(len(path)-1):
                for k in range(B):
                    face((start+j*B+k,start+j*B+(k+1)%B,start+(j+1)*B+(k+1)%B,start+(j+1)*B+k),
                         [(k/B,j/len(path)),((k+1)/B,j/len(path)),((k+1)/B,(j+1)/len(path)),(k/B,(j+1)/len(path))],1)
            for j in [0,len(path)-1]:
                face(tuple(start+j*B+k for k in range(B)),[(.5+.4*math.cos(k/B*math.tau),.5+.4*math.sin(k/B*math.tau)) for k in range(B)],1)
    name='SM_Zhanmadao_Blade_chixiao_V1_LOD'+str(level)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(mat);mesh.materials.append(gold)
    layer=mesh.uv_layers.new(name='UVMap')
    for f,coords,material in zip(mesh.polygons,uvs,mats):
        f.material_index=material;f.use_smooth=len(f.vertices)==4
        for li,tex in zip(f.loop_indices,coords):layer.data[li].uv=tex
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    obj=bpy.data.objects.new(name,mesh);S.collection.objects.link(obj);mesh.calc_loop_triangles()
    return obj,len(mesh.loop_triangles)
lods=[];counts=[]
for level,args in enumerate([(180,23,42),(90,16,25),(44,10,15)]):
    obj,count=create_lod(level,*args);lods.append(obj);counts.append(count)
name='SM_Zhanmadao_Blade_chixiao_V1';group=bpy.data.objects.new(name+'_LODGroup',None);group['fbx_type']='LodGroup';S.collection.objects.link(group)
for obj in lods:obj.parent=group
bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
for obj in lods:obj.select_set(True)
bpy.context.view_layer.objects.active=lods[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
for obj in lods[1:]:obj.hide_render=True;obj.hide_set(True)
# Keep the real hilt as an editable assembly reference without exporting it.
with bpy.data.libraries.load(str(P.parent/'Zhanmadao_Modular_Editable.blend'),link=False) as (available,loaded):
    loaded.objects=[n for n in ['SM_Zhanmadao_Guard_V1','SM_Zhanmadao_Grip_V1','SM_Zhanmadao_Pommel_V1'] if n in available.objects]
for obj in loaded.objects:S.collection.objects.link(obj)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Chixiao_Blade_Editable.blend'))
layout_t=np.linspace(.14,.90,9);zs=ROOT+layout_t*(TIP-ROOT)
layout={'z_cm':(zs*100).tolist(),'center_x_cm':[shape(t)[0]*100 for t in layout_t],
    'rune_width_cm':[shape(t)[1]*.55*100 for t in layout_t], 'blade_z_cm':[ROOT*100,TIP*100]}
# Shift the rune lane away from the recessed dorsal inlay, toward the broad face.
layout['center_x_cm']=[(shape(t)[0]+shape(t)[1]*.01)*100 for t in layout_t]
(P/'layout.json').write_text(json.dumps(layout,indent=2)+'\n',encoding='utf-8')
data={'id':'chixiao','name':'赤霄','mesh_name':name,'lod_triangles':counts,'material_slots':[mat.name,gold.name],
    'trace_base_cm':[CX*100,CY*100,reference['cuts_z_cm']['blade_guard']],
    'trace_tip_cm':[C[-1]*100,CY*100,TIP*100],'rune_dimensions_cm':[10,3,120],
    'seat_size_cm':[RW*100,RT*100],'seat_overlap_mm':.6,'rigid_length_cm':reference['reference']['rigid_length_cm'],
    'geometry':'new closed loft with recessed spine inlay/fullers and two-sided brass cloud relief',
    'texture_resolution':[NX,NY],'source':'Chixiao_Blade_Editable.blend','effects_applied':False,'game_tested':False}
(P/'exports.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CHIXIAO_BLADE_AUTHORED',counts,flush=True)
