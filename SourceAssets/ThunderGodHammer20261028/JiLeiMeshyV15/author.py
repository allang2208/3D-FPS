"""Fit the supplied Meshy seat to the native Thor interfaces, retaining corner UV/normals."""
import bpy,bmesh,math,json,hashlib,shutil
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
for d in ('Export','Integration'):(P/d).mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'JiLeiInlaidLightningV14/JiLei_V14_Editable.blend'))
keep=['20_NativeLeftHeadInterface','21_NativeRightHeadInterface','22_NativeNeckInterface']
context_names=['SM_ThunderGodHammer_hammer_heads_factory','SM_ThunderGodHammer_neck_factory','SM_ThunderGodHammer_shaft_factory']
for o in list(bpy.data.objects):
    if o.name not in keep+context_names:bpy.data.objects.remove(o,do_unlink=True)
parts=[bpy.data.objects[n] for n in keep]
for o in parts:o.hide_set(False);o.hide_render=False
for n in context_names:
    if n in bpy.data.objects:bpy.data.objects[n].hide_set(True);bpy.data.objects[n].hide_render=True
steel=bpy.data.materials['M_JiLei14_Steel'].copy();steel.name='M_JiLei15_InterfaceSteel'
for o in parts:
    for i,m in enumerate(o.data.materials):
        if m.name!='M_OriginalHammer_ContextPBR':o.data.materials[i]=steel
bpy.ops.import_scene.gltf(filepath=str(P/'Original/Meshy_AI_Nordic_Aegis_Shield_1101101638_texture.glb'))
src=next(o for o in bpy.context.selected_objects if o.type=='MESH')
mat=src.data.materials[0];mat.name='M_JiLei15_MeshyPBR';mat.use_backface_culling=True
for node in mat.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        name=node.image.name
        index=0 if name=='normal' else 2 if 'metallic_roughness' in name else 1
        node.image=bpy.data.images.load(str(P/'Textures'/('MeshySource_'+str(index)+'.png')),check_existing=True)
        node.image.colorspace_settings.name='sRGB' if index==1 else 'Non-Color'
me=src.data;me.calc_loop_triangles()
# Uniform author scale retains the medallion, depth and engraving. A continuous
# local shoulder fit retains all outer relief instead of slicing the crest tips.
CX=-.0004452141;CY=-.0010566595;SCALE=.08;TZ=.916
raw_x=max(abs(v.co.x*SCALE) for v in me.vertices);start=.033;target_width=.0593
def fit_x(x):
    r=abs(x)
    if r<=start:return x,1.
    span=raw_x-start;out=target_width-start;t=(r-start)/span
    y=(2*t**3-3*t*t+1)*0+(t**3-2*t*t+t)*span+(-2*t**3+3*t*t)*out+(t**3-t*t)*span*.35
    derivative=((3*t*t-4*t+1)*span+(-6*t*t+6*t)*out+(3*t*t-2*t)*span*.35)/span
    return math.copysign(start+y,x),derivative
fitted=[fit_x(v.co.x*SCALE) for v in me.vertices]
positions=[Vector((fitted[i][0]+CX,v.co.y*SCALE+CY,v.co.z*SCALE+TZ)) for i,v in enumerate(me.vertices)]
normals=[n.vector.copy() for n in me.corner_normals];uv=me.uv_layers[0]
for i,n in enumerate(normals):
    n.x/=fitted[me.loops[i].vertex_index][1];n.normalize()
def clip(poly,axis,level,positive):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-level)*(1 if positive else -1);db=(b[0][axis]-level)*(1 if positive else -1)
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return result
verts=[];faces=[];corners=[]
for tri in me.loop_triangles:
    poly=[(positions[me.loops[i].vertex_index],uv.data[i].uv.copy(),normals[i]) for i in tri.loops]
    poly=clip(poly,2,.850,True)
    if not poly:continue
    for k in range(1,len(poly)-1):
        t=[poly[0],poly[k],poly[k+1]]
        if (t[1][0]-t[0][0]).cross(t[2][0]-t[0][0]).length<1e-12:continue
        faces.append(tuple(range(len(verts),len(verts)+3)))
        for c in t:verts.append(c[0]);corners.append(c)
bodyme=bpy.data.meshes.new('Meshy fitted source');bodyme.from_pydata(verts,[],faces);bodyme.update();bodyme.materials.append(mat);bodyme.materials.append(steel)
uvout=bodyme.uv_layers.new(name='UVMap');stored=bodyme.attributes.new('PreservedNormal',type='FLOAT_VECTOR',domain='CORNER')
for face in bodyme.polygons:
    face.use_smooth=True
    for li in face.loop_indices:
        c=corners[bodyme.loops[li].vertex_index];uvout.data[li].uv=c[1];stored.data[li].vector=c[2].normalized()
