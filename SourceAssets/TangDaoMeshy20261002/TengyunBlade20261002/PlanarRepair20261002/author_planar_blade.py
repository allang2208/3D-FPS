"""Author a straight, planar Tengyun root and a uniform-thickness blade."""
import bpy, json
import numpy as np
from pathlib import Path
from mathutils import Matrix

P = Path(__file__).resolve().parent
T = P.parent
UE = '/Game/Weapons/TangDao20261002/TengyunBlade20261002'
SURFACE_UE = UE+'/JointRepair20261002'
NAME = 'SM_TangDao_Blade_tengyun_dragon'
BASE = .0134  # Seat the clean blade 0.6 mm inside the closed guard collar.
UV_ROOT = .014
HALF_THICKNESS = .0035
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(T.parent/'SurfaceV2/TangDao_SurfaceV2_Editable.blend'))
print('TENGYUN_PLANAR_ROOT_BUILDING', flush=True)

# Monotone shape-preserving slopes prevent a waist/overshoot near the hilt.
profile_z = np.array([BASE,.08,.14,.24,.40,.60,.72,.80,.85,.88])
profile_edge = np.array([-.02525,-.029,-.030,-.028,-.022,-.008,.010,.037,.068,.0948])
profile_spine = np.array([.0284,.031,.032,.037,.047,.064,.080,.089,.093,.0953])

def profile(values, z):
    h = np.diff(profile_z)
    d = np.diff(values)/h
    slopes = np.zeros_like(values)
    for i in range(1, len(values)-1):
        if d[i-1]*d[i] > 0:
            w1, w2 = 2*h[i]+h[i-1], h[i]+2*h[i-1]
            slopes[i] = (w1+w2)/(w1/d[i-1]+w2/d[i])
    for endpoint, step, next_step, slope, next_slope in [
        (0,h[0],h[1],d[0],d[1]),(-1,h[-1],h[-2],d[-1],d[-2])]:
        value = ((2*step+next_step)*slope-step*next_slope)/(step+next_step)
        slopes[endpoint] = 0 if value*slope <= 0 else np.sign(value)*min(abs(value),3*abs(slope))
    i = np.clip(np.searchsorted(profile_z,z)-1,0,len(profile_z)-2)
    step = profile_z[i+1]-profile_z[i]
    q = np.clip((z-profile_z[i])/step,0,1)
    return ((2*q**3-3*q**2+1)*values[i]+(q**3-2*q**2+q)*step*slopes[i]
        +(-2*q**3+3*q**2)*values[i+1]+(q**3-q**2)*step*slopes[i+1])

def smooth(a,b,q):
    t = np.clip((q-a)/(b-a),0,1)
    return t*t*(3-2*t)

ts = np.unique(np.r_[np.linspace(0,1,65),.20,.24,.30,.58,.60,.614,.628,.64,.652,.666,.68,
    .74,.76,.78,.80,.814,.828,.842,.855,.868,.882,.896,.91,.93,.95,.976])
across = np.r_[ts,ts[::-1]]
sides = np.r_[-np.ones(len(ts)),np.ones(len(ts))]
zs = np.unique(np.r_[np.linspace(BASE,.14,55),np.linspace(.14,.878,257),
    .165,.20,.69,.755,.878,.8785,.879,.8795,.88,profile_z])

def points(z):
    z = np.asarray(z).reshape(-1,1)
    lo, hi = profile(profile_edge,z), profile(profile_spine,z)
    x = lo+across[None,:]*(hi-lo)
    # Parallel main faces from the clean root to the tip's final 2 mm bevel.
    # Only the cutting edge, spine chamfer and physical fuller change the section.
    y = np.broadcast_to(np.interp(across,[0,.20,.30,.95,.976,1],
        [.00010,.00260,HALF_THICKNESS,HALF_THICKNESS,.00295,.00245]),x.shape).copy()
    gate = smooth(.165,.20,z)*(1-smooth(.69,.755,z))
    y -= .00070*np.exp(-((across[None,:]-.855)/.041)**4)*gate
    y *= 1-.975*smooth(.878,.88,z)
    # Gilded dragon microrelief stays in the existing normal map. Its geometry
    # no longer bends the broad steel planes or changes the blade's base thickness.
    return np.stack([x,y*sides[None,:],np.broadcast_to(z,x.shape)],axis=-1)

