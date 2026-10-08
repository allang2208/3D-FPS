"""Offline Meshy reduction integration. Keeps production rigs and authored anatomy.

Run one species per background Blender process. No UE, previews, or tests.
"""
import bpy, bmesh, numpy as np
import sys, json, struct, shutil, hashlib, math, heapq, time, traceback, gc
from pathlib import Path
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/AlienGeometry20261006/RemeshV3'
SOURCES = json.loads((ROOT.parent/'BlenderV2/source_inputs.json').read_text(encoding='utf8'))
INPUTS = {
 'SpiralPillarM14': 'Meshy_AI_Veiled_Maw_M_14_1006155759_texture.glb',
 'M10Mawcrawler': 'Meshy_AI_M_10_Mawcrawler_1006155813_texture.glb',
 'HangingBellM09': 'Meshy_AI_Bound_Oculamoth_1006155727_texture.glb',
 'LurkerM08': 'Meshy_AI_Mawbound_Leviathan_1006155754_texture.glb',
}
SPECIES = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'SpiralPillarM14'
OUT = ROOT/SPECIES
OUT.mkdir(parents=True, exist_ok=True)
START = time.time()
REPORT = dict(species=SPECIES, complete=False, ue_imported=False, tested=False,
              input_origin='User remeshed the original Meshy source', materials={}, lods=[])

def log(message): print('REMESH_V3 '+SPECIES+' '+str(message), flush=True)
def record():
    REPORT['seconds'] = round(time.time()-START, 2)
    (OUT/'authoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def glb(path):
    raw=Path(path).read_bytes(); length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]); binary=raw[28+length:]
    def read(i):
        a=doc['accessors'][i]; v=doc['bufferViews'][a['bufferView']]
        dt={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
        width={'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']]
        return np.ndarray((a['count'],width),dtype=dt,buffer=binary,
          offset=v.get('byteOffset',0)+a.get('byteOffset',0),
          strides=(v.get('byteStride',np.dtype(dt).itemsize*width),np.dtype(dt).itemsize)).copy()
    pr=doc['meshes'][0]['primitives'][0]
    return doc,binary,read(pr['attributes']['POSITION']),read(pr['indices']).reshape(-1,3),read(pr['attributes']['TEXCOORD_0'])

def coords(obj):
    p=np.empty((len(obj.data.vertices),3),np.float32); obj.data.vertices.foreach_get('co',p.ravel())
    m=np.asarray(obj.matrix_world); return p@m[:3,:3].T+m[:3,3]

def triangles(obj):
    obj.data.calc_loop_triangles()
    f=np.empty((len(obj.data.loop_triangles),3),np.int32)
    obj.data.loop_triangles.foreach_get('vertices',f.ravel())
    return f

class Projection:
    def __init__(self,p,f):
        self.p=p; self.f=f
        self.tree=BVHTree.FromPolygons(p.tolist(),f.tolist(),all_triangles=True)
    def at(self,q):
        idx=np.empty(len(q),np.int32); hit=np.empty_like(q,dtype=np.float64)
        for i,point in enumerate(q):
            location,normal,j,distance=self.tree.find_nearest(point)
            if j is None: raise RuntimeError('Empty source surface')
            idx[i]=j;hit[i]=location
        tri=self.p[self.f[idx]]; a=tri[:,1]-tri[:,0]; b=tri[:,2]-tri[:,0]; d=hit-tri[:,0]
        aa=(a*a).sum(1); ab=(a*b).sum(1); bb=(b*b).sum(1)
        da=(d*a).sum(1); db=(d*b).sum(1); den=aa*bb-ab*ab
        den=np.where(abs(den)>1e-25,den,1.)
        u=(bb*da-ab*db)/den; v=(aa*db-ab*da)/den
        bary=np.maximum(np.stack([1-u-v,u,v],axis=1),0)
        bary/=np.maximum(bary.sum(1,keepdims=True),1e-20)
        return idx,bary
    def sample(self,values,idx,bary):
        return np.einsum('ij,ij...->i...',bary,values[self.f[idx]])

