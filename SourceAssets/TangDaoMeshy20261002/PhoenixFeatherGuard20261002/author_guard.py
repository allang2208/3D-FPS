"""Closed double-sided phoenix feather relief and garnet insets, using exact TangDao seats."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
NAME='SM_TangDao_Guard_phoenix_feather';MAT='M_TangDaoPhoenixFeatherGuard_Gilt';GEM_MAT='M_TangDaoPhoenixFeatherGuard_Garnet'
UE='/Game/Weapons/TangDao20261002/PhoenixFeatherGuard20261002'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
src=np.load(P/'Ornament/guard_geometry.npz');h,mask=src['height'],src['mask']
ny,nx=h.shape;W=.134;H=.178;ART_OFFSET_X=.020
verts=[];faces=[];uvfaces=[];smooth=[];material_indices=[]

def add(v,fs,uvs,sm=True,material=0):
    offset=len(verts);verts.extend(v)
    for f,uv in zip(fs,uvs):faces.append([offset+i for i in f]);uvfaces.append(uv);smooth.append(sm);material_indices.append(material)

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
    index[j,i]=len(verts);verts.append((-W/2+ART_OFFSET_X+W*i/(nx-1),H/2-H*j/(ny-1),.0035+float(h[j,i])))
front_count=len(verts)
for j,i in zip(*np.where(used)):
    verts.append((-W/2+ART_OFFSET_X+W*i/(nx-1),H/2-H*j/(ny-1),-.0045-.82*float(h[j,i])))

def face(indices,uvs,sm=True):faces.append(indices);uvfaces.append(uvs);smooth.append(sm);material_indices.append(0)
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
            x,y,_=verts[v];uvs[k]=(.02+.76*((x-ART_OFFSET_X)/W+.5),.02+.96*(y/H+.5))

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
            carving=0.0 # Keep the manufactured collar straight; engraving is a fine normal map.
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
    # Planar UVs for both closed installation caps; constant UVs would create
    # zero-length tangents in the imported metal surfaces.
    xs=[p[0] for p in v];ys=[p[1] for p in v]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
    for cap in fs[-2:]:
        uv.append([(.783+.024*(v[i][0]-xmin)/max(xmax-xmin,1e-6),.24+.52*(v[i][1]-ymin)/max(ymax-ymin,1e-6)) for i in cap])
    add(v,fs,uv)

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

# Closed cabochons on both sides, individually inset into their raised bezels.
gems=json.loads((P/'Ornament/gemstones.json').read_text(encoding='utf-8'))
for g in gems:
    for sign in [1,-1]:
        cx,cy=g['x_m'],g['y_m'];rx,ry=g['radius_x_m'],g['radius_y_m']
        z0=.0070 if sign==1 else -.0076;dome=g['dome_height_m'];segments=64;levels=10
        # Substantial gilded bezel/seat reaches the metal plate and supports
        # the inset stone; the cabochon is not suspended above the relief.
        bezel=[];bf=[];bu=[]
        profile=[(1.18,z0-sign*.0026),(1.22,z0-sign*.00045),(1.13,z0+sign*.00012),(1.01,z0+sign*.00012),(.99,z0-sign*.0006)]
        for r,z in profile:
            for i in range(segments):
                theta=2*math.pi*i/segments
                bezel.append((cx+rx*r*math.cos(theta),cy+ry*r*math.sin(theta),z))
        for j in range(len(profile)-1):
            for i in range(segments):bf.append([j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i])
        bf.extend([list(range(segments-1,-1,-1)),[(len(profile)-1)*segments+i for i in range(segments)]])
        for f in bf:bu.append([(.795+.010*(bezel[i][0]-cx)/rx,.5+.32*(bezel[i][1]-cy)/ry) for i in f])
        add(bezel,bf,bu,sm=True,material=0)
        v=[];uv=[];fs=[]
        for j in range(levels):
            a=(j/levels)*math.pi/2;r=math.cos(a);z=z0+sign*dome*math.sin(a)
            for i in range(segments):
                theta=2*math.pi*i/segments
                v.append((cx+rx*r*math.cos(theta),cy+ry*r*math.sin(theta),z))
        top=len(v);v.append((cx,cy,z0+sign*dome))
        bottom=len(v);v.append((cx,cy,z0-sign*.0008))
        for j in range(levels-1):
            for i in range(segments):fs.append([j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i])
        for i in range(segments):
            fs.append([(levels-1)*segments+i,(levels-1)*segments+(i+1)%segments,top])
            fs.append([(i+1)%segments,i,bottom])
        for f in fs:uv.append([(.5+.49*(v[i][0]-cx)/rx,.5+.49*(v[i][1]-cy)/ry) for i in f])
        add(v,fs,uv,sm=True,material=1)

mesh=bpy.data.meshes.new(NAME);mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for poly,coords in zip(mesh.polygons,uvfaces):
    poly.use_smooth=smooth[poly.index];poly.material_index=material_indices[poly.index]
    for loop,co in zip(poly.loop_indices,coords):uv.data[loop].uv=co
bm=bmesh.new();bm.from_mesh(mesh)
# Resolve touching diagonal mask corners into separate solid outlines. Grid
# samples are already shared; do not weld across the intentionally open holes.
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for e in bm.edges:
    if e.is_manifold and e.calc_face_angle()>.65:e.smooth=False
bm.to_mesh(mesh);bm.free();mesh.update()
for family,name in [('Gilt',MAT),('Garnet',GEM_MAT)]:
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    for key in ['BaseColor','ORM','Normal']:
        im=bpy.data.images.load(str(P/'Textures'/('TangDao_PhoenixFeatherGuard_'+family+'_'+key+'.png')))
        im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
        node=nt.nodes.new('ShaderNodeTexImage');node.image=im
        if key=='BaseColor':nt.links.new(node.outputs[0],bs.inputs['Base Color'])
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
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'TangDao_PhoenixFeatherGuard_Editable.blend'))
counts=[]
for lod in lods:lod.data.calc_loop_triangles();counts.append(len(lod.data.loop_triangles))
m={'id':'phoenix_feather','name':'凤仪华羽护手','weapon':'ue_tang_dao','slot':'guard','interface':'tang_dao_hilt_v1',
 'ue_root':UE,'mesh_name':NAME,'mesh':UE+'/Meshes/'+NAME+'.'+NAME,'materials':{name:UE+'/Materials/'+name+'.'+name for name in [MAT,GEM_MAT]},
 'location_cm':[0,0,0],'rotation_deg':[0,0,0],'scale':[1,1,1],'lod_triangles':counts,
 'plate_width_cm':W*100,'plate_height_cm':H*100,'core_thickness_mm':8.,'relief_height_mm':3.1,
 'front_blade_seat_z_cm':1.4,'rear_grip_seat_z_cm':-5.,'texture_resolution':{'Gilt':4096,'Garnet':512},'art_offset_x_cm':2.0,'gemstones_per_side':len(gems),
 'features':['非对称凤羽层叠外廓','双面凤首与羽脊实体浮雕','羽隙与卷云贯通镂空及实体孔壁','暖鎏金凸纹与暗铜凹底','双面红石独立嵌饰','精确承力芯与雕纹止滑环'],
 'stats':{},'runtime_tested':False}
(P/'guard_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PHOENIX_FEATHER_GUARD_AUTHORED '+json.dumps({'lod_triangles':counts,'mesh':m['mesh']}),flush=True)
