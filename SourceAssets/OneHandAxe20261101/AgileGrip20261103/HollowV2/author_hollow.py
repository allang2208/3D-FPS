"""Produce a real through-window in the existing agile/breaker grip. No test render."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;SOURCE=P.parent/'TacticalHatchet_AgileGrip_Editable.blend'
design=json.loads((P.parent/'design.json').read_text('utf-8'))
prior=json.loads((P/'Before/agile_grip.json').read_text('utf-8'))
sys.path.insert(0,str(P.parents[2]/'KukriComponentVariants20261026'))
from asset_tools import *
for folder in ('Export','Textures','IconInputs','Icons','Before'):(P/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene
for o in scene.objects:o.hide_set(True);o.hide_render=True
original=bpy.data.objects['SM_TacticalHatchet_GripAgile']
obj=original.copy();obj.data=original.data.copy();scene.collection.objects.link(obj)
name='SM_TacticalHatchet_GripAgileHollowV2';obj.name=name;obj.data.name=name;obj.location=(0,0,0)
# SourceUV is now the finished V1 grip's baked UV, not the factory texture layout.
mesh=obj.data
uv=mesh.uv_layers.get('SourceUV') or mesh.uv_layers.new(name='SourceUV')
for a,b in zip(uv.data,mesh.uv_layers[0].data):a.uv=b.uv
obj.data.materials.clear()
CX=-.0015;TOP=-.065;BOTTOM=-.139;RADIUS=.0068
def radius(p):return math.hypot(p.x-CX,p.z-max(BOTTOM,min(TOP,p.z)))
m,nt,bs,out=make_mat('Author_GripAgileHollowV2')
base=tex(nt,prior['textures']['BaseColor'],True,'SourceUV')
orm=tex(nt,prior['textures']['ORM'],False,'SourceUV')
normal=tex(nt,prior['textures']['Normal'],False,'SourceUV')
channels=node(nt,'ShaderNodeSeparateColor');nt.links.new(orm.outputs[0],channels.inputs[0])
nm=node(nt,'ShaderNodeNormalMap',uv_map='SourceUV');nt.links.new(normal.outputs[0],nm.inputs['Color'])
tc=node(nt,'ShaderNodeTexCoord');xyz=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],xyz.inputs[0])
x,y,z=xyz.outputs
dx=op(nt,'SUBTRACT',x,CX)
dz=op(nt,'SUBTRACT',z,op(nt,'MINIMUM',TOP,op(nt,'MAXIMUM',BOTTOM,z)))
dist=op(nt,'SQRT',op(nt,'ADD',op(nt,'MULTIPLY',dx,dx),op(nt,'MULTIPLY',dz,dz)))
fade=node(nt,'ShaderNodeMapRange');put(nt,fade.inputs['Value'],dist)
fade.inputs['From Min'].default_value=RADIUS+.0004;fade.inputs['From Max'].default_value=RADIUS+.0017
fade.interpolation_type='SMOOTHSTEP';fade.clamp=True
rim=op(nt,'SUBTRACT',1,fade.outputs['Result'])
grain=node(nt,'ShaderNodeTexNoise');nt.links.new(tc.outputs['Object'],grain.inputs['Vector']);grain.inputs['Scale'].default_value=2100
silver=mix(nt,grain.outputs['Fac'],(.19,.20,.21,1),(.27,.28,.29,1))
color=mix(nt,rim,base.outputs[0],silver)
rough=mix(nt,rim,channels.outputs[1],(.30,.30,.30,1))
metal=mix(nt,rim,channels.outputs[2],(.95,.95,.95,1))
packed=node(nt,'ShaderNodeCombineColor');nt.links.new(channels.outputs[0],packed.inputs[0]);put(nt,packed.inputs[1],rough);put(nt,packed.inputs[2],metal)
geo=node(nt,'ShaderNodeNewGeometry');n=mix(nt,rim,nm.outputs[0],geo.outputs['Normal'])
for socket,value in [('Base Color',color),('Roughness',rough),('Metallic',metal),('Normal',n)]:put(nt,bs.inputs[socket],value)
body=(m,{'BaseColor':color,'ORM':packed.outputs[0]},bs,out)
wall=constant_material('Author_GripHollowInnerWall',(.22,.23,.24),.95,.32)
obj.data.materials.append(m);obj.data.materials.append(wall[0])
for face in obj.data.polygons:face.material_index=0
# Capsule cutter in XZ, traversing the full Y thickness and every original layer.
polygon=[]
for center,start in ((TOP,0),(BOTTOM,math.pi)):
    for i in range(33):
        a=start+math.pi*i/32
        polygon.append((CX+RADIUS*math.cos(a),center+RADIUS*math.sin(a)))
count=len(polygon)
verts=[(x,y,z) for y in (-.045,.045) for x,z in polygon]
faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
faces.extend((i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count))
cutmesh=bpy.data.meshes.new('GripLongWindowCutter');cutmesh.from_pydata(verts,[],faces);cutmesh.update()
cut=bpy.data.objects.new('GripLongWindowCutter',cutmesh);scene.collection.objects.link(cut)
bm=bmesh.new();bm.from_mesh(cutmesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cutmesh);bm.free()
activate(obj);cutmod=obj.modifiers.new('CentralThroughWindow','BOOLEAN');cutmod.operation='DIFFERENCE';cutmod.solver='EXACT';cutmod.object=cut
bpy.ops.object.modifier_apply(modifier=cutmod.name);bpy.data.objects.remove(cut,do_unlink=True)
mesh=obj.data
for face in mesh.polygons:
    if abs(radius(face.center)-RADIUS)<.0003 and abs(face.normal.y)<.75:face.material_index=1
# Chamfer only the newly cut window; preserve the existing authored joint normals.
adj={}
for face in mesh.polygons:
    for key in face.edge_keys:adj.setdefault(tuple(sorted(key)),[]).append(face.normal.copy())
weights=mesh.attributes.get('bevel_weight_edge') or mesh.attributes.new('bevel_weight_edge','FLOAT','EDGE')
for edge in mesh.edges:
    mid=sum((mesh.vertices[i].co for i in edge.vertices),Vector())*.5;normals=adj.get(tuple(sorted(edge.vertices)),[])
    weights.data[edge.index].value=1. if abs(radius(mid)-RADIUS)<.0004 and len(normals)==2 and normals[0].angle(normals[1],0.)>.6 else 0.
bevelmod=obj.modifiers.new('SoftMachinedWindowEdges','BEVEL');bevelmod.limit_method='WEIGHT';bevelmod.width=.0004;bevelmod.segments=3;bevelmod.harden_normals=True
bpy.ops.object.modifier_apply(modifier=bevelmod.name)
# Freeze the newly cut n-gons before tangent-space baking and FBX export.
tri=obj.modifiers.new('ExportWindowTriangles','TRIANGULATE');tri.min_vertices=5
if hasattr(tri,'keep_custom_normals'):tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
# Boolean/bevel may carry material slots from evaluated data: explicitly bind the
# two authored surfaces so every face participates in the PBR bake.
obj.data.materials.clear();obj.data.materials.append(body[0]);obj.data.materials.append(wall[0])
for face in obj.data.polygons:
    face.material_index=1 if abs(radius(face.center)-RADIUS)<.0006 and abs(face.normal.y)<.8 else 0
unwrap(obj)
scene.render.engine='CYCLES';scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
maps=bake(obj,[body,wall],'T_TacticalHatchet_GripAgileHollowV2',P/'Textures',2048)
activate(obj);fbx=P/'Export'/(name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False,bake_anim=False)
entry={'id':design['id'],'name':design['name'],'slot':'grip','object':name,'fbx':str(fbx),'textures':maps,
    'mesh':'/Game/Weapons/TacticalHatchet20261101/ModulesV1/'+name+'.'+name,
    'factory_grip_length_cm':19.25,'extension_cm':0,'material_slot':obj.data.materials[0].name,
    'origin_cm':[0,0,11.5],'pommel_offset_cm':[0,0,0],'grip_length_cm':19.25,
    'window':{'width_cm':RADIUS*200,'tip_z_cm':[(BOTTOM-RADIUS)*100,(TOP+RADIUS)*100],'through_axis':'Y'},
    'interface':'Original upper/lower joints and outside hand-contact envelope retained; continuous rails surrounding a central rounded through-window',
    'stats':design['stats'],'design_revision':design['revision'],'model_revision':'hollow_v2_20261103',
    'modification_tier':'Special','triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
    'normal_convention':'OpenGL tangent; one UE green-channel flip','runtime_tested':False}
(P/'hollow_grip.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
obj.location=(0,0,.115)
for key in ('SM_TacticalHatchet_Head_Factory','SM_TacticalHatchet_Pommel_Factory'):
    part=bpy.data.objects[key];part.hide_set(False);part.hide_render=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_GripAgile_HollowV2_Editable.blend'))
print('HOLLOW_GRIP_AUTHORED triangles='+str(entry['triangles']),flush=True)
