"""Extract the selected package optic without changing its topology or UV."""
import bpy,json,gzip,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1]
B=P/'SourceAssets/SVCHReplacement20261018'
S=B/'Download/Extracted/Original/Native/KVInhibitor'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'KV Inhibitor.blend'),load_ui=False)
ob=bpy.data.objects['other\\sight_scope.smd']
for other in list(bpy.data.objects):
    if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
inventory=json.loads((B/'source_inventory.json').read_text());world=Matrix(next(x['matrix'] for x in inventory['objects'] if x['name']=='other\\sight_scope.smd'))
ob.parent=None;ob.matrix_world=Matrix.Identity(4)
for mod in list(ob.modifiers):ob.modifiers.remove(mod)
ob.data=ob.data.copy();ob.data.transform(world)
# Picatinny rail crown comes from the same original rifle's source assembly.
# Source muzzle is -X, source right is +Y. UE optical frame: +X forward.
scale=7.6000190034954285;anchor=1.50;rail=2.3927176
T=Matrix(((-scale*.01,0,0,anchor*scale*.01),(0,-scale*.01,0,0),(0,0,scale*.01,-rail*scale*.01),(0,0,0,1)))
ob.data.transform(T);ob.name='SM_KVScope_Common';ob.vertex_groups.clear()
for slot in ob.data.materials:
    slot.use_nodes=True;n=slot.node_tree.nodes;n.clear();lk=slot.node_tree.links
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');lk.new(bs.outputs[0],out.inputs[0])
    if slot.name.startswith('att_lens'):
        bs.inputs['Base Color'].default_value=(.015,.06,.09,1);bs.inputs['Roughness'].default_value=.08;bs.inputs['Metallic'].default_value=.25
    else:
        bs.inputs['Roughness'].default_value=.42;bs.inputs['Metallic'].default_value=.45
        color=n.new('ShaderNodeTexImage');color.image=bpy.data.images.load(str(S/'KVInhibitor_sight_scope.png'),check_existing=True);lk.new(color.outputs['Color'],bs.inputs['Base Color'])
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(S/'KVInhibitor_sight_scope_n.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
        sep=n.new('ShaderNodeSeparateXYZ');iv=n.new('ShaderNodeMath');iv.operation='SUBTRACT';iv.inputs[0].default_value=1;comb=n.new('ShaderNodeCombineXYZ');nm=n.new('ShaderNodeNormalMap')
        lk.new(tex.outputs['Color'],sep.inputs[0]);lk.new(sep.outputs['X'],comb.inputs['X']);lk.new(sep.outputs['Y'],iv.inputs[1]);lk.new(iv.outputs[0],comb.inputs['Y']);lk.new(sep.outputs['Z'],comb.inputs['Z']);lk.new(comb.outputs[0],nm.inputs['Color']);lk.new(nm.outputs[0],bs.inputs['Normal'])
ob.data.calc_loop_triangles();v=np.array([list(v.co) for v in ob.data.vertices])*[100,-100,100]
glass=np.unique([i for p in ob.data.polygons if ob.data.materials[p.material_index].name.startswith('att_lens') for i in p.vertices]);gv=v[glass]
# Separate ocular/objective discs by their axial midpoint, not body bounds.
rear=gv[gv[:,0]<(gv[:,0].min()+gv[:,0].max())*.5];front=gv[gv[:,0]>=(gv[:,0].min()+gv[:,0].max())*.5]
def center(p):return ((p.min(0)+p.max(0))*.5).tolist()
data={'positions':v.tolist(),'triangles':[list(t.vertices) for t in ob.data.loop_triangles],'material_ids':[t.material_index for t in ob.data.loop_triangles],'materials':[m.name for m in ob.data.materials]}
report={'source_object':'other\\sight_scope.smd','source_package':str(S/'KV Inhibitor.blend'),'vertices':len(v),'triangles':len(data['triangles']),'bounds_cm':[v.min(0).tolist(),v.max(0).tolist()],'SightRear':center(rear),'SightFront':center(front),'rail_plane_z':0.,'source_model_number_confirmed':False,'source_texture_markings':'Cyrillic elevation/windage text and stylized logo; no unambiguous model plate','topology_uv_custom_normals_preserved':True}
with gzip.open(O/'source_geometry.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
(O/'source_report.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.fbx(filepath=str(O/'SM_KVScope_Common.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world.color=(.24,.24,.24);scene.view_settings.view_transform='AgX'
def area(name,pos,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.035))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-.15,-.25,.35),30,.3);area('Fill',(.15,.3,.2),20,.3);area('Rim',(-.2,.05,.3),20,.2)
camera=bpy.data.objects.new('SourceStudyCamera',bpy.data.cameras.new('SourceStudyCamera'));scene.collection.objects.link(camera);camera.location=(-.30,-.42,.19);target=Vector((-.025,0,.035));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.31;scene.camera=camera
scene.render.film_transparent=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'KVScope_Source_Editable.blend'))
scene.render.filepath=str(O/'source_scope_study.png');bpy.ops.render.render(write_still=True)
print('KV_SCOPE_SOURCE_PREPARED',json.dumps(report),flush=True)
