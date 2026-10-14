"""Tailored gardener layers, fixed barycentric FR binding, and physical-scale PBR."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/EcologyGardener20261014/V02'
SOURCE=PROJECT/'SourceAssets/EcologyGardener20261014/V01/Authoring/EcologyGardener_V01.blend'
for d in ('Authoring','Delivery','Textures','Logs'):(ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['root'];coat=bpy.data.objects['Researcher_LabCoat_Continuous']
body=bpy.data.objects['Researcher_CompleteBody'];display=bpy.data.objects['Researcher_OutfitBody']
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(0)
for o in list(bpy.context.scene.objects):
    if o.name.startswith(('Gardener_Waterproof','Gardener_Shoulder','Gardener_Waist','Gardener_Bib','Researcher_HipPocket')):
        bpy.data.objects.remove(o,do_unlink=True)

def material(family,color,rough,kind='cloth'):
    """Shared 20 cm tile: millimetre weave/grain; linear normal and ORM."""
    size=2048 if family in ('Workwear','Apron') else 1024
    yy,xx=np.mgrid[:size,:size].astype(np.float32);u=xx/size;v=yy/size
    rng=np.random.default_rng(214+len(family));grain=np.zeros_like(u);macro=np.zeros_like(u)
    for k in range(9):
        a,b=rng.integers(25,180,2);phase=float(rng.uniform(0,2*math.pi))
        grain+=np.sin(2*math.pi*(a*u+b*v)+phase)/9
    for a,b,phase in ((2,3,.4),(5,-2,1.7),(8,5,2.1)):
        macro+=np.sin(2*math.pi*(a*u+b*v)+phase)/3
    if kind=='cloth':
        warp=np.sin(2*math.pi*u*224);weft=np.sin(2*math.pi*v*224)
        over=np.sin(2*math.pi*(u-v)*112)
        height=.000055*(warp*(.5+.5*over)+weft*(.5-.5*over))+.000018*grain
        tone=.045*over+.025*macro;rv=rough-.025*over+.035*macro;metal=0.
    elif kind=='leather':
        creases=np.exp(-np.square(np.sin(2*math.pi*(u*7+v*3))/.16))
        height=.00009*grain-.00008*creases+.00005*macro
        tone=.065*macro+.035*grain-.025*creases;rv=rough+.055*grain+.06*macro;metal=0.
    elif kind=='metal':
        height=.000009*grain+.000012*np.sin(2*math.pi*v*280)
        tone=.035*macro;rv=rough+.07*macro;metal=.88
    else:
        height=.000025*grain;tone=.025*macro;rv=rough+.045*macro;metal=0.
    dy,dx=np.gradient(height,.2/size)
    normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    base=np.clip(np.asarray(color,dtype=np.float32)[None,None,:]*(1+tone[:,:,None]),0,1)
    orm=np.ones((size,size,3),np.float32);orm[:,:,0]=np.clip(1-abs(grain)*.06,.85,1)
    orm[:,:,1]=np.clip(rv,.2,.94);orm[:,:,2]=metal
    name='GardenerV02_'+family;mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bs=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None) or nodes.new('ShaderNodeBsdfPrincipled')
    output=next((n for n in nodes if n.type=='OUTPUT_MATERIAL'),None) or nodes.new('ShaderNodeOutputMaterial')
    links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    bs.inputs['Sheen Weight'].default_value=.1 if kind=='cloth' else 0
    for suffix,array in [('BaseColor',base),('Normal',normal*.5+.5),('ORM',orm)]:
        im=bpy.data.images.new(name+'_'+suffix,width=size,height=size,alpha=False)
        # Pixel fields already contain sRGB for color and linear data for other maps.
        im.colorspace_settings.name='Non-Color'
        rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=array
        im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(ROOT/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save()
        if suffix=='BaseColor':im.colorspace_settings.name='sRGB'
        tex=nodes.new('ShaderNodeTexImage');tex.image=im
        if suffix=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif suffix=='Normal':
            nm=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:
            sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs['Color'])
            links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    return mat

mats={
    'Workwear':material('Workwear',(.30,.34,.23),.79),
    'Apron':material('Apron',(.30,.17,.085),.48,'leather'),
    'Trousers':material('Trousers',(.145,.17,.12),.85),
    'Rubber':material('Rubber',(.085,.10,.075),.61,'rubber'),
    'Binding':material('Binding',(.38,.34,.24),.81),
    'Hardware':material('Hardware',(.45,.37,.22),.38,'metal')
}
def dress(o,mat):
    o.data.materials.clear();o.data.materials.append(mat)
    for face in o.data.polygons:face.material_index=0
for o in bpy.context.scene.objects:
    if o==coat:dress(o,mats['Workwear'])
    elif o.name=='Researcher_Trousers':dress(o,mats['Trousers'])
    elif o.name.startswith(('Researcher_ClosedShoe','Gardener_RubberBoot')):dress(o,mats['Rubber'])

# Stable reference triangles drive every new panel, edge, stitch and buckle.
coat.data.calc_loop_triangles();outer=int(coat['outer_vertex_count'])
cp=np.array([v.co[:] for v in coat.data.vertices],np.float32)
tri=np.array([t.vertices[:] for t in coat.data.loop_triangles if max(t.vertices)<outer],np.int32)
bvh=BVHTree.FromPolygons(cp.tolist(),tri.tolist(),all_triangles=True)
sourcekeys={}
for key in coat.data.shape_keys.key_blocks:
    ar=np.empty_like(cp);key.data.foreach_get('co',ar.ravel());sourcekeys[key.name]=ar
groups=[g.name for g in coat.vertex_groups]
rows=[{g.group:g.weight for g in v.groups} for v in coat.data.vertices]

def reference(hit):
    if hit[0] is None:raise RuntimeError('Tailoring ray did not reach coat')
    ids=tri[hit[2]]
    bc=barycentric_transform(hit[0],*(Vector(cp[i]) for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    weights=np.maximum(np.array(bc),0);weights/=weights.sum()
    return (ids,weights)
def front(x,z,depth=0.):
    hit=bvh.ray_cast(Vector((x,-.65,z)),Vector((0,1,0)),1.3)
    if hit[0] is None:raise RuntimeError('Coat front missing at x=%f z=%f'%(x,z))
    return (np.array(hit[0],np.float32)+np.array((0,-depth,0)),reference(hit))
def nearest(p):return reference(bvh.find_nearest(Vector(p)))
def frame(ar,ids):
    e=ar[ids[:,1]]-ar[ids[:,0]];e/=np.maximum(np.linalg.norm(e,axis=1,keepdims=True),1e-8)
    n=np.cross(e,ar[ids[:,2]]-ar[ids[:,0]]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8)
    return e,np.cross(n,e),n

created=[]
def bound_mesh(name,verts,faces,refs,mat,uvs=None):
    points=np.asarray(verts,np.float32)
    me=bpy.data.meshes.new(name);me.from_pydata(points.tolist(),[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    ob.parent=coat.parent;ob.matrix_parent_inverse=coat.matrix_parent_inverse.copy();ob.matrix_basis=coat.matrix_basis.copy()
    dress(ob,mat)
    for n in groups:ob.vertex_groups.new(name=n)
    ids=np.asarray([r[0] for r in refs]);weights=np.asarray([r[1] for r in refs])
    for i,(indices,abc) in enumerate(zip(ids,weights)):
        row={}
        for index,w in zip(indices,abc):
            for g,amount in rows[index].items():row[g]=row.get(g,0)+w*amount
        total=sum(row.values())
        for g,w in row.items():
            if w>1e-7:ob.vertex_groups[g].add([i],float(w/total),'REPLACE')
    e,t,n=frame(cp,ids);offset=points-np.sum(cp[ids]*weights[:,:,None],axis=1)
    local=np.stack(((offset*e).sum(1),(offset*t).sum(1),(offset*n).sum(1)),axis=1)
    for key,ar in sourcekeys.items():
        sk=ob.shape_key_add(name=key)
        if key=='Basis':out=points
        else:
            ke,kt,kn=frame(ar,ids)
            out=np.sum(ar[ids]*weights[:,:,None],axis=1)+ke*local[:,0,None]+kt*local[:,1,None]+kn*local[:,2,None]
        sk.data.foreach_set('co',np.asarray(out,np.float32).ravel());sk.value=0
    uv=me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            i=me.loops[li].vertex_index;p=points[i]
            uv.data[li].uv=uvs[i] if uvs is not None else (p[0]/.2,p[2]/.2)
    mod=ob.modifiers.new('PreservedResearcherSkin','ARMATURE');mod.object=rig
    ob['surface_binding']='Fixed source triangle and barycentric weights; transported offsets for all FR morphs'
    created.append(ob);return ob

def sheet(name,nx,nz,fn,mat,thickness=.002):
    anchors=[fn(i/nx,j/nz) for j in range(nz+1) for i in range(nx+1)]
    p=np.array([a[0] for a in anchors]);refs=[a[1] for a in anchors]
    faces=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(nz) for i in range(nx)]
    normal=np.zeros_like(p)
    for f in faces:
        v=np.cross(p[f[1]]-p[f[0]],p[f[3]]-p[f[0]])
        for i in f:normal[i]+=v
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8)
    # Orient using the actual coat's outward radial direction, including the shoulder.
    center=p.mean(0);desired=np.array((center[0],center[1]-.017,max(0,center[2]-1.48)))
    if np.dot(normal.mean(0),desired)<0:normal*=-1;faces=[tuple(reversed(f)) for f in faces]
    count=len(p);vertices=np.vstack((p,p-normal*thickness));allfaces=faces+[tuple(i+count for i in reversed(f)) for f in faces]
    edge=[i for i in range(nx+1)]+[j*(nx+1)+nx for j in range(1,nz+1)]+[nz*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(nz-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):allfaces.append((b,a,a+count,b+count))
    # Metre-based cloth pattern coordinates follow the actual sheet in both
    # directions. A front projection collapses UVs over shoulders and belt sides.
    lattice=p.reshape(nz+1,nx+1,3)
    along=np.zeros((nz+1,nx+1),np.float32);across=along.copy()
    along[:,1:]=np.cumsum(np.linalg.norm(np.diff(lattice,axis=1),axis=2),axis=1)
    across[1:,:]=np.cumsum(np.linalg.norm(np.diff(lattice,axis=0),axis=2),axis=0)
    coordinates=np.stack((along,across),axis=2).reshape(-1,2)/.2
    bound_mesh(name,vertices,allfaces,refs+refs,mat,np.vstack((coordinates,coordinates)))
    return anchors,edge

def tube_geometry(path,radius,sides=6):
    verts=[];refs=[];faces=[]
    for i,(p,ref) in enumerate(path):
        tangent=path[min(i+1,len(path)-1)][0]-path[max(0,i-1)][0]
        tangent=tangent/max(np.linalg.norm(tangent),1e-8)
        a=np.cross(tangent,np.array((0,1,0)))
        if np.linalg.norm(a)<.1:a=np.cross(tangent,np.array((1,0,0)))
        a/=np.linalg.norm(a);b=np.cross(tangent,a)
        for k in range(sides):
            angle=2*math.pi*k/sides;verts.append(p+radius*(a*math.cos(angle)+b*math.sin(angle)));refs.append(ref)
    for i in range(len(path)-1):
        for k in range(sides):faces.append((i*sides+k,i*sides+(k+1)%sides,(i+1)*sides+(k+1)%sides,(i+1)*sides+k))
    faces.extend([tuple(reversed(range(sides))),tuple((len(path)-1)*sides+k for k in range(sides))])
    return verts,faces,refs
def tubing(name,path,radius,mat,sides=6):
    v,f,r=tube_geometry(path,radius,sides);return bound_mesh(name,v,f,r,mat)
def seam(name,path):
    # Raised folded leather edge and short individually curved stitch segments.
    tubing(name+'_Fold',path,.00165,mats['Apron'])
    verts=[];faces=[];refs=[];travel=0.;next_stitch=.003
    for (a,ra),(b,rb) in zip(path,path[1:]):
        length=float(np.linalg.norm(b-a))
        if length<1e-7:continue
        while next_stitch+ .0035<travel+length:
            t=(next_stitch-travel)/length
            if t>=0:
                start=a+(b-a)*t+np.array((0,-.0018,0));end=start+(b-a)/length*.0035
                middle=(start+end)*.5+np.array((0,-.00045,0));r=ra if t<.5 else rb
                vv,ff,rr=tube_geometry([(start,r),(middle,r),(end,r)],.0004,4);n=len(verts)
                verts.extend(vv);refs.extend(rr);faces.extend(tuple(i+n for i in f) for f in ff)
            next_stitch+=.008
        travel+=length
    if verts:bound_mesh(name+'_Stitches',verts,faces,refs,mats['Binding'])

def apron_point(u,v):
    # The source coat has a real front stride vent up to the waist. Keep a
    # rounded, continuous apron vent above it instead of bridging opposite legs.
    a=abs(2*u-1);bottom=.805+.027*a**8+.275*math.exp(-(a/.24)**6)
    z=bottom+(1.435-bottom)*v
    width=float(np.interp(z,[.80,1.06,1.14,1.30,1.435],[.195,.175,.151,.127,.112]))
    x=(2*u-1)*width
    folds=.0027*math.sin(2*math.pi*u*4+.4)*math.sin(math.pi*v)**2
    depth=.012+.008*math.sin(math.pi*u)*math.sin(math.pi*v)+folds
    return front(x,z,depth)
ap,edge=sheet('GardenerV02_TailoredApron',40,60,apron_point,mats['Apron'],.0024)
seam('GardenerV02_ApronHem',[ap[i] for i in edge]+[ap[edge[0]]])

def pocket(name,cx,zlo,zhi,width):
    def fn(u,v):
        x=cx+(u-.5)*width;z=zlo+(zhi-zlo)*v+.009*abs(2*u-1)**8*(1-v)
        # Seated lower/side gussets, an open lip, and a separate rounded bag front.
        fullness=.022*math.sin(math.pi*u)**.7*math.sin(math.pi*(.18+.72*v))
        return front(x,z,.021+fullness)
    points,edge=sheet(name,18,20,fn,mats['Apron'],.002)
    gusset_ids=[j*19 for j in range(20,-1,-1)]+list(range(1,19))+[j*19+18 for j in range(1,21)]
    def gusset(u,v):
        t=u*(len(gusset_ids)-1);i=min(int(t),len(gusset_ids)-2);f=t-i
        p=points[gusset_ids[i]][0]*(1-f)+points[gusset_ids[i+1]][0]*f
        back,ref=front(float(p[0]),float(p[2]),.018)
        return back*(1-v)+p*v,ref
    sheet(name+'_SewnGusset',len(gusset_ids)-1,3,gusset,mats['Apron'],.0015)
    seam(name+'_Seam',[points[i] for i in edge]+[points[edge[0]]])
    top=[points[20*19+i] for i in range(19)]
    tubing(name+'_RolledOpening',top,.0028,mats['Binding'])
    return points
pocket('GardenerV02_LeftBellowsPocket',-.103,.91,1.077,.146)
pocket('GardenerV02_RightBellowsPocket',.103,.91,1.077,.146)
pocket('GardenerV02_BibToolPocket',0,1.265,1.36,.165)
# Sewn divider leaves a narrower channel for tools in the bib pocket.
line=[front(.036,1.272+i*.080/16,.045) for i in range(17)]
tubing('GardenerV02_ToolPocketDivider',line,.0012,mats['Binding'])

for sign in (-1,1):
    def strap(u,v,sign=sign):
        x=sign*.113+(u-.5)*.032
        if v<.68:
            theta=math.pi*v/.68
            direction=Vector((0,math.cos(theta),-math.sin(theta)))
            origin=Vector((x,.017-2*math.cos(theta),1.405+2*math.sin(theta)))
            hit=bvh.ray_cast(origin,direction,4.)
            p=np.array(hit[0])+np.array(direction)*-.010
        else:
            z=1.405-(v-.68)/.32*.29
            hit=bvh.ray_cast(Vector((x,.65,z)),Vector((0,-1,0)),1.3)
            p=np.array(hit[0])+np.array((0,.010,0))
        return p,reference(hit)
    points,edge=sheet('GardenerV02_ShoulderWebbing_'+str(sign),6,64,strap,mats['Binding'],.003)
    # Both boundaries are explicitly sampled continuous curves, never cut-face masks.
    for side in (0,6):
        path=[points[j*7+side] for j in range(65)]
        tubing('GardenerV02_StrapPiping_'+str((sign,side)),path,.0009,mats['Apron'])
    cx=sign*.113;z=1.423;w=.038;h=.026;r=.006
    path=[]
    for xx,zz,start in ((cx+w/2-r,z+h/2-r,0),(cx-w/2+r,z+h/2-r,90),(cx-w/2+r,z-h/2+r,180),(cx+w/2-r,z-h/2+r,270)):
        for a in np.linspace(start,start+90,7):
            angle=math.radians(float(a));path.append(front(xx+r*math.cos(angle),zz+r*math.sin(angle),.020))
    path.append(path[0]);tubing('GardenerV02_Adjuster_'+str(sign),path,.0023,mats['Hardware'],8)
    tubing('GardenerV02_AdjusterBar_'+str(sign),[front(cx-w*.36,z,.022),front(cx+w*.36,z,.022)],.0019,mats['Hardware'],8)

def belt(u,v):
    angle=2*math.pi*u;direction=Vector((math.sin(angle),-math.cos(angle),0));z=1.107+(v-.5)*.034
    hit=bvh.ray_cast(Vector((0,.017,z)),direction,.45)
    p=np.array(hit[0])+np.array(direction)*(.028 if math.cos(angle)>.25 else .009)
    return p,reference(hit)
sheet('GardenerV02_ContinuousWaistBelt',96,5,belt,mats['Binding'],.003)
# The upper shirt closure remains visible above the bib.
sheet('GardenerV02_ShirtPlacket',6,16,lambda u,v:front((u-.5)*.022,1.44+v*.078,.004),mats['Workwear'],.0015)

# Dirt is bounded to contact areas; no broad brown gradient over every garment.
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body]
for o in objects:
    if o.data.shape_keys:
        for key in o.data.shape_keys.key_blocks:key.value=0
    if o==display:continue
    attr=o.data.color_attributes.get('GardenerWear') or o.data.color_attributes.new(name='GardenerWear',type='FLOAT_COLOR',domain='CORNER')
    colors=np.ones((len(o.data.loops),4),np.float32)
    for lp in o.data.loops:
        p=o.data.vertices[lp.vertex_index].co
        flecks=max(0.,math.sin(p.x*163+p.z*181)*math.sin(p.y*147-p.z*93))**3
        contact=max(0.,1-p.z/.32)*.45
        hem=max(0.,1-abs(p.z-.82)/.065)*.18
        soil=min(.38,(contact+hem)*(.2+.8*flecks))
        if 'Adjuster' in o.name:soil=0
        colors[lp.index]=[soil,soil,soil,1]
    attr.data.foreach_set('color',colors.ravel());o.data.color_attributes.active_color=attr
    o.data.color_attributes.render_color_index=list(o.data.color_attributes).index(attr)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/EcologyGardener_V02.blend'))
keynames=sorted(k for k in sourcekeys if k!='Basis');copies=[]
for o in objects:
    copy=o.copy();copy.data=o.data.copy();bpy.context.collection.objects.link(copy);copy.hide_set(False);copies.append(copy)
bpy.ops.object.select_all(action='DESELECT');active=copies[0]
if not active.data.shape_keys:active.shape_key_add(name='Basis')
for name in keynames:
    if name not in active.data.shape_keys.key_blocks:active.shape_key_add(name=name)
for o in copies:o.select_set(True)
bpy.context.view_layer.objects.active=active;bpy.ops.object.join();merged=bpy.context.object;merged.name='SK_EcologyGardener_V02'
bpy.ops.object.select_all(action='DESELECT');merged.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery/SK_EcologyGardener_V02.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,use_armature_deform_only=False,mesh_smooth_type='FACE',use_mesh_modifiers=False)
report={'source':str(SOURCE),'mesh':'SK_EcologyGardener_V02','file':'Delivery/SK_EcologyGardener_V02.fbx',
    'material_families':list(mats),'material_slots':[m.name for m in merged.data.materials],
    'triangles':sum(len(p.vertices)-2 for p in merged.data.polygons),'bones':len(rig.data.bones)+1,
    'corrective_morphs':keynames,'morph_count':len(keynames),'new_layer_objects':[o.name for o in created],
    'production':'Continuous apron and shoulder patterns; 12-20mm stand-off, 2.4mm leather shell, bellows pockets, folded rims, stitches, metal adjusters; fixed barycentric binding of all 231 FR morphs',
    'runtime_tested':False,'rendered':False}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('GARDENER_V02_AUTHORED '+json.dumps({k:report[k] for k in ('mesh','triangles','morph_count','material_slots')}),flush=True)
