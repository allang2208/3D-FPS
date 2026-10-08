"""Retained factory center plus closed curved cast wings with double-sided relief."""
from pathlib import Path
import bpy,bmesh,json,math
import numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent
NAME='SM_XuanChi_Guard_PanChiZhanYue_V1';MAT='M_XuanChi_PanChiWing_V1'
UE='/Game/Weapons/XuanChiZhenYue20261004/PanChiGuard20261006'
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'BladeV3/XuanChi_BladeV3_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
factory=bpy.data.objects['SM_XuanChi_Guard_V3'];src=factory.data;src.calc_loop_triangles()
original_normals=[Vector(n.vector) for n in src.corner_normals]
verts=[];faces=[];uvs=[];normals=[];materials=[]
# Clip only the replaced outer wings. Preserve the complete central jade, blade
# collar, grip seat, face-corner UVs and custom normals at their authored positions.
for tri in src.loop_triangles:
    poly=[(src.vertices[src.loops[li].vertex_index].co.copy(),src.uv_layers[0].data[li].uv.copy(),original_normals[li]) for li in tri.loops]
    for side in (-1,1):
        clipped=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=.064-side*a[0].x;db=.064-side*b[0].x
            if da>=0:clipped.append(a)
            if (da>=0)!=(db>=0):
                t=da/(da-db);clipped.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized()))
        poly=clipped
    for k in range(1,len(poly)-1):
        corners=[poly[0],poly[k],poly[k+1]]
        if (corners[1][0]-corners[0][0]).cross(corners[2][0]-corners[0][0]).length<1e-12:continue
        faces.append(tuple(range(len(verts),len(verts)+3)));materials.append(tri.material_index)
        for co,uv,no in corners:verts.append(co);uvs.append(uv);normals.append(no)
mesh=bpy.data.meshes.new(NAME+'_FactoryCenter');mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='UVMap');attr=mesh.attributes.new('PanChiRetainedNormal','FLOAT_VECTOR','CORNER')
for f,mi in zip(mesh.polygons,materials):
    f.use_smooth=True;f.material_index=mi
    for li in f.loop_indices:
        vi=mesh.loops[li].vertex_index;uv.data[li].uv=uvs[vi];attr.data[li].vector=normals[vi]
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000003)
edges=[e for e in bm.edges if e.is_boundary and all(abs(abs(v.co.x)-.064)<.000001 for v in e.verts)]
caps=bmesh.ops.holes_fill(bm,edges=edges,sides=0).get('faces',[])
normal_layer=bm.loops.layers.float_vector['PanChiRetainedNormal'];uv_layer=bm.loops.layers.uv[0]
for f in caps:
    f.normal_update();f.material_index=0
    for l in f.loops:l[normal_layer]=f.normal;l[uv_layer].uv=(.025+l.vert.co.y,.025+l.vert.co.z)
bm.to_mesh(mesh);bm.free();mesh.update()
mesh.normals_split_custom_set([tuple(n.vector) for n in mesh.attributes['PanChiRetainedNormal'].data])
for m in src.materials:mesh.materials.append(m)
center=bpy.data.objects.new(NAME,mesh);scene.collection.objects.link(center)
# Packed author files predate the accepted silver/copper finish: explicitly use
# current external production maps, never revive their old packed colors.
for m in mesh.materials:
    for n in m.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image:
            filename=Path(n.image.filepath).name
            folder=P.parent/('BladeV3/Textures' if 'Blade_' in filename else 'SurfaceV2/Textures')
            path=folder/filename
            if path.exists():
                n.image=bpy.data.images.load(str(path),check_existing=False)
                n.image.colorspace_settings.name='sRGB' if 'BaseColor' in filename else 'Non-Color'

mat=bpy.data.materials.new(MAT);mat.use_nodes=True;nt=mat.node_tree
bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
for key in ['BaseColor','ORM','Normal']:
    tx=nt.nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(P/'Textures'/('PanChi_'+key+'.png')))
    tx.image.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
    if key=='BaseColor':nt.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
    elif key=='ORM':
        sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tx.outputs[0],sep.inputs[0])
        nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    else:
        nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tx.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])

data=np.load(P/'Ornament/wing_geometry.npz');h,mask,dist=data['height'],data['mask'],data['distance']
ny,nx=h.shape;W,H=.148,.057
cell=mask[:-1,:-1]&mask[1:,:-1]&mask[:-1,1:]&mask[1:,1:]
for _ in range(3):
    a,b,c,d=cell[:-1,:-1],cell[:-1,1:],cell[1:,:-1],cell[1:,1:]
    for j,i in zip(*np.where((a&d&~b&~c)|(b&c&~a&~d))):
        if cell[j,i]:cell[j,i]=False
        else:cell[j,i+1]=False
used=np.zeros_like(mask)
for dy,dx in [(0,0),(1,0),(0,1),(1,1)]:used[dy:dy+ny-1,dx:dx+nx-1]|=cell
index=np.full(mask.shape,-1,dtype=np.int32);points=[];uvpoints=[]
for j,i in zip(*np.where(used)):
    u=i/(nx-1);v=j/(ny-1);index[j,i]=len(points)
    x=.052+W*u;z=.023-H*v
    # The visible central cut has a taller section than the art's blunt root.
    # Grow only the buried shoulder, then smoothly return to the approved wing.
    root_t=min(1.,u/.22);shoulder=1.-root_t*root_t*(3.-2.*root_t)
    z=-.006+(z+.006)*(1.+.80*shoulder)
    # Tapering elliptical cast body rather than a flat plate extruded backward.
    edge=min(1.,float(dist[j,i])/.0022);rounding=.48+.52*math.sqrt(edge)
    half=(.0055+.0090*(1.-u)**2+.0025*math.sin(math.pi*u))*rounding*(1.+.12*shoulder)
    relief=float(h[j,i])*(.60+.40*min(1.,u/.12))
    points.append((x,-half-relief,z));uvpoints.append((40/2048+(1884-40)/2048*u,40/1024+(984-40)/1024*(1-v)))