coords = points(zs)
longitudinal = (points(zs+.00001)-points(zs-.00001))/.00002
segments = np.roll(coords,-1,axis=1)-coords
normal = np.cross(segments,.5*(longitudinal+np.roll(longitudinal,-1,axis=1)))
normal /= np.maximum(np.linalg.norm(normal,axis=-1,keepdims=True),1e-15)
count = len(across)
verts = coords.reshape(-1,3).tolist()
u = np.where(sides < 0,.02+.46*across,.98-.46*across)
v = np.clip((zs-UV_ROOT)/(.88-UV_ROOT),0,1)
faces, face_uvs, face_normals = [], [], []
for row in range(len(zs)-1):
    for i in range(count):
        k = (i+1)%count
        faces.append((row*count+i,row*count+k,(row+1)*count+k,(row+1)*count+i))
        face_uvs.append(((u[i],v[row]),(u[k],v[row]),(u[k],v[row+1]),(u[i],v[row+1])))
        face_normals.append((normal[row,i],normal[row,i],normal[row+1,i],normal[row+1,i]))
for row, reverse in [(0,True),(len(zs)-1,False)]:
    center = len(verts)
    verts.append(coords[row].mean(axis=0).tolist())
    cap_normal = (0,0,-1 if reverse else 1)
    for i in range(count):
        k = (i+1)%count
        a,b = (k,i) if reverse else (i,k)
        faces.append((row*count+a,row*count+b,center))
        face_uvs.append(((u[a],v[row]),(u[b],v[row]),(.5,v[row])))
        face_normals.append((cap_normal,cap_normal,cap_normal))

mesh = bpy.data.meshes.new(NAME+'_PlanarSolidV4')
mesh.from_pydata(verts,[],faces)
mesh.update()
uv = mesh.uv_layers.new(name='UVMap')
loops_uv = np.concatenate([np.asarray(values) for values in face_uvs],axis=0)
uv.data.foreach_set('uv',loops_uv.ravel())
for f in mesh.polygons:
    f.use_smooth = True
mesh.normals_split_custom_set(np.concatenate([np.asarray(values) for values in face_normals],axis=0).tolist())

steel = bpy.data.materials.new('M_TangDaoTengyunSteel')
steel.use_nodes = True
nt = steel.node_tree
bs = next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
for key,socket in [('BaseColor','Base Color'),('Normal','Normal'),('ORM',None)]:
    image = bpy.data.images.load(str(T/'Textures'/('TangDao_Tengyun_'+key+'.png')),check_existing=True)
    image.colorspace_settings.name = 'sRGB' if key=='BaseColor' else 'Non-Color'
    node = nt.nodes.new('ShaderNodeTexImage')
    node.image = image
    if key=='ORM':
        separate = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(node.outputs['Color'],separate.inputs[0])
        nt.links.new(separate.outputs['Green'],bs.inputs['Roughness'])
        nt.links.new(separate.outputs['Blue'],bs.inputs['Metallic'])
    elif key=='Normal':
        n = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(node.outputs['Color'],n.inputs['Color'])
        nt.links.new(n.outputs['Normal'],bs.inputs['Normal'])
    else:
        nt.links.new(node.outputs['Color'],bs.inputs[socket])
mesh.materials.append(steel)
obj = bpy.data.objects.new(NAME+'_LOD0',mesh)
bpy.context.scene.collection.objects.link(obj)
obj.matrix_world = Matrix.Identity(4)
for other in bpy.context.scene.objects:
    if other.type=='MESH':
        other.hide_render = other != obj
        other.hide_set(other != obj)
