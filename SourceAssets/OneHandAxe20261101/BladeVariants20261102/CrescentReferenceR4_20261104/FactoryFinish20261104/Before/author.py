"""Approved Draft02 curves, continuous thickness field, and an edge-connected stock neck."""
import bpy,bmesh,math,json,sys,ast
from pathlib import Path
from mathutils import Vector,geometry
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'KukriComponentVariants20261026'))
from asset_tools import *
KIND='SwiftCrescent';ID='axe_swift_crescent';CY=.0006362;CENTER_X=.003511
SCALE=.031743/31.;ROOT_Z=.165;ROOT_V=240-(ROOT_Z-.115)/SCALE
for directory in ['Export','Textures','Icons','Before','Review']:(P/directory).mkdir(parents=True,exist_ok=True)
design=json.loads((P.parent/'CrescentReferenceDraft02/design.json').read_text('utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(P.parents[1]/'ModulesV1/TacticalHatchet_Modules_Editable.blend'))
factory=bpy.data.objects['SM_TacticalHatchet_Head_Factory']
for obj in bpy.context.scene.objects:obj.hide_render=True;obj.hide_set(True)
helper=P.parent/'RebuildV2/author.py'
tree=ast.parse(helper.read_text('utf-8-sig'))
defs=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='author_material'],type_ignores=[])
exec(compile(defs,str(helper),'exec'),globals())
materials=[author_material(False),author_material(True)]

def cubic(a,b,c,d,n):
    a,b,c,d=map(Vector,(a,b,c,d))
    return [tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d) for t in [i/n for i in range(1,n+1)]]
def sampled(commands):
    points=[]
    for op,*v in commands:
        if op=='M':points.append(tuple(v))
        elif op=='L':
            end=Vector(v);start=Vector(points[-1]);n=max(1,math.ceil((end-start).length/1.6))
            points.extend(tuple(start.lerp(end,i/n)) for i in range(1,n+1))
        elif op=='C':
            control=[points[-1],tuple(v[:2]),tuple(v[2:4]),tuple(v[4:6])]
            length=sum((Vector(control[i+1])-Vector(control[i])).length for i in range(3))
            points.extend(cubic(*control,max(12,math.ceil(length/1.5))))
    if (Vector(points[0])-Vector(points[-1])).length<1e-7:points.pop()
    return points
def coords(u,v,h):return (CENTER_X+(165.5-u)*SCALE,CY+h,.115+(240-v)*SCALE)
def half_thickness(u,v):
    shoulder=smooth(117,153,u)*(1-smooth(183,222,u))
    neck=.0068+(.0085-.0068)*(1-smooth(159,188,v))
    return .0044+(neck-.0044)*shoulder

# Wedge strip is explicitly shared with the main face, matching the design's silver edge boundary.
N=72
outer=[(114.,46.)]+cubic((114,46),(84,43),(52,78),(49,118),N)+cubic((49,118),(46,161),(69,200),(109,218),N)
inner=[(114.,46.)]+cubic((114,46),(94,70),(77,100),(77,137),N)+cubic((77,137),(75,174),(88,198),(109,218),N)
rest=[list(c) for c in design['outline'][3:]]
for command in rest:
    if command[0]=='L' and command[-1]==240:command[-1]=ROOT_V
rest_points=sampled([['M',109,218]]+rest)
# Both chains end at the top horn; remove its closing duplicate.
if (Vector(rest_points[-1])-Vector(inner[0])).length<1e-6:rest_points.pop()
boundary=inner+rest_points[1:]

def inside(x,y,points):
    hit=False
    for i,a in enumerate(points):
        b=points[(i+1)%len(points)]
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
    return hit
points=list(boundary)
for u in [49.37+i*1.65 for i in range(110)]:
    for v in [47.23+i*1.65 for i in range(117)]:
        if inside(u,v,boundary):points.append((u,v))
vecs=[Vector(p) for p in points];n=len(boundary)
result=geometry.delaunay_2d_cdt(vecs,[(i,(i+1)%n) for i in range(n)],[list(range(n))],1,1e-7,False)
flat_verts,_,flat_faces=result[:3]
verts=[];faces=[];matids=[];lookup={}
def vertex(position):
    key=tuple(round(float(x),8) for x in position)
    if key not in lookup:lookup[key]=len(verts);verts.append(key)
    return lookup[key]