def material(source,new_texture):
    key=('R3_' if new_texture else 'Kept_')+source.name.replace('.','_')
    if key in REPORT['materials']: return bpy.data.materials[key]
    mat=source.copy();mat.name=key
    REPORT['materials'][key]=dict(source_material_name=source.name,new_texture=new_texture)
    if new_texture:
        # The new Meshy atlas must stay paired with its own UVs.
        mat.use_nodes=True; nodes=mat.node_tree.nodes; links=mat.node_tree.links; nodes.clear()
        output=nodes.new('ShaderNodeOutputMaterial'); shader=nodes.new('ShaderNodeBsdfPrincipled')
        links.new(shader.outputs['BSDF'],output.inputs['Surface'])
        for role,path in REPORT['textures'].items():
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(path,check_existing=True)
            if role!='BaseColor':tex.image.colorspace_settings.name='Non-Color'
            if role=='BaseColor':links.new(tex.outputs['Color'],shader.inputs['Base Color'])
            elif role=='Normal':
                normal=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color'])
                links.new(normal.outputs['Normal'],shader.inputs['Normal'])
            elif role=='MetallicRoughness':
                sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs['Color'])
                links.new(sep.outputs['Green'],shader.inputs['Roughness']);links.new(sep.outputs['Blue'],shader.inputs['Metallic'])
    return mat

def make_mesh(name,p,f,uv,mats,face_material=None):
    data=bpy.data.meshes.new(name);data.from_pydata(p.tolist(),[],f.tolist());data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    layer=data.uv_layers.new(name='UVMap')
    layer.data.foreach_set('uv',np.asarray(uv[f],np.float32).ravel())
    for mat in mats:data.materials.append(mat)
    if face_material is not None:data.polygons.foreach_set('material_index',np.asarray(face_material,np.int32))
    data.polygons.foreach_set('use_smooth',np.ones(len(data.polygons),bool))
    return obj

def bind(obj,rig):
    world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world
    arm=next((m for m in obj.modifiers if m.type=='ARMATURE'),None) or obj.modifiers.new('ProductionRig','ARMATURE')
    arm.object=rig;arm.show_viewport=True;arm.show_render=True

def transfer(source,target,rig,limit=8,projection=None,queries=None,morphs=True):
    log('transfer '+source.name+' -> '+target.name)
    projection=projection or Projection(coords(source),triangles(source))
    idx,bary=projection.at(coords(target) if queries is None else queries)
    bone_names=[g.name for g in source.vertex_groups if g.name in rig.data.bones]
    names={name:i for i,name in enumerate(bone_names)}
    lookup={g.index:names[g.name] for g in source.vertex_groups if g.name in names}
    weights=np.zeros((len(source.data.vertices),len(names)),np.float32)
    for vert in source.data.vertices:
        for group in vert.groups:
            if group.group in lookup:weights[vert.index,lookup[group.group]]=group.weight
    weights=projection.sample(weights,idx,bary)
    target.vertex_groups.clear()
    for name in bone_names:target.vertex_groups.new(name=name)
    order=np.argsort(weights,axis=1)[:,-limit:]
    selected=np.take_along_axis(weights,order,axis=1);selected/=np.maximum(selected.sum(1,keepdims=True),1e-20)
    for i,(indices,values) in enumerate(zip(order,selected)):
        for j,w in zip(indices,values):
            if w>1e-6:target.vertex_groups[int(j)].add([i],float(w),'REPLACE')
    if morphs and source.data.shape_keys:
        basis=source.data.shape_keys.key_blocks[0]
        bp=np.empty((len(basis.data),3),np.float32);basis.data.foreach_get('co',bp.ravel())
        tp=coords(target); inv=np.asarray(target.matrix_world.inverted())[:3,:3]
        rot=np.asarray(source.matrix_world)[:3,:3]
        target.shape_key_add(name='Basis')
        for key in list(source.data.shape_keys.key_blocks)[1:]:
            kp=np.empty_like(bp);key.data.foreach_get('co',kp.ravel())
            delta=projection.sample((kp-bp)@rot.T,idx,bary)@inv.T
            new=target.shape_key_add(name=key.name);new.data.foreach_set('co',np.asarray(tp+delta,np.float32).ravel())
            new.slider_min=key.slider_min;new.slider_max=key.slider_max
    bind(target,rig)
    return projection,idx,bary

def duplicate(obj,name):
    copy=obj.copy();copy.data=obj.data.copy();copy.name=name
    bpy.context.scene.collection.objects.link(copy);copy.hide_set(False);copy.hide_viewport=False
    return copy

