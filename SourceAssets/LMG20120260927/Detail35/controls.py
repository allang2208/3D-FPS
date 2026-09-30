"""Refine existing moving control sections without changing their bind pose."""
import bpy,bmesh,json,math
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/Body.fbx'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data_clear();rig.data.pose_position='REST'
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');names=['M_LMG201_ReceiverReferenceHardware','M_LMG201_ReceiverReferenceRail'];keep={i for i,m in enumerate(ob.data.materials) if m.name in names}
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in keep],context='FACES');bm.to_mesh(ob.data);bm.free()
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
# Preserve the current slider, folding lever, grip ridges and hinge cap. Radius
# is in the source object's metres and only affects still-sharp edges.
bpy.ops.mesh.customdata_custom_splitnormals_clear()
bevel=ob.modifiers.new('Control edge polish','BEVEL');bevel.width=.00012;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(52);bevel.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=bevel.name)
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for f in bm.faces:f.smooth=True
for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(42)
bm.to_mesh(ob.data);bm.free()
weighted=ob.modifiers.new('Control planar normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=40;bpy.ops.object.modifier_apply(modifier=weighted.name)
for i in keep:
 satin='Hardware' in ob.data.materials[i].name;m=bpy.data.materials.new('M_LMG201_D35_ControlSatin' if satin else 'M_LMG201_D35_ControlCoat');m.use_nodes=True
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Base Color'].default_value=(*((.040,.046,.052) if satin else (.021,.026,.031)),1);bs.inputs['Metallic'].default_value=.78 if satin else .35;bs.inputs['Roughness'].default_value=.42 if satin else .58;bs.inputs['Specular IOR Level'].default_value=.28;ob.data.materials[i]=m
bpy.ops.object.material_slot_remove_unused();ob.name='LMG201_D35_NativeControls';rig.select_set(True)
out=O/'Exports/SK_LMG201_D35_Controls.fbx';bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_D35_Controls.blend'))
report={'export':str(out),'replaces_slots':names,'preserved':'existing geometry profile, UV and animated bone ownership','changes':'small edge radius, coherent split/weighted normals, dedicated clean coating/satin finish'}
(O/'controls.json').write_text(json.dumps(report,indent=2));print('DETAIL35_CONTROLS_SAVED',flush=True)