count=len(points)
points += [(x,-y*.93,z) for x,y,z in points[:]]
fcs=[];fuv=[];border={}
def face(indices,uv):fcs.append(indices);fuv.append(uv)
for j,i in zip(*np.where(cell)):
    ijs=[(j,i),(j+1,i),(j+1,i+1),(j,i+1)];ids=[int(index[a,b]) for a,b in ijs]
    uv=[uvpoints[n] for n in ids];face(ids,uv);face([n+count for n in ids[::-1]],uv[::-1])
    for k,(dj,di) in enumerate([(0,-1),(1,0),(0,1),(-1,0)]):
        nj,ni=j+dj,i+di
        if 0<=nj<ny-1 and 0<=ni<nx-1 and cell[nj,ni]:continue
        a,b=ids[k],ids[(k+1)%4];border.setdefault(a,set()).add(b);border.setdefault(b,set()).add(a)
        face([b,a,a+count,b+count],[(.956,.2),(.966,.2),(.966,.8),(.956,.8)])
# Round the submillimetre staircase of the sampled outline/holes only.
for _ in range(5):
    updated={a:np.array(points[a])*.6+sum((np.array(points[b]) for b in adj),np.zeros(3))*.2 for a,adj in border.items() if len(adj)==2}
    for a,p in updated.items():
        points[a]=(p[0],points[a][1],p[2]);points[a+count]=(p[0],points[a+count][1],p[2])
wingmesh=bpy.data.meshes.new('PanChi_CurvedDoubleRelief');wingmesh.from_pydata(points,[],fcs);wingmesh.update()
uv=wingmesh.uv_layers.new(name='UVMap')
for f,coords in zip(wingmesh.polygons,fuv):
    f.use_smooth=True
    for li,c in zip(f.loop_indices,coords):uv.data[li].uv=c
wingmesh.materials.append(mat)
bm=bmesh.new();bm.from_mesh(wingmesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(wingmesh);bm.free()
wings=[]
for side in (1,-1):
    wing=bpy.data.objects.new('PanChi_RightWing' if side==1 else 'PanChi_LeftWing',wingmesh.copy());scene.collection.objects.link(wing)
    if side<0:
        for v in wing.data.vertices:v.co.x=-v.co.x
        bm=bmesh.new();bm.from_mesh(wing.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(wing.data);bm.free()
    wing.data.update();wings.append(wing)

bpy.ops.object.select_all(action='DESELECT')
for o in [center]+wings:o.select_set(True);o.hide_set(False)
bpy.context.view_layer.objects.active=center;bpy.ops.object.join();center.name=NAME+'_LOD0'
center['preserved_factory_interface']='xuanchi_hilt_v1; original center |X| <= 6.4 cm'
group=bpy.data.objects.new(NAME+'_LODGroup',None);group['fbx_type']='LodGroup';scene.collection.objects.link(group);center.parent=group
lods=[center]
for level,ratio in [(1,.55),(2,.25)]:
    lod=center.copy();lod.data=center.data.copy();lod.name=NAME+'_LOD'+str(level);scene.collection.objects.link(lod)
    bpy.context.view_layer.objects.active=lod
    mod=lod.modifiers.new('Distant ornament relief','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name);lods.append(lod)
bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
for o in lods:o.select_set(True)
bpy.context.view_layer.objects.active=center
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(NAME+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.object.select_all(action='DESELECT');center.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/(NAME+'.glb')),use_selection=True,export_format='GLB')
for o in scene.objects:
    if o.type=='MESH':o.hide_render=o!=center
for lod in lods[1:]:lod.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'PanChi_Guard_Editable.blend'))
counts=[]
for o in lods:o.data.calc_loop_triangles();counts.append(len(o.data.loop_triangles))
manifest={'id':'panchi_zhanyue','name':'蟠螭展岳','weapon':'ue_xuanchi_zhenyue','slot':'guard','tier':'special','stats':{},
    'interface':'xuanchi_hilt_v1','ue_root':UE,'mesh_name':NAME,'mesh':UE+'/Meshes/'+NAME+'.'+NAME,
    'materials':{MAT:UE+'/Materials/'+MAT+'.'+MAT},'location_cm':[0,0,0],'rotation_deg':[0,0,0],'scale':[1,1,1],
    'lod_triangles':counts,'design_span_cm':40,'max_relief_mm':3.2,'texture_size':[2048,1024],
    'center_source':'../BladeV3/XuanChi_BladeV3_Editable.blend:SM_XuanChi_Guard_V3',
    'retained_center_half_width_cm':6.4,'process':'Blender retained native center, curved closed mirrored casting and commissioned sculpt-height relief',
    'source_art':'Ornament/Wing_HeightSource.png','runtime_tested':False,'acceptance_render_run':False}
(P/'guard_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PANCHI_GUARD_EXPORTED '+json.dumps({'lod_triangles':counts,'mesh':manifest['mesh']}),flush=True)
