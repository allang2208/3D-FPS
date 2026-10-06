"""Build sealed, feathered RSH skins in the current native component frame."""
import json, math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).resolve().parent
inputs=json.loads((O/'panel_inputs.json').read_text(encoding='utf8'))
parts=json.loads(Path(inputs['source']).read_text(encoding='utf8'))
grip=next(p for p in parts if p['name']=='9_l')
current=O.parent/'RSH12Speedloader20261003/Single'
bpy.ops.wm.open_mainfile(filepath=str(current/'RSH12_single_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
root=rig.data.bones['WPN_root'].matrix_local.copy()
alignment=Matrix(json.loads((current/'authoring.json').read_text(encoding='utf8'))['alignment'])
frame=rig.matrix_world@root@alignment
bvh=BVHTree.FromPolygons([Vector(v) for v in grip['verts']],grip['faces'])
for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)

name='SM_RSH12_GripSurface'
V=[];F=[];UV=[];fits=[]
for panel in inputs['panels']:
    side=panel['side'];points=panel['positions_yz'];triangles=panel['triangles_ccw']
    count=len(points);base=len(V);slope=panel['slope_y_from_z'];scale=math.sqrt(1+slope*slope)
    for back in (False,True):
        for index,(y,z) in enumerate(points):
            hit,_,_,_=bvh.ray_cast(Vector((side*.055,y,z)),Vector((-side,0,0)))
            if hit is None:raise RuntimeError('RSH grip contact surface missing')
            distance=panel['distance_to_edge'][index]
            t=min(1.,distance/.0012);fade=t*t*(3-2*t)
            offset=.000035 if back else .000090+.000150*fade
            position=Vector((hit.x+side*offset,y,z))
            V.append(frame@position)
            # Orthogonal physical coordinates measured after boundary clipping.
            UV.append(((y-slope*z)/(.1*scale),(slope*y+z)/(.1*scale)))
    edge_count={};oriented={}
    for triangle in triangles:
        front=triangle if side>0 else triangle[::-1]
        F.append(tuple(base+i for i in front))
        F.append(tuple(base+count+i for i in front[::-1]))
        for a,b in zip(front,front[1:]+front[:1]):
            key=tuple(sorted((a,b)));edge_count[key]=edge_count.get(key,0)+1;oriented[key]=(a,b)
    for edge,n in edge_count.items():
        if n==1:
            a,b=oriented[edge];F.append((base+b,base+a,base+count+a,base+count+b))
    fits.append({k:panel[k] for k in ('side','source_faces','source_boundary_yz','boundary_yz','holes_yz','clearance_m','slope_y_from_z','cover_area_m2')})

mesh=bpy.data.meshes.new(name);mesh.from_pydata(V,[],F);mesh.update()
material=bpy.data.materials.new('M_pistol_grip_granular');material.diffuse_color=(.024,.024,.024,1)
material['unreal_material']='/Game/Weapons/PistolGripSurface20260927/Materials/M_pistol_grip_granular'
mesh.materials.append(material)
uv=mesh.uv_layers.new(name='UV0')
for face in mesh.polygons:
    face.use_smooth=True
    for li in face.loop_indices:uv.data[li].uv=UV[mesh.loops[li].vertex_index]
ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
ob['native_grip']='9_l: actual lateral palm outline with 0.8mm inset'
ob['surface_family']='pistol_grip_granular / pistol_grip_diamond / pistol_grip_quickdot'
ob['layer']='sealed backing; 0.09mm perimeter feathering to 0.24mm face offset'
references=bpy.data.collections.new('REFERENCE_OriginalRSH');bpy.context.scene.collection.children.link(references)
for part in parts:
    if part['name']=='10_l':continue
    data=bpy.data.meshes.new('Reference_'+part['name'])
    data.from_pydata([frame@Vector(v) for v in part['verts']],[],part['faces']);data.update()
    ref=bpy.data.objects.new(data.name,data);references.objects.link(ref)
    ref.hide_render=True;ref.hide_set(True);ref['reference_only']=True
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
(O/'Exports').mkdir(exist_ok=True)
fbx=O/'Exports'/(name+'.fbx');blend=O/'Exports'/(name+'_Editable.blend')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
record=dict(name=name,mesh='/Game/Weapons/RSH12/GripSurfaces20261004/'+name,fbx=str(fbx),blend=str(blend),
    source=inputs['source'],source_part='9_l',frame='native component reference; inverse WPN_root bind chain at runtime',
    root_matrix=[list(r) for r in root],canonical_to_component_m=[list(r) for r in frame],
    alignment=[list(r) for r in alignment],bone='WPN_root',fits=fits,
    triangles=sum(len(f.vertices)-2 for f in mesh.polygons),texture_tile_m=.1,
    uv_mapping='UV0 orthogonal YZ coordinates aligned to the native grip rake, from final clipped positions',
    layer_m=dict(back=.000035,edge=.000090,face=.000240,feather_width=.0012),
    materials={key:'/Game/Weapons/PistolGripSurface20260927/Materials/M_'+key for key in
        ('pistol_grip_granular','pistol_grip_diamond','pistol_grip_quickdot')},
    native_mesh_changed=False,hand_pose_changed=False,shared_materials_changed=False,
    provenance='Derived from RSH-12 by Medji; existing Docs/ThirdParty/RSH12-Medji-CCBY4.md attribution applies',
    runtime_tested=False,acceptance_rendered=False)
(O/'authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('RSH_GRIP_SURFACE_AUTHORED',record['triangles'],flush=True)
