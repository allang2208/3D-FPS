"""Closed double-sided scalloped dragon relief, pierced clouds, exact TangDao seats."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
NAME='SM_TangDao_Guard_xuan_cloud_dragon';MAT='M_TangDaoXuanCloudGuard'
UE='/Game/Weapons/TangDao20261002/XuanCloudGuard20261002'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
src=np.load(P/'Ornament/guard_geometry.npz');h,mask=src['height'],src['mask']
ny,nx=h.shape;W=.144;H=.164
verts=[];faces=[];uvfaces=[];smooth=[]

def add(v,fs,uvs,sm=True):
    offset=len(verts);verts.extend(v)
    for f,uv in zip(fs,uvs):faces.append([offset+i for i in f]);uvfaces.append(uv);smooth.append(sm)

# Remove the material outside the outline or inside the cloud perforations.
# Each exposed grid edge receives a front-to-back wall: no one-sided shells.
cell=mask[:-1,:-1]&mask[1:,:-1]&mask[:-1,1:]&mask[1:,1:]
# Avoid a single vertex connecting two diagonal islands at a pierced outline.
for _ in range(3):
    a,b,c,d=cell[:-1,:-1],cell[:-1,1:],cell[1:,:-1],cell[1:,1:]
    pinch=(a&d&~b&~c)|(b&c&~a&~d)
    jj,ii=np.where(pinch)
    for j,i in zip(jj,ii):
        if cell[j,i]:cell[j,i]=False
        else:cell[j,i+1]=False
used=np.zeros_like(mask)
for dy,dx in [(0,0),(1,0),(0,1),(1,1)]:used[dy:dy+ny-1,dx:dx+nx-1]|=cell
index=np.full(mask.shape,-1,dtype=np.int32)
for j,i in zip(*np.where(used)):
    index[j,i]=len(verts);verts.append((-W/2+W*i/(nx-1),H/2-H*j/(ny-1),.0035+float(h[j,i])))
front_count=len(verts)
for j,i in zip(*np.where(used)):
    verts.append((-W/2+W*i/(nx-1),H/2-H*j/(ny-1),-.0045-.82*float(h[j,i])))

def face(indices,uvs,sm=True):faces.append(indices);uvfaces.append(uvs);smooth.append(sm)
def art_uv(j,i):return (.02+.76*i/(nx-1),.02+.96*(1-j/(ny-1)))

border={}
for j,i in zip(*np.where(cell)):
    pts=[(j,i),(j+1,i),(j+1,i+1),(j,i+1)]
    inds=[int(index[a,b]) for a,b in pts];uv=[art_uv(a,b) for a,b in pts]
    face(inds,uv);face([v+front_count for v in reversed(inds)],list(reversed(uv)))
    for k,(dj,di) in enumerate([(0,-1),(1,0),(0,1),(-1,0)]):
        nj,ni=j+dj,i+di
        if 0<=nj<ny-1 and 0<=ni<nx-1 and cell[nj,ni]:continue
        a,b=inds[k],inds[(k+1)%4]
        border.setdefault(a,set()).add(b);border.setdefault(b,set()).add(a)
        # Gilded sidewall strip, with coherent local grain rather than face color.
        face([b,a,a+front_count,b+front_count],[(.795,.3),(.802,.3),(.802,.6),(.795,.6)])

# Smooth the sub-millimetre grid quantisation of the scallops and cloud holes.
# Preserve the 3D relief; reproject UVs so the engraved rim follows the mesh.
for _ in range(8):
    updated={}
    for a,adj in border.items():
        if len(adj)!=2:continue
        b,c=adj
        updated[a]=[.60*verts[a][k]+.20*(verts[b][k]+verts[c][k]) for k in (0,1)]
    for a,(x,y) in updated.items():
        verts[a]=(x,y,verts[a][2]-.00003)
        verts[a+front_count]=(x,y,verts[a+front_count][2]+.00003)
for f,uvs in zip(faces,uvfaces):
    if all(v<front_count for v in f) or all(v>=front_count for v in f):
        for k,v in enumerate(f):
            x,y,_=verts[v];uvs[k]=(.02+.76*(x/W+.5),.02+.96*(y/H+.5))

interface=json.loads((P.parent/'interfaces.json').read_text(encoding='utf-8'))['parts']['guard']

def seat_loop(raw):
    pts=[tuple(v) for v in raw]
    area=sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
    if area<0:pts.reverse()
    return pts

def collar(raw,levels,center):
    points=seat_loop(raw);n=len(points);v=[]
    # All Z rings keep the recorded mount outline; no global-bounds resizing.
    for z,scale in levels:
        for i,(x,y,_) in enumerate(points):
            a=math.atan2(y-center[1],x-center[0])
            carving=.00014*math.sin(8*a+1.8*math.sin((z+.05)/.064*10*math.pi))
            carving*=math.sin(math.pi*(z-levels[0][0])/(levels[-1][0]-levels[0][0]))**2
            r=max(math.hypot(x-center[0],y-center[1]),.001)
            s=scale+carving/r
            v.append((center[0]+(x-center[0])*s,center[1]+(y-center[1])*s,z))
    fs=[];uv=[]
    for j in range(len(levels)-1):
        for i in range(n):
            k=(i+1)%n;f=[j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i];fs.append(f)
            uv.append([(.81+.18*(i/n),max(.015,min(.985,(v[idx][2]+.05)/.064))) if idx%n==i else (.81+.18*((i+1)/n),max(.015,min(.985,(v[idx][2]+.05)/.064))) for idx in f])
    # Closed caps, concealed by the blade and grip ends in the assembly.
    fs.extend([list(range(n-1,-1,-1)),[(len(levels)-1)*n+i for i in range(n)]])
    uv.extend([[(.797,.4)]*n,[(.797,.4)]*n]);add(v,fs,uv)

blade,grip=interface['cut_boundary_loops_local_m']
# Front ferrule bridges exactly into z=14mm. Double rolled edges are solid.
collar(blade,[(.002,1.08),(.004,1.08),(.005,1.15),(.0062,1.15),(.0066,1.05),
              (.0108,1.05),(.0112,1.13),(.0126,1.13),(.013,1.00),(.014,1.00)],(.00158,-.00005))
# The rear collar and slip-stop ring taper into the original -50mm grip seat.
levels=[(-.050,1.),(-.0488,1.),(-.048,1.10),(-.046,1.10),(-.0454,1.03)]
levels += [(z,1.03) for z in np.linspace(-.044,-.030,18)]
levels += [(-.0295,1.14),(-.0273,1.14),(-.0268,1.055)]
levels += [(z,1.055) for z in np.linspace(-.026,-.015,16)]
levels += [(-.0145,1.18),(-.0120,1.18),(-.0115,1.08),(-.004,1.08)]
collar(grip,levels,(.00132,.00011))

mesh=bpy.data.meshes.new(NAME);mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for poly,coords in zip(mesh.polygons,uvfaces):
    poly.use_smooth=smooth[poly.index]
    for loop,co in zip(poly.loop_indices,coords):uv.data[loop].uv=co
bm=bmesh.new();bm.from_mesh(mesh)
# Resolve touching diagonal mask corners into separate solid outlines. Grid
# samples are already shared; do not weld across the intentionally open holes.
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for e in bm.edges:
    if e.is_manifold and e.calc_face_angle()>.65:e.smooth=False
bm.to_mesh(mesh);bm.free();mesh.update()
mat=bpy.data.materials.new(MAT);mat.use_nodes=True
nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
for key in ['BaseColor','ORM','Normal']:
    im=bpy.data.images.load(str(P/'Textures'/('TangDao_XuanCloudGuard_'+key+'.png')))
    im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
    node=nt.nodes.new('ShaderNodeTexImage');node.image=im
    if key=='BaseColor':nt.links.new(node.outputs['Color'],bs.inputs['Base Color'])
    elif key=='ORM':
        sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(node.outputs[0],sep.inputs[0])
        nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    else:
        nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(node.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
mesh.materials.append(mat)
obj=bpy.data.objects.new(NAME+'_LOD0',mesh);bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
# Hard junction normals prevent shading from rounding the thick center collars.
mod=obj.modifiers.new('Manufactured collar normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
bpy.ops.object.modifier_apply(modifier=mod.name)
group=bpy.data.objects.new(NAME+'_LODGroup',None);group['fbx_type']='LodGroup';bpy.context.scene.collection.objects.link(group);obj.parent=group
lods=[obj]
for level,ratio in [(1,.53),(2,.23)]:
    lod=obj.copy();lod.data=obj.data.copy();lod.name=NAME+'_LOD'+str(level);bpy.context.scene.collection.objects.link(lod)
    bpy.context.view_layer.objects.active=lod
    mod=lod.modifiers.new('Distance relief LOD','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name);lods.append(lod)
bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
for lod in lods:lod.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(NAME+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/(NAME+'.glb')),use_selection=True,export_format='GLB')
for lod in lods[1:]:lod.hide_set(True);lod.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'TangDao_XuanCloudGuard_Editable.blend'))
counts=[]
for lod in lods:lod.data.calc_loop_triangles();counts.append(len(lod.data.loop_triangles))
m={'id':'xuan_cloud_dragon','name':'璇云龙璧护手','weapon':'ue_tang_dao','slot':'guard','interface':'tang_dao_hilt_v1',
 'ue_root':UE,'mesh_name':NAME,'mesh':UE+'/Meshes/'+NAME+'.'+NAME,'materials':{MAT:UE+'/Materials/'+MAT+'.'+MAT},
 'location_cm':[0,0,0],'rotation_deg':[0,0,0],'scale':[1,1,1],'lod_triangles':counts,
 'plate_width_cm':W*100,'plate_height_cm':H*100,'core_thickness_mm':8.,'relief_height_mm':2.5,
 'front_blade_seat_z_cm':1.4,'rear_grip_seat_z_cm':-5.,'texture_resolution':4096,
 'features':['四瓣璇云层叠外廓','双面实体龙云浮雕','云纹贯通镂空及封闭内壁','鎏金凸纹与暗铜凹底','龙鳞蚀刻','承力芯与雕纹止滑环'],
 'stats':{},'runtime_tested':False}
(P/'guard_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('XUAN_CLOUD_GUARD_AUTHORED '+json.dumps({'lod_triangles':counts,'mesh':m['mesh']}),flush=True)
