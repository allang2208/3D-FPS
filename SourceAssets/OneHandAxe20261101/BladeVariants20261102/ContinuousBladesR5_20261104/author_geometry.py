"""Continuous forged shoulders, convex ground bevels and connected stock necks."""
import ast,bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,geometry
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'KukriComponentVariants20261026'))
from asset_tools import *
COMMON=P.parent/'CrescentReferenceR4_20261104/FactoryFinish20261104'
KIND=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'HeavyCleaver'
ID,LABEL,T,W={'HeavyCleaver':('axe_heavy_cleaver','厚背重劈斧刃',.012,.026),
    'FoldedArc':('axe_folded_arc','百炼弧锋斧刃',.009,.020)}[KIND]
CY=.0006362;ROOT_Z=.170
for folder in ['Export','Geometry','IconInputs','Icons','Before',KIND+'/Textures',KIND+'/Before/Textures']:(P/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parents[1]/'ModulesV1/TacticalHatchet_Modules_Editable.blend'))
factory=bpy.data.objects['SM_TacticalHatchet_Head_Factory']
for obj in bpy.context.scene.objects:obj.hide_render=True;obj.hide_set(True)
helper=P.parent/'RebuildV2/author.py'
source=helper.read_text('utf-8-sig').replace('n=18','n=36').replace(',42)',',96)')
tree=ast.parse(source)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'cubic','contour','author_material'}],type_ignores=[]),str(helper),'exec'),globals())
joint_helper=COMMON/'Before/author.py';tree=ast.parse(joint_helper.read_text('utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'boundary_ring','split_ring'}],type_ignores=[]),str(joint_helper),'exec'),globals())
materials=[author_material(False),author_material(True)]
outline,start,end=contour()
outline[0]=(outline[0][0],ROOT_Z);outline[-1]=(outline[-1][0],ROOT_Z)
outer=outline[start:end+1];inner=[]
for i,(x,z) in enumerate(outer):
    t=i/(len(outer)-1)
    width=W*math.sin(math.pi*t)
    inner.append((x-width,z))
# Side face: inner edge from upper to lower tip, then the neck and spine back to the upper tip.
rest=outline[end:]+outline[:start+1]
boundary=inner+rest[1:-1]
# Densify straight segments to support the thickness field without large thin triangles.
dense=[]
for i,a in enumerate(boundary):
    b=boundary[(i+1)%len(boundary)];length=(Vector(b)-Vector(a)).length
    dense.append(a)
    if i>=len(inner)-1:
        steps=max(1,math.ceil(length/.002))
        dense.extend(tuple(Vector(a).lerp(Vector(b),j/steps)) for j in range(1,steps))
boundary=dense

def inside(x,z):
    hit=False
    for i,a in enumerate(boundary):
        b=boundary[(i+1)%len(boundary)]
        if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:hit=not hit
    return hit

def half_height(x,z):
    # Thick shoulder tapers across the whole face before meeting the grinding zone.
    near_edge=.0055 if KIND=='HeavyCleaver' else .0043
    head=T+(near_edge-T)*smooth(.035,.140,x)
    neck=.0069
    value=neck+(head-neck)*smooth(ROOT_Z,.225,z)
    tip_distance=min(math.hypot(x-outer[0][0],z-outer[0][1]),math.hypot(x-outer[-1][0],z-outer[-1][1]))
    return .00030+(value-.00030)*smooth(0,.010,tip_distance)

points=list(boundary)
for x in np.arange(-.0447,.198,.0024):
    for z in np.arange(ROOT_Z+.0011,.315,.0024):
        if inside(x,z):points.append((x,z))
n=len(boundary)
flat,_,triangles,*_=geometry.delaunay_2d_cdt([Vector((x*1000,z*1000)) for x,z in points],
    [(i,(i+1)%n) for i in range(n)],[list(range(n))],1,1e-6,False)
verts=[];faces=[];matids=[];lookup={}
def vertex(x,y,z):
    key=tuple(round(float(v),8) for v in (x,y,z))
    if key not in lookup:lookup[key]=len(verts);verts.append(key)
    return lookup[key]
def face(indices,material=0):
    ids=list(dict.fromkeys(indices))
    if len(ids)>=3:faces.append(ids);matids.append(material)
for side in [-1,1]:
    mapping=[vertex(x/1000,CY+side*half_height(x/1000,z/1000),z/1000) for x,z in flat]
    for tri in triangles:face([mapping[i] for i in (tri if side==1 else tri[::-1])])
    grid={}
    for i,(a,b) in enumerate(zip(outer,inner)):
        for j in range(13):
            t=j/12;x,z=Vector(a).lerp(Vector(b),t)
            # C1 approach to the main face: same height and slope at the grinding shoulder.
            h=.00030+(half_height(x,z)-.00030)*math.sin(t*math.pi/2)
            grid[i,j]=vertex(x,CY+side*h,z)
    for i in range(len(outer)-1):
        for j in range(12):
            q=[grid[i,j],grid[i+1,j],grid[i+1,j+1],grid[i,j+1]]
            face(q if side==1 else q[::-1],1)
for a,b in zip(outer,outer[1:]):face([vertex(a[0],CY-.0003,a[1]),vertex(b[0],CY-.0003,b[1]),vertex(b[0],CY+.0003,b[1]),vertex(a[0],CY+.0003,a[1])],1)
# Use the subdivided non-cutting perimeter exactly, so all face edges are shared.
remaining=boundary[len(inner)-1:]+[boundary[0]]
for a,b in zip(remaining,remaining[1:]):
    if abs(a[1]-ROOT_Z)<1e-6 and abs(b[1]-ROOT_Z)<1e-6:continue
    ha,hb=half_height(*a),half_height(*b)
    face([vertex(a[0],CY-ha,a[1]),vertex(b[0],CY-hb,b[1]),vertex(b[0],CY+hb,b[1]),vertex(a[0],CY+ha,a[1])])
mesh=bpy.data.meshes.new('Continuous_'+KIND)
mesh.from_pydata(verts,[],faces);mesh.update()
body=bpy.data.objects.new('SM_TacticalHatchet_Head_'+KIND+'_R5',mesh);bpy.context.scene.collection.objects.link(body)
for material,*_ in materials:mesh.materials.append(material)
for f,index in zip(mesh.polygons,matids):f.material_index=index
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-7)
bmesh.ops.dissolve_degenerate(bm,dist=2e-7,edges=list(bm.edges))
# Keep the original assembly end; connect its upper ring directly to the new head.
stock=bmesh.new();stock.from_mesh(factory.data)
bmesh.ops.bisect_plane(stock,geom=list(stock.verts)+list(stock.edges)+list(stock.faces),dist=1e-7,
    plane_co=(0,0,.130),plane_no=(0,0,1),clear_outer=True)
mapping={v:bm.verts.new(v.co) for v in stock.verts}
for f in stock.faces:bm.faces.new([mapping[v] for v in f.verts]).material_index=0
stock.free();bm.normal_update()
low_center,low=boundary_ring(.130);high_center,high=boundary_ring(ROOT_Z)
angles=sorted(set(round(a,10) for a,v in low+high)|{0.,math.pi/2,math.pi,math.pi*1.5})
lower=split_ring(low_center,low);upper=split_ring(high_center,high)
# Match the broad original neck taper, not individual irregular source triangles.
probe=bmesh.new();probe.from_mesh(factory.data)
bmesh.ops.bisect_plane(probe,geom=list(probe.verts)+list(probe.edges)+list(probe.faces),dist=1e-7,
    plane_co=(0,0,.127),plane_no=(0,0,1),clear_outer=True)
below=[v.co.copy() for v in probe.verts if abs(v.co.z-.127)<2e-6]
lo_min=Vector((min(v.co.x for v in lower),min(v.co.y for v in lower),0))
lo_max=Vector((max(v.co.x for v in lower),max(v.co.y for v in lower),0))
be_min=Vector((min(v.x for v in below),min(v.y for v in below),0))
be_max=Vector((max(v.x for v in below),max(v.y for v in below),0));probe.free()
center_slope=((lo_min+lo_max)-(be_min+be_max))/.006
width_slope=((lo_max-lo_min)-(be_max-be_min))/.003
slopes=[]
for v in lower:
    slope=Vector((center_slope.x+(v.co.x-low_center.x)*width_slope.x/(lo_max.x-lo_min.x),
        center_slope.y+(v.co.y-low_center.y)*width_slope.y/(lo_max.y-lo_min.y),0))
    if slope.length>.2:slope=slope.normalized()*.2
    slopes.append(slope)
previous=lower;length=ROOT_Z-.130
for j in range(1,17):
    t=j/16;h00=2*t**3-3*t*t+1;h10=t**3-2*t*t+t;h01=-2*t**3+3*t*t
    ring=upper if j==16 else [bm.verts.new(Vector((a.co.x*h00+s.x*length*h10+b.co.x*h01,
        a.co.y*h00+s.y*length*h10+b.co.y*h01,.130+length*t))) for a,b,s in zip(lower,upper,slopes)]
    for i in range(len(ring)):
        k=(i+1)%len(ring);ids=list(dict.fromkeys([previous[i],previous[k],ring[k],ring[i]]))
        if len(ids)>2:bm.faces.new(ids).material_index=0
    previous=ring
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-7)
bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
activate(body)
bevel=body.modifiers.new('NonCuttingEdgeRadius','BEVEL');bevel.width=.00055;bevel.segments=4
bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(45);bevel.use_clamp_overlap=True
bpy.ops.object.modifier_apply(modifier=bevel.name)
for f in mesh.polygons:f.use_smooth=True
bm=bmesh.new();bm.from_mesh(mesh)
for edge in bm.edges:edge.smooth=len(edge.link_faces)==2 and edge.calc_face_angle(0)<math.radians(50)
bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
normal=body.modifiers.new('ContinuousSurfaceNormals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=25
bpy.ops.object.modifier_apply(modifier=normal.name)
if not mesh.uv_layers:mesh.uv_layers.new(name='UVMap')
unwrap(body)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
prefix='T_TacticalHatchet_Head_'+KIND+'_R5'
maskmaps=bake(body,materials,prefix,P/KIND/'Before/Textures',2048)
mesh.calc_loop_triangles();mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
tris=list(mesh.loop_triangles)
np.savez_compressed(P/KIND/'target_surface.npz',
    points=np.array([[mesh.vertices[v].co[:] for v in tri.vertices] for tri in tris]),
    uv=np.array([[mesh.uv_layers[0].data[li].uv[:] for li in tri.loops] for tri in tris]),
    normals=np.array([[mesh.corner_normals[li].vector[:] for li in tri.loops] for tri in tris]),
    tangents=np.array([[mesh.loops[li].tangent[:] for li in tri.loops] for tri in tris]),
    signs=np.array([[mesh.loops[li].bitangent_sign for li in tri.loops] for tri in tris]))
config={'texture_prefix':prefix,'factory_surface':str(COMMON/'factory_steel.npz'),
    'edge_points_xz_m':outer,'edge_mask_thresholds':[.52,.60]}
if KIND=='FoldedArc':config['body_pattern_linear_mean']=(.15+.168)*.5*1.025
(P/KIND/'transfer_config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
entry={'id':ID,'name':LABEL,'kind':KIND,'slot':'blade_1','object':body.name,
    'mesh':'/Game/Weapons/TacticalHatchet20261101/ModulesV1/'+body.name+'.'+body.name,
    'source_blend':str(P/'Geometry'/(KIND+'_Editable.blend')),'fbx':str(P/'Export'/(body.name+'.fbx')),
    'textures':{role:str(P/KIND/'Textures'/Path(path).name) for role,path in maskmaps.items()},
    'origin_cm':[0,0,0],'model_revision':'continuous_forged_r5_20261104',
    'material_revision':'factory_finish_20261104','material_slot':mesh.materials[0].name,
    'trace_base_cm':[outer[-1][0]*100,-CY*100,outer[-1][1]*100],
    'trace_tip_cm':[outer[0][0]*100,-CY*100,outer[0][1]*100],
    'geometry':{'triangles':len(mesh.polygons),'stock_interface_z_cm':11.5,'loft_sections':16,
        'shoulder_thickness_mm':T*2000,'blade_support_thickness_mm':11 if KIND=='HeavyCleaver' else 8.6,
        'cutting_edge_thickness_mm':.6,'grind_profile':'continuous convex sine profile'}}
(P/(KIND+'.json')).write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
source=json.loads((COMMON/'surface_source.json').read_text('utf-8'));source['target']=entry['mesh']
(P/KIND/'surface_source.json').write_text(json.dumps(source,indent=2)+'\n',encoding='utf-8')
for material in mesh.materials:
    for node in material.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image:node.image.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=entry['source_blend'])
print('CONTINUOUS_R5_AUTHORED '+KIND+' '+json.dumps(entry['geometry']),flush=True)