def add_face(indices,material=0):
    indices=list(dict.fromkeys(indices))
    if len(indices)>=3:faces.append(indices);matids.append(material)
def face_height(u,v):
    # Tip thickness converges to the edge; the broad face stays planar away from the shoulder.
    distance=min(math.hypot(u-114,v-46),math.hypot(u-109,v-218))
    return .00025+(half_thickness(u,v)-.00025)*smooth(0,5,distance)
for side in (-1,1):
    mapping=[vertex(coords(u,v,side*face_height(u,v))) for u,v in flat_verts]
    for face in flat_faces:add_face([mapping[i] for i in (face if side==1 else face[::-1])])
    grid={}
    for i,(a,b) in enumerate(zip(outer,inner)):
        for j in range(5):
            t=j/4.;p=Vector(a).lerp(Vector(b),t)
            h=.00025+(face_height(*b)-.00025)*t
            grid[i,j]=vertex(coords(*p,side*h))
    for i in range(len(outer)-1):
        for j in range(4):
            q=[grid[i,j],grid[i+1,j],grid[i+1,j+1],grid[i,j+1]]
            add_face(q if side==1 else q[::-1],1)
# Outer perimeter: a narrow edge ribbon and the remaining non-cutting outline.
for i in range(len(outer)-1):
    a,b=outer[i:i+2]
    add_face([vertex(coords(*a,-.00025)),vertex(coords(*b,-.00025)),vertex(coords(*b,.00025)),vertex(coords(*a,.00025))],1)
remaining=rest_points+[inner[0]]
for a,b in zip(remaining,remaining[1:]):
    # Leave the bottom ring open for the actual factory-profile loft.
    if abs(a[1]-ROOT_V)<1e-3 and abs(b[1]-ROOT_V)<1e-3:continue
    ha,hb=face_height(*a),face_height(*b)
    add_face([vertex(coords(*a,-ha)),vertex(coords(*b,-hb)),vertex(coords(*b,hb)),vertex(coords(*a,ha))])
mesh=bpy.data.meshes.new('ReferenceShapeContinuousHead');mesh.from_pydata(verts,[],faces);mesh.update()
body=bpy.data.objects.new('SM_TacticalHatchet_Head_SwiftCrescent_R4',mesh);bpy.context.scene.collection.objects.link(body)
for material,*_ in materials:mesh.materials.append(material)
for face,index in zip(mesh.polygons,matids):face.material_index=index
activate(body)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-7)
bmesh.ops.dissolve_degenerate(bm,dist=2e-7,edges=list(bm.edges))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))

# Retain the exact factory lower neck. Split its upper ring and the new head's lower ring to common angular samples.
stock=bmesh.new();stock.from_mesh(factory.data)
bmesh.ops.bisect_plane(stock,geom=list(stock.verts)+list(stock.edges)+list(stock.faces),dist=1e-7,
    plane_co=(0,0,.130),plane_no=(0,0,1),clear_outer=True)
stock.normal_update()
mapping={v:bm.verts.new(v.co) for v in stock.verts}
for f in stock.faces:
    nf=bm.faces.new([mapping[v] for v in f.verts]);nf.material_index=0
stock.free();bm.normal_update()
def boundary_ring(z):
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<2e-6 for v in e.verts)]
    points=set(v for e in edges for v in e.verts)
    if not points:raise RuntimeError('Missing mating loop at '+str(z))
    center=Vector(((min(v.co.x for v in points)+max(v.co.x for v in points))/2,
                   (min(v.co.y for v in points)+max(v.co.y for v in points))/2,z))
    ordered=sorted((math.atan2(v.co.y-center.y,v.co.x-center.x)%(2*math.pi),v) for v in points)
    return center,ordered