obj.hide_set(False)
group = bpy.data.objects.new(NAME+'_LODGroup',None)
group['fbx_type'] = 'LodGroup'
bpy.context.scene.collection.objects.link(group)
obj.parent = group
lods = [obj]
for level,ratio in [(1,.55),(2,.26)]:
    lod = obj.copy()
    lod.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(lod)
    lod.name = NAME+'_LOD'+str(level)
    lod.hide_set(False)
    bpy.context.view_layer.objects.active = lod
    modifier = lod.modifiers.new('Distance LOD','DECIMATE')
    modifier.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    lod.hide_render = True
    lods.append(lod)
print('TENGYUN_PLANAR_EXPORTING',flush=True)
out = T/'Export'
out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
group.select_set(True)
for lod in lods:
    lod.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(filepath=str(out/(NAME+'.fbx')),use_selection=True,
    object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/(NAME+'.glb')),use_selection=True,export_format='GLB')
for lod in lods[1:]:
    lod.hide_set(True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(T/'TangDao_TengyunBlade_Editable.blend'))
counts = []
for lod in lods:
    lod.data.calc_loop_triangles()
    counts.append(len(lod.data.loop_triangles))
material = SURFACE_UE+'/Materials/M_TangDaoBladeRuneSurface_CloudTengyunJoint'
manifest = {
    'id':'tengyun_dragon','weapon':'ue_tang_dao','slot':'blade_1','name':'腾云游龙刀身',
    'ue_root':UE,'mesh_name':NAME,'mesh':UE+'/Meshes/'+NAME+'_SolidV4.'+NAME+'_SolidV4',
    'surface_ue_root':SURFACE_UE,'material_name':'M_TangDaoBladeRuneSurface_CloudTengyunJoint',
    'reuse_saved_surface':True,'preserve_ui_icon':True,
    'interface':'tang_dao_hilt_v1','location_cm':[0,0,0],
    'trace_base_cm':[0,0,3],'trace_tip_cm':[9.505,0,88],'rune_dimensions_cm':[14,12,74],
    'materials':{'M_TangDaoTengyunSteel':material+'.'+material.rsplit('/',1)[-1]},
    'lod_triangles':counts,'uv_z_cm':[1.4,88],'base_z_cm':BASE*100,
    'guard_seat_overlap_mm':.6,'original_geometry_retained':False,
    'mounting_root_unchanged':False,'original_surface_material_retained':False,
    'body_thickness_mm':HALF_THICKNESS*2000,'body_faces_parallel':True,
    'longitudinal_thickness_taper':'none; only final 2mm tip bevel',
    'tip_bevel_z_cm':[87.8,88],'fuller_depth_mm':.70,'fuller_centers_across_blade':[.855],
    'fuller_z_cm':[16.5,75.5],'blade_tip_cm':[9.505,0,88],
    'dragon_relief':'existing baked normal map; planar geometry',
    'repair_revision':'TangDaoTengyunPlanarSolidV4_20261002',
    'reference':str(T/'Reference/TengyunBlade_UserReference.png'),
    'repair_reference':str(P/'Reference/ReportedWarpedRoot.png'),
    'scope':'Uniform-thickness planar blade and clean hilt seat; original silhouette, atlas, native/cloud runes and gameplay retained',
    'runtime_tested':False}
(T/'blade_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'authoring_recipe.json').write_text(json.dumps({
    'revision':manifest['repair_revision'],'profile_z_cm':(profile_z*100).tolist(),
    'edge_x_cm':(profile_edge*100).tolist(),'spine_x_cm':(profile_spine*100).tolist(),
    'body_thickness_mm':7,'cross_section_orientation':'fixed X/Y; no perimeter interpolation',
    'original_root_removed':True,'main_faces':'parallel planar steel',
    'dragon_detail_source':'unchanged albedo and baked normal',
    'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('TENGYUN_PLANAR_AUTHORED',json.dumps({'mesh':manifest['mesh'],'lod_triangles':counts,'body_thickness_mm':7}),flush=True)