bm=bmesh.new();bm.from_mesh(bodyme);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00000015)
# Close only new mounting cuts; existing generated surfaces are left intact.
boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-.850)<2e-6 for v in e.verts)]
caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces'] if boundary else []
caps=bmesh.ops.triangulate(bm,faces=caps)['faces'] if caps else []
normal_layer=bm.loops.layers.float_vector['PreservedNormal'];uvlayer=bm.loops.layers.uv[0]
for face in caps:
    face.material_index=1;face.smooth=False;face.normal_update()
    axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
    for loop in face.loops:loop[normal_layer]=face.normal;loop[uvlayer].uv=(loop.vert.co[axes[0]]/.06,loop.vert.co[axes[1]]/.06)
bm.to_mesh(bodyme);bm.free();bodyme.update()
bodyme.normals_split_custom_set([tuple(n.vector) for n in bodyme.attributes['PreservedNormal'].data])
body=bpy.data.objects.new('01_MeshyBody_OriginalUVAndNormals',bodyme);bpy.context.collection.objects.link(body);parts.append(body)
bpy.data.objects.remove(src,do_unlink=True)
bpy.context.view_layer.update();surface=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())

def native_inner_loops(obj,axis,value):
    # Edges shared by the native shell and its inner cut cap, in original coordinates.
    me=obj.data;me.calc_loop_triangles();links={};points={}
    def key(v):return tuple(round(float(c),7) for c in v)
    for tri in me.loop_triangles:
        p=[me.vertices[i].co.copy() for i in tri.vertices]
        on=[i for i,v in enumerate(p) if abs(v[axis]-value)<2e-6]
        if len(on)!=2:continue
        a,b=[key(p[i]) for i in on]
        if a==b:continue
        points[a]=p[on[0]];points[b]=p[on[1]];links.setdefault(a,set()).add(b);links.setdefault(b,set()).add(a)
    unused={tuple(sorted((a,b))) for a,ns in links.items() for b in ns};loops=[]
    while unused:
        a,b=next(iter(unused));path=[a];prev=a;cur=b;unused.discard(tuple(sorted((a,b))))
        while cur!=a:
            path.append(cur);choices=[n for n in links[cur] if tuple(sorted((cur,n))) in unused]
            if not choices:break
            nxt=choices[0];unused.discard(tuple(sorted((cur,nxt))));prev,cur=cur,nxt
        if cur==a and len(path)>8:loops.append([points[k] for k in path])
    return loops

bridge_records=[]
for name,axis,value,direction in [('20_NativeLeftHeadInterface',0,CX-.0595,Vector((1,0,0))),('21_NativeRightHeadInterface',0,CX+.0595,Vector((-1,0,0))),('22_NativeNeckInterface',2,.851,Vector((0,0,1)))]:
    obj=bpy.data.objects[name]
    loops=native_inner_loops(obj,axis,value)
    if not loops:raise RuntimeError('No native inner cross-section: '+name)
    for loop_index,profile in enumerate(loops):
        axes=[i for i in range(3) if i!=axis]
        center=Vector((CX,CY,.911)) if axis==0 else Vector((CX,CY,.862))
        if axis==0:center.x=CX+math.copysign(.039,value-CX)
        radial=[];N=360
        for j in range(N):
            a=j*math.tau/N;d=Vector((0,0,0));d[axes[0]]=math.cos(a);d[axes[1]]=math.sin(a)
            hit=surface.ray_cast(center+d*.15,-d,.15)
            if hit[0] is None:raise RuntimeError('Open body cross-section at '+name)
            radial.append((hit[0]-center).length)
        # Preserve the measured section while removing tiny ornamental noise in
        # the buried end of the transition. Parameterization stays circular and
        # continuous; independent nearest-point jumps cannot create metal spikes.
        radii=np.asarray(radial)
        radii=sum(np.roll(radii,k)*w for k,w in [(-2,1),(-1,2),(0,3),(1,2),(2,1)])/9
        targets=[]
        native_center=Vector((CX,CY,.911))
        for point in profile:
            a=math.atan2(point[axes[1]]-native_center[axes[1]],point[axes[0]]-native_center[axes[0]])%math.tau
            t=a/math.tau*N;j=int(t)%N;q=t-int(t);radius=max(.001,radii[j]*(1-q)+radii[(j+1)%N]*q-.0015)
            target=center.copy();target[axes[0]]+=radius*math.cos(a);target[axes[1]]+=radius*math.sin(a);targets.append(target)
        vs=[];count=len(profile)
        # A continuous load web from the unmodified native contour into the Meshy solid.
        for t in (0,.25,.5,.75,1):
            for a,b in zip(profile,targets):vs.append(a.lerp(b,t))
        fs=[]
        for ring in range(4):
            for j in range(count):
                a=ring*count+j;b=ring*count+(j+1)%count;c=b+count;d=a+count
                fs.extend(((a,b,c),(a,c,d)))
        fs.extend((tuple(range(count-1,-1,-1)),tuple(4*count+j for j in range(count))))
        mesh=bpy.data.meshes.new(name+'_ContinuousWeb');mesh.from_pydata(vs,[],fs);mesh.materials.append(steel);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
        uv=mesh.uv_layers.new(name='UVMap')
        for f in mesh.polygons:
            f.use_smooth=len(f.vertices)==3
            axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
            for li in f.loop_indices:
                p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.06,p[axes[1]]/.06)
        web=bpy.data.objects.new(name+'_ContinuousWeb_'+str(loop_index),mesh);bpy.context.collection.objects.link(web);parts.append(web)
        bridge_records.append(dict(interface=name,inner_plane=value,contour_vertices=count,max_connection_m=max((a-b).length for a,b in zip(profile,targets))))