low_center,low=boundary_ring(.130);high_center,high=boundary_ring(ROOT_Z)
angles=sorted(set(round(a,10) for a,v in low+high)|{0.,math.pi/2,math.pi,math.pi*1.5})
def split_ring(center,ordered):
    output={round(a,10):v for a,v in ordered}
    for index,(a,start) in enumerate(ordered):
        b,end=ordered[(index+1)%len(ordered)]
        if b<=a:b+=2*math.pi
        targets=sorted(t if t>a else t+2*math.pi for t in angles if a+1e-8<(t if t>a else t+2*math.pi)<b-1e-8)
        original=start.co.copy();edge_vector=end.co-original;current=start
        for t in targets:
            ray=Vector((math.cos(t),math.sin(t),0));aa=original-center
            cross=lambda p,q:p.x*q.y-p.y*q.x
            radius=cross(aa,edge_vector)/cross(ray,edge_vector)
            pos=center+ray*radius
            edge=next((e for e in current.link_edges if end in e.verts),None)
            if edge is None:
                raise RuntimeError('Mating boundary is disconnected')
            fraction=(pos-current.co).length/(end.co-current.co).length
            _,new=bmesh.utils.edge_split(edge,current,max(0,min(1,fraction)));new.co=pos
            output[round(t%(2*math.pi),10)]=new;current=new
    return [output[min(output,key=lambda key:abs((key-a+math.pi)%(2*math.pi)-math.pi))] for a in angles]
lower=split_ring(low_center,low);upper=split_ring(high_center,high)
previous=lower
for j in range(1,13):
    t=j/12.;blend=t*t*(3-2*t)
    ring=upper if j==12 else [bm.verts.new(Vector((a.co.x*(1-blend)+b.co.x*blend,a.co.y*(1-blend)+b.co.y*blend,.130+(ROOT_Z-.130)*t))) for a,b in zip(lower,upper)]
    for i in range(len(ring)):
        k=(i+1)%len(ring)
        unique=list(dict.fromkeys([previous[i],previous[k],ring[k],ring[i]]))
        if len(unique)>2:bm.faces.new(unique).material_index=0
    previous=ring
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-7)
bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
# Keep the curved thickness field; remove unnecessary grid edges on truly planar regions.
bmesh.ops.dissolve_limit(bm,angle_limit=1e-5,use_dissolve_boundaries=False,
    verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL','MATERIAL'})
bm.to_mesh(mesh);bm.free()
activate(body)
bevel_mod=body.modifiers.new('SoftNonCuttingRims','BEVEL');bevel_mod.width=.00038;bevel_mod.segments=3
bevel_mod.limit_method='ANGLE';bevel_mod.angle_limit=math.radians(40);bevel_mod.use_clamp_overlap=True
bpy.ops.object.modifier_apply(modifier=bevel_mod.name)
# Smooth the continuous shoulder and neck; flat areas retain their geometric normals.
for face in mesh.polygons:face.use_smooth=True
bm=bmesh.new();bm.from_mesh(mesh)
for edge in bm.edges:edge.smooth=len(edge.link_faces)==2 and edge.calc_face_angle(0)<math.radians(48)
bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
normal=body.modifiers.new('AreaWeightedSurfaceNormals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=35
bpy.ops.object.modifier_apply(modifier=normal.name)
if not mesh.uv_layers:mesh.uv_layers.new(name='UVMap')
unwrap(body)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU' if any(device.use for device in prefs.devices) else 'CPU'
maps=bake(body,materials,'T_TacticalHatchet_Head_SwiftCrescent_R4',P/'Textures',2048)
for material in mesh.materials:
    for node in material.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image:node.image.pack()
fbx=P/'Export'/(body.name+'.fbx');export(body,fbx)
def trace(index):
    x,y,z=coords(*outer[index],0);return [x*100,-y*100,z*100]
entry={'id':ID,'name':'轻型钩月斧刃','kind':KIND,'slot':'blade_1','object':body.name,'fbx':str(fbx),'textures':maps,
       'origin_cm':[0,0,0],'mesh':'/Game/Weapons/TacticalHatchet20261101/ModulesV1/'+body.name+'.'+body.name,
       'material_slot':mesh.materials[0].name,'model_revision':'approved_reference_draft02_r4_20261104',
       'design_source':str(P.parent/'CrescentReferenceDraft02/design.json'),
       'geometry':{'triangles':len(mesh.polygons),'dimensions_cm':[float(d)*100 for d in body.dimensions],
                   'stock_interface_z_cm':11.5,'continuous_loft_rings':12,'design_scale_m':SCALE},
       'trace_base_cm':trace(125),'trace_tip_cm':trace(17)}
(P/'SwiftCrescent.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'SwiftCrescent_Editable.blend'))
print('REFERENCE_CRESCENT_R4_AUTHORED '+json.dumps(entry['geometry']),flush=True)