def decimate(obj,ratio):
    if ratio>=.999:return
    if obj.data.shape_keys:obj.shape_key_clear()
    for m in list(obj.modifiers):
        if m.type=='ARMATURE':obj.modifiers.remove(m)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('OfflineReduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name)

def prepare_m14(raw,f,uv,source,rig):
    src=source['M14_SoftDeathMesh']; factor=float(rig['source_scale'])
    original=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/Original/Meshy_AI_Veiled_Maw_M_14_1004025810_texture.glb'
    _,_,op,_,_=glb(original)
    p=np.stack([raw[:,0]*factor,-raw[:,2]*factor,(raw[:,1]-op[:,1].min())*factor],axis=1)
    proj=Projection(coords(src),triangles(src));idx,_=proj.at(p[f].mean(1))
    poly=np.empty(len(src.data.loop_triangles),np.int32);src.data.loop_triangles.foreach_get('polygon_index',poly)
    mi=np.asarray([p.material_index for p in src.data.polygons],np.int32)
    obj=make_mesh('M14_RemeshV3',p,f,uv,[material(m,True) for m in src.data.materials],mi[poly[idx]])
    transfer(src,obj,rig,projection=proj)
    REPORT['retained_design']=['V15 support skin weights','nine existing death shape keys','four material regions','49-bone production skeleton']
    return [obj]

def prepare_m10(raw,f,uv,source,rig):
    base=PROJECT/'SourceAssets/M10ChenXia20261003'
    a=np.load(base/'RigV1/source_geometry.npz'); d=np.load(base/'SurfaceRigV5/surface_rig_data.npz')
    op=a['original'][:,[2,0,1]]; factor=4.2/np.ptp(op[:,0])
    offset=np.array([(op[:,0].min()+op[:,0].max())*.5,(op[:,1].min()+op[:,1].max())*.5,op[:,2].min()])
    p=(raw[:,[2,0,1]]-offset)*factor
    center=p[f].mean(1); radius=np.sqrt((center[:,1]/.39)**2+((center[:,2]-.323)/.139)**2)
    f=f[~((radius<.955)&(center[:,0]>1.56))]
    ids,inv=np.unique(f,return_inverse=True);p=p[ids];uv=uv[ids];f=inv.reshape(-1,3)
    original_projection=Projection(a['vertices'],a['faces'])
    idx,bary=original_projection.at(p)
    displacement=original_projection.sample(d['displacement'][a['inverse']],idx,bary)
    p+=displacement
    src=source['M10_OriginalSurface']
    obj=make_mesh('M10_RemeshV3',p,f,uv,[material(src.data.materials[0],True)])
    # The same pre-displacement correspondence carries tissue motion without
    # projecting across the newly opened mouth onto its opposite lip.
    transfer(src,obj,rig,limit=4,morphs=False)
    obj.shape_key_add(name='Basis')
    for name,key in [('M10_MouthOpenTissue','open_delta'),('M10_MouthWideTissue','wide_delta')]:
        delta=original_projection.sample(d[key][a['inverse']],idx,bary)
        morph=obj.shape_key_add(name=name);morph.data.foreach_set('co',np.asarray(p+delta,np.float32).ravel())
    result=[obj]
    for name in ('M10_OralLiner','M10_OralTeeth','M10_OralGum'):
        keep=duplicate(source[name],name+'_KeptV5');keep.data.materials.clear()
        for mat in source[name].data.materials:keep.data.materials.append(material(mat,False))
        result.append(keep)
    REPORT['retained_design']=['V5 eye and face displacement','opened oral seam','authored mouth liner, gums and teeth','two tissue morphs','62-bone production skeleton']
    return result

def back_aperture(obj,inner):
    # Identical V01 bore profile and V02 local fairing, operating on the user's
    # reduced body. The existing inner-wall texture atlas remains applicable.
    n=128;length=96;half=1.10;cx=-.00055;cz=.205
    def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
    verts=[];faces=[]
    for k in range(length+1):
        y=-half+2*half*k/length;flare=.015*smooth(abs(y-.08)/.9)
        for j in range(n):
            t=2*math.pi*j/n;wave=1+.012*math.cos(4*t)+.007*math.cos(10*t)*math.cos(2*y)
            verts.append((cx+(.105+flare)*math.cos(t)*wave,y,cz+(.121+flare*.30)*math.sin(t)*wave))
    for k in range(length):
        for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    faces.extend([tuple(reversed(range(n))),tuple(length*n+j for j in range(n))])
    data=bpy.data.meshes.new('DorsalBore');data.from_pydata(verts,[],faces);data.update()
    cutter=bpy.data.objects.new('DorsalBore',data);bpy.context.scene.collection.objects.link(cutter)
    data.materials.append(obj.data.materials[0]);data.materials.append(inner)
    data.polygons.foreach_set('material_index',np.ones(len(data.polygons),np.int32))
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('AcceptedDorsalBore','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;mod.material_mode='TRANSFER'
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(obj.data)
    edges=[e for e in bm.edges if len(e.link_faces)==2 and e.link_faces[0].material_index!=e.link_faces[1].material_index]
    bmesh.ops.bevel(bm,geom=edges,offset=.006,segments=4,profile=.5,affect='EDGES',clamp_overlap=True,loop_slide=True,material=1)
    layer=bm.loops.layers.uv.active
    for face in bm.faces:
        if face.material_index!=1:continue
        us=[]
        for loop in face.loops:
            co=loop.vert.co;flare=.015*smooth(abs(co.y-.08)/.9)
            us.append((math.atan2((co.z-cz)/(.121+flare*.30),(co.x-cx)/(.105+flare))%(2*math.pi))/(2*math.pi))
        seam=max(us)-min(us)>.5
        for loop,u in zip(face.loops,us):loop[layer].uv=(u+1 if seam and u<.5 else u,(loop.vert.co.y+half)/(2*half))
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    def eligible(v):x,y,z=v.co;return abs(x)<.27 and -.73<y<.89 and z>.052
    seeds={v for f in bm.faces if f.material_index==1 for v in f.verts if eligible(v)}
    distance=np.full(len(bm.verts),np.inf);queue=[]
    for v in seeds:distance[v.index]=0;heapq.heappush(queue,(0.,v.index))
    while queue:
        d,i=heapq.heappop(queue)
        if d>distance[i] or d>.038:continue
        for edge in bm.verts[i].link_edges:
            v=edge.other_vert(bm.verts[i]);nd=d+edge.calc_length()
            if eligible(v) and nd<.038 and nd<distance[v.index]:distance[v.index]=nd;heapq.heappush(queue,(nd,v.index))
    weight=bm.verts.layers.float.new('M08_V02_LocalFairingWeight')
    for v in bm.verts:v[weight]=float((1-smooth(distance[v.index]/.038))*smooth((v.co.z-.052)/.035))
    for _ in range(3):
        edges=[e for e in bm.edges if min(v[weight] for v in e.verts)>.025 and e.calc_length()>.008]
        if not edges:break
        bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True,smooth=0.)
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    weights=np.asarray([v[weight] for v in bm.verts]);pairs=np.asarray([(e.verts[0].index,e.verts[1].index) for e in bm.edges if any(v[weight]>.00001 for v in e.verts)])
    ids=np.unique(pairs);mapping=np.full(len(bm.verts),-1);mapping[ids]=np.arange(len(ids));pairs=mapping[pairs]
    p=np.asarray([tuple(bm.verts[int(i)].co) for i in ids]);initial=p.copy();w=weights[ids]
    theta=np.arctan2((p[:,2]-cz)/.121,(p[:,0]-cx)/.105)
    p[:,0]+=w*(-.10*np.sin(theta)+.018*np.cos(4*theta))*(p[:,0]-cx);p[:,2]+=w*.0045*np.cos(2*theta)
    a,b=pairs.T;edge_weights=1/np.maximum(np.linalg.norm(initial[a]-initial[b],axis=1),.001)
    start=np.r_[a,b];end=np.r_[b,a];edge_weights=np.r_[edge_weights,edge_weights];den=np.bincount(start,weights=edge_weights,minlength=len(ids))
    for _ in range(120):
        for factor in (.45,-.46):
            total=np.column_stack([np.bincount(start,weights=p[end,c]*edge_weights,minlength=len(ids)) for c in range(3)])
            p+=factor*w[:,None]*(total/np.maximum(den[:,None],1e-12)-p)
    for i,co in zip(ids,p):bm.verts[int(i)].co=co
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bm.normal_update();bm.to_mesh(obj.data);bm.free()

def prepare_m08(raw,f,uv,source,rig):
    src=source['SK_LurkerM08'];p=raw[:,[0,2,1]].copy();p[:,1]*=-1
    obj=make_mesh('M08_RemeshV3',p,f,uv,[material(src.data.materials[0],True),material(src.data.materials[1],False)])
    log('restore dorsal aperture and local organic transition')
    back_aperture(obj,obj.data.materials[1])
    original=json.loads((PROJECT/'SourceAssets/Monsters/LurkerM08/ProductionV01_20261004/authoring.json').read_text())
    scale=original['scale'];pelvis=next(b for b in original['bones'] if b['name']=='pelvis')
    offset=np.asarray(pelvis['head'])/scale-np.array([0,.52,-.055])
    obj.data.vertices.foreach_set('co',np.asarray((coords(obj)+offset)*scale,np.float32).ravel());obj.data.update()
    transfer(src,obj,rig,limit=4)
    REPORT['retained_design']=['V01 dorsal bore','V02 organic rim fairing and inner atlas','V03 canine surface skin','70-bone production skeleton']
    return [obj]

def cap_boundaries(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    # Meshy exports split UV seams. Weld positional duplicates while retaining
    # loop UVs, so only actual semantic cuts receive an inset closure.
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    edges=[e for e in bm.edges if e.is_boundary]
    if edges:
        result=bmesh.ops.holes_fill(bm,edges=edges,sides=0)
        for face in result['faces']:face.material_index=len(obj.data.materials)-1
        bmesh.ops.triangulate(bm,faces=result['faces'])
    bm.normal_update();bm.to_mesh(obj.data);bm.free();obj.data.update()

def prepare_m09(raw,f,uv,source,rig):
    base=PROJECT/'SourceAssets/HangingBellM09Meshy20261003'
    a=np.load(base/'Authoring/source_arrays.npz');r=np.load(base/'Authoring/semantic_parts_v02.npz')
    recipe=json.loads((base/'Records/parts_recipe_v02.json').read_text());manifest=json.loads((base/'Records/source_manifest.json').read_text())
    projection=Projection(a['positions'],a['faces']);faceids,_=projection.at(raw[f].mean(1))
    labels=r['face_labels'][faceids];scale=manifest['scale_to_280cm'];bottom=manifest['source_min_y'];result=[]
    for label,name in enumerate(recipe['part_names']):
        # Original cuffs were merged into the approved continuous arms in V16.
        if label in (8,9,15,16) or name not in source:continue
        fs=f[labels==label]
        if not len(fs):raise RuntimeError('Missing reduced semantic part '+name)
        ids,inv=np.unique(fs,return_inverse=True);p=raw[ids].copy();lf=inv.reshape(-1,3)
        if 1<=label<=6:
            idx,bary=projection.at(p)
            p+=projection.sample(r['membrane_delta'][label,a['weld_ids']],idx,bary)
        elif label in recipe['digit_ids']:
            sign=1 if '_L_' in name else -1;k=int(name[-2:])-1
            t=np.clip((p[:,1]-.805)/.08,0,1);w=t*t*(3-2*t)
            p[:,0]+=sign*(k-2)*.0028*w;p[:,2]+=(.0015 if k%2 else -.0015)*w
        p=np.stack([p[:,0]*scale,-p[:,2]*scale,(p[:,1]-bottom)*scale],axis=1)
        src=source[name];obj=make_mesh(name+'_RemeshV3',p,lf,uv[ids],[material(m,True) for m in src.data.materials])
        cap_boundaries(obj);transfer(src,obj,rig,limit=5);result.append(obj)
    for name in ('M09_SmallArm_L','M09_SmallArm_R'):
        src=source[name];obj=duplicate(src,name+'_KeptV16');obj.data.materials.clear()
        for mat in src.data.materials:obj.data.materials.append(material(mat,False))
        decimate(obj,18000/len(triangles(src)));bind(obj,rig);result.append(obj)
    REPORT['retained_design']=['six separate unfolded membranes','five independent eyes','ten hooked fingers','V16 continuous shoulders and wrists','114-bone production skeleton']
    return result

def export(objects,rig,path):
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False);rig.select_set(True)
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    common=dict(use_selection=True,object_types={'ARMATURE','MESH'},bake_anim=False,add_leaf_bones=False,
        use_mesh_modifiers=False,apply_unit_scale=True,path_mode='STRIP')
    if SPECIES in ('SpiralPillarM14','HangingBellM09'):
        common.update(apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_armature_deform_only=True,armature_nodetype='NULL',mesh_smooth_type='FACE')
    else:
        common.update(apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',use_armature_deform_only=False,mesh_smooth_type='OFF')
    bpy.ops.export_scene.fbx(filepath=str(path),**common)

def run():
    incoming=Path('C:/Users/allan/Downloads/重拓扑')/INPUTS[SPECIES]
    archive=OUT/'Input'/incoming.name;archive.parent.mkdir(exist_ok=True)
    if not archive.exists():shutil.copy2(incoming,archive)
    doc,binary,p,f,uv=glb(archive);uv[:,1]=1-uv[:,1]
    REPORT.update(source=str(PROJECT/SOURCES[SPECIES]['source']),input=str(archive),input_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),input_triangles=len(f),textures={})
    mat=doc['materials'][0];pbr=mat['pbrMetallicRoughness']
    texids={'BaseColor':pbr['baseColorTexture']['index'],'MetallicRoughness':pbr['metallicRoughnessTexture']['index'],'Normal':mat['normalTexture']['index']}
    texdir=OUT/'Textures';texdir.mkdir(exist_ok=True)
    for role,idx in texids.items():
        im=doc['images'][doc['textures'][idx]['source']];view=doc['bufferViews'][im['bufferView']]
        file=texdir/(role+('.png' if im['mimeType']=='image/png' else '.jpg'))
        file.write_bytes(binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]);REPORT['textures'][role]=str(file)
    del binary,doc
    bpy.ops.wm.open_mainfile(filepath=REPORT['source'],load_ui=False)
    source={o.name:o for o in bpy.context.scene.objects if o.type=='MESH'}
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear();rig.data.pose_position='REST'
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    for obj in source.values():
        obj.hide_viewport=False;obj.hide_set(False)
        if obj.data.shape_keys:
            obj.data.shape_keys.animation_data_clear()
            for key in obj.data.shape_keys.key_blocks:key.value=0
        for mod in obj.modifiers:
            if mod.type=='ARMATURE':mod.show_viewport=False
    bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    builder={'SpiralPillarM14':prepare_m14,'M10Mawcrawler':prepare_m10,'LurkerM08':prepare_m08,'HangingBellM09':prepare_m09}[SPECIES]
    result=builder(p,f,uv,source,rig);record()
    for obj in list(bpy.context.scene.objects):
        if obj not in result and obj!=rig:bpy.data.objects.remove(obj,do_unlink=True)
    source.clear();gc.collect()
    for im in bpy.data.images:
        if im.users and not im.packed_file:im.pack()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(SPECIES+'_RemeshV3.blend')),compress=True)
    for level,ratio in enumerate((1.,.38,.14,.05)):
        log('export offline LOD '+str(level))
        objects=result if level==0 else []
        if level:
            for src in result:
                obj=duplicate(src,src.name+'_LOD'+str(level));decimate(obj,ratio)
                if src.data.shape_keys:transfer(src,obj,rig,limit=8)
                else:bind(obj,rig)
                objects.append(obj)
        file=OUT/(SPECIES+'_LOD'+str(level)+'.fbx');export(objects,rig,file)
        REPORT['lods'].append(dict(level=level,file=str(file),triangles=sum(len(triangles(o)) for o in objects),
            vertices=sum(len(o.data.vertices) for o in objects),morphs=sorted({k.name for o in objects if o.data.shape_keys for k in o.data.shape_keys.key_blocks if k.name!='Basis'})))
        record()
        if level:
            for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
    REPORT.update(complete=True,blend=str(OUT/(SPECIES+'_RemeshV3.blend')),bones=[b.name for b in rig.data.bones],animations_reauthored=False)
    record();log('SAVED '+json.dumps(REPORT['lods']))

if __name__=='__main__':
    try:run()
    except Exception:
        REPORT['error']=traceback.format_exc();record();raise