# Blue inlays receive low emission from their actual color-channel mask; steel remains opaque.
ns=mat.node_tree.nodes;ls=mat.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
base=bs.inputs['Base Color'].links[0].from_socket
sep=ns.new('ShaderNodeSeparateColor');ls.new(base,sep.inputs[0])
mx=ns.new('ShaderNodeMath');mx.operation='MAXIMUM';ls.new(sep.outputs['Red'],mx.inputs[0]);ls.new(sep.outputs['Green'],mx.inputs[1])
sub=ns.new('ShaderNodeMath');sub.operation='SUBTRACT';ls.new(sep.outputs['Blue'],sub.inputs[0]);ls.new(mx.outputs[0],sub.inputs[1])
mul=ns.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.use_clamp=True;mul.inputs[1].default_value=3.0;ls.new(sub.outputs[0],mul.inputs[0])
bs.inputs['Emission Color'].default_value=(.025,.22,.65,1);ls.new(mul.outputs[0],bs.inputs['Emission Strength'])

bpy.ops.object.select_all(action='DESELECT');copies=[]
for o in parts:
    c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);c.hide_set(False);c.hide_render=False;c.select_set(True);copies.append(c)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='SM_ThunderGodHammer_head_mount_ji_lei_seat_V15'
joined.data.calc_loop_triangles()
fbx=P/'Export'/(joined.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.export_scene.gltf(filepath=str(P/'Export/JiLei_V15.glb'),export_format='GLB',use_selection=True,export_apply=True)
joined.hide_set(True);joined.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'JiLei_V15_Editable.blend'))
used={p.material_index for p in joined.data.polygons};rows=[]
for i,m in enumerate(joined.data.materials):
    if i not in used:continue
    if m.name=='M_OriginalHammer_ContextPBR':rows.append(dict(slot=m.name,kind='native'))
    elif m==steel:rows.append(dict(slot=m.name,kind='reuse',asset='/Game/Weapons/ThunderGodHammer20261028/JiLeiInlaidLightningV14/Materials/M_JiLei14_Steel'))
    elif m==mat:rows.append(dict(slot=m.name,kind='pbr',family='Meshy',tint=[1.,1.,1.],normal_strength=1.,emissive_mask='blue_minus_max_red_green'))
    else:raise RuntimeError('Unexpected material: '+m.name)
for index,kind in [(0,'Normal'),(1,'BaseColor'),(2,'ORM')]:shutil.copy2(P/'Textures'/('MeshySource_'+str(index)+'.png'),P/'Textures'/('T_JiLei15_Meshy_'+kind+'.png'))
manifest=dict(revision='JiLeiMeshyV15',mesh=joined.name,fbx=str(fbx),fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),source_blend=str(P/'JiLei_V15_Editable.blend'),triangles=len(joined.data.loop_triangles),materials=rows,objects=[o.name for o in parts],interfaces=bridge_records,uniform_source_scale=SCALE,local_shoulder_fit=dict(unchanged_core_half_width_m=start,outer_half_width_m=target_width,method='monotonic cubic Hermite; inverse-Jacobian custom normals'),source_translation_m=[CX,CY,TZ],native_outer_interfaces_m=dict(left=CX-.065,right=CX+.065,neck=.842),runtime_tested=False)
(P/'Integration/runtime_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('JILEI_V15_AUTHORED',manifest['triangles'],bridge_records,flush=True)
