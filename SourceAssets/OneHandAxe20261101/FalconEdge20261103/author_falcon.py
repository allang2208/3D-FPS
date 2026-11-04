"""Author the exclusive axe head from its actual factory interface. Production only."""
import bpy,bmesh,json,math,sys,ast
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
SOURCE=P.parent/'ModulesV1/TacticalHatchet_Modules_Editable.blend'
BASE=P.parent/'Textures'
DEST='/Game/Weapons/TacticalHatchet20261101/FalconEdge20261103'
for folder in ('Export','Textures','IconInputs','Icons','Before'):(P/folder).mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P.parents[1]/'KukriComponentVariants20261026'))
from asset_tools import *
design=json.loads((P/'design.json').read_text('utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
for o in scene.objects:o.hide_render=True;o.hide_set(True)
source=bpy.data.objects['SM_TacticalHatchet_Head_Factory'].data
CY=.0006362
ZMIN=.180;ZMAX=max(v.co.z for v in source.vertices);COUNT=240
sections=[]
for i in range(COUNT+1):
    z=ZMIN+(ZMAX-ZMIN)*i/COUNT;xs=[]
    for edge in source.edges:
        a,b=(source.vertices[j].co for j in edge.vertices)
        if min(a.z,b.z)<=z<=max(a.z,b.z) and abs(b.z-a.z)>1e-9:xs.append(a.x+(b.x-a.x)*(z-a.z)/(b.z-a.z))
    sections.append(max(xs) if xs else max(v.co.x for v in source.vertices))
def front(z):
    t=min(COUNT,max(0.,(z-ZMIN)/(ZMAX-ZMIN)*COUNT));i=min(COUNT-1,int(t));f=t-i
    return sections[i]*(1-f)+sections[i+1]*f
def bevel(p):return (1-smooth(.003,.015,front(p.z)-p.x))*smooth(.065,.105,p.x)
def deform(p):
    if p.z<=ZMIN:return p.copy()
    q=p.copy();root=smooth(.180,.235,p.z);side=p.y-CY
    cutting=root*smooth(.065,.13,p.x)
    q.x+=.007*cutting
    q.z-=.007*cutting*(1-smooth(.21,.26,p.z))
    # Compress the square factory poll into a short downward-facing beak.
    beak=smooth(.004,.045,-p.x)*smooth(.235,.255,p.z)
    q.x-=.022*beak
    q.z=(1-beak)*q.z+beak*(.267+(p.z-.274)*.10)
    q.y=CY+side*(1-.18*root)*(1-.55*beak)
    return q
name='SM_TacticalHatchet_Head_FalconEdge'
obj=derived_mesh(source,name,deform,levels=0)
colors=obj.data.color_attributes.new(name='BladeData',type='FLOAT_COLOR',domain='CORNER')
for i,loop in enumerate(obj.data.loops):
    # derived_mesh emits source triangle corners in their original order.
    tri=source.loop_triangles[i//3];p=source.vertices[source.loops[tri.loops[i%3]].vertex_index].co
    colors.data[i].color=(smooth(.180,.225,p.z),max(bevel(p),smooth(.020,.044,-p.x)),0,1)
# Reuse the established carbon-steel authoring and original neck surface.
src=P.parent/'BladeVariants20261102/author_blades.py'
tree=ast.parse(src.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('noise_output','author_material')],type_ignores=[]),str(src),'exec'),globals())
bodymat=author_material('HeavyCleaver')
wallmat=constant_material('Author_Falcon_MachinedHole',(.24,.25,.26),.96,.27)
obj.data.materials.append(bodymat[0]);obj.data.materials.append(wallmat[0])
# Closed triangular prism: one real through-hole, rounded corners, no painted void.
polygon=[(.021,.289),(.091,.282),(.032,.263)]
verts=[(x,y,z) for y in (-.06,.06) for x,z in polygon]
faces=[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)]
mesh=bpy.data.meshes.new('FalconWindowCutter');mesh.from_pydata(verts,[],faces);mesh.update()
cut=bpy.data.objects.new('FalconWindowCutter',mesh);scene.collection.objects.link(cut)
activate(cut);bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
rounds=cut.modifiers.new('RoundedWindowCorners','BEVEL');rounds.width=.0015;rounds.segments=4
bpy.ops.object.modifier_apply(modifier=rounds.name)
activate(obj);mod=obj.modifiers.new('TriangularThroughWindow','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
# Newly exposed bore faces get steel rather than interpolated source UV color.
for face in obj.data.polygons:
    p=face.center
    if .018<p.x<.094 and .260<p.z<.292 and abs(face.normal.y)<.75:face.material_index=1
# Only the new aperture perimeter receives a small machined chamfer.
mesh=obj.data
weights=mesh.attributes.get('bevel_weight_edge') or mesh.attributes.new('bevel_weight_edge','FLOAT','EDGE')
adj={}
for face in mesh.polygons:
    for key in face.edge_keys:adj.setdefault(tuple(sorted(key)),[]).append(face.normal.copy())
for edge in mesh.edges:
    mid=sum((mesh.vertices[i].co for i in edge.vertices),Vector())*.5
    normals=adj.get(tuple(sorted(edge.vertices)),[])
    weights.data[edge.index].value=1. if .018<mid.x<.094 and .260<mid.z<.292 and len(normals)==2 and normals[0].angle(normals[1],0.)>.65 else 0.
rim=obj.modifiers.new('MachinedWindowRim','BEVEL');rim.limit_method='WEIGHT';rim.width=.00035;rim.segments=2;rim.affect='EDGES';rim.harden_normals=True
bpy.ops.object.modifier_apply(modifier=rim.name)
unwrap(obj)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
maps=bake(obj,[bodymat,wallmat],'T_TacticalHatchet_Head_FalconEdge',P/'Textures',2048)
activate(obj);fbx=P/'Export'/(name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False)
entry={'id':design['id'],'name':design['name'],'slot':'blade_1','object':name,'fbx':str(fbx),'origin_cm':[0,0,0],
       'textures':maps,'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'normal_convention':'OpenGL tangent; UE green flip',
       'source':str(SOURCE),'frozen_neck_max_z_cm':18.,'head_cut_z_cm':11.5,'runtime_tested':False}
catalog=json.loads((P.parents[2]/'Content/ColdSteelData/tactical-hatchet-modules.json').read_text('utf-8'))
trace=catalog['slots']['blade_1']['factory']
for field in ('trace_base_cm','trace_tip_cm'):
    original=Vector(trace[field])*.01;original.y=-original.y
    point=deform(original)*100;entry[field]=[point.x,-point.y,point.z]
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_FalconEdge_Editable.blend'))
(P/'falcon_edge.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FALCON_EDGE_AUTHORED '+str(entry['triangles']),flush=True)
