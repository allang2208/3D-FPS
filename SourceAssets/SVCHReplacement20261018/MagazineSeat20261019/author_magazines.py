"""Original standard/extended shells in the installed SVCh socket frame."""
import bpy,json,gzip
import numpy as np
from pathlib import Path
from mathutils import Matrix

O=Path(__file__).parent;BASE=O.parent
SOURCE=BASE/'Download/Extracted/Original/Native/KVInhibitor'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(BASE/'RealSights20261019/SVCH_RealFoldingSights_Editable.blend'),load_ui=False)
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';rig.animation_data_clear()
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
standard=bpy.data.objects['SVCH_New_mag'];bullets=bpy.data.objects['SVCH_New_bullets']
inventory=json.loads((BASE/'source_inventory.json').read_text())
matrices={x['name']:np.array(x['matrix']) for x in inventory['objects']}
with bpy.data.libraries.load(str(SOURCE/'KV Inhibitor.blend'),link=False) as (_,data):
    data.objects=['other\\mag_extended.smd']
extended=data.objects[0];bpy.context.scene.collection.objects.link(extended)
SN=np.asarray(json.loads((BASE/'registration.json').read_text())['source_to_previous_native'])
hold=json.loads((BASE.parent/'SVCHSketchfab20261017/Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm'])
def comp(n):
    n=np.asarray(n);g=np.stack((n[...,0]-18.7444,n[...,2]-1.5268,n[...,1]),axis=-1);return g@HR.T+HT
def bpos(n):return comp(n)*[.01,-.01,.01]
T=np.eye(4);T[:3,3]=bpos(SN[:3,3]);T[:3,:3]=np.column_stack([bpos(SN[:3,3]+SN[:3,i])-T[:3,3] for i in range(3)])
# The download displays its alternate magazine below the rifle. Both object
# transforms share rotation/scale; remove that explicit display translation.
EM=matrices['other\\mag_extended.smd'].copy();SM=matrices['other\\mag.smd']
display=EM[:3,3]-SM[:3,3];EM[:3,3]=SM[:3,3]
extended.data=extended.data.copy();extended.data.transform(Matrix(T@EM))
extended.parent=None;extended.matrix_world=Matrix.Identity(4)
for mod in list(extended.modifiers):extended.modifiers.remove(mod)
extended.vertex_groups.clear()
extended.name='SVCH_SourceExtendedMagazine'
# Keep the supplied UV and both source maps for the extended polymer shell.
for mat in extended.data.materials:
    mat.name='KVInhibitor_mag_extended';mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links=mat.node_tree.links
    links.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Roughness'].default_value=.45;bs.inputs['Metallic'].default_value=0.
    for kind,suffix in [('color',''),('normal','_n')]:
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(SOURCE/('KVInhibitor_mag_extended'+suffix+'.png')),check_existing=True)
        if kind=='color':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        else:
            tex.image.colorspace_settings.name='Non-Color';sep=nodes.new('ShaderNodeSeparateXYZ');comb=nodes.new('ShaderNodeCombineXYZ');inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1.;normal=nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['X'],comb.inputs['X']);links.new(sep.outputs['Y'],inv.inputs[1]);links.new(inv.outputs[0],comb.inputs['Y']);links.new(sep.outputs['Z'],comb.inputs['Z']);links.new(comb.outputs[0],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
C=np.diag([100.,-100.,100.,1.]);CI=np.linalg.inv(C)
seat=np.array(json.loads((O/'seat_calibration.json').read_text())['static_socket_from_visual_cm'])
payload={};report={'source_master':str(BASE/'RealSights20261019/SVCH_RealFoldingSights_Editable.blend'),'extended_source':str(SOURCE/'KV Inhibitor.blend'),'removed_extended_display_translation':display.tolist(),'socket':'WPN_SOCKET_Magazine','runtime_relative_scale':.01,'native_V9_written':False,'source_topology_uv_normals_preserved':True,'meshes':{}}
for label,shell in [('Magazine10',standard),('Magazine20',extended)]:
    copies=[];visual=[];tris=[];offset=0
    for original in (shell,bullets):
        ob=original.copy();ob.data=original.data.copy();bpy.context.scene.collection.objects.link(ob)
        M=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.transform(M)
        for mod in list(ob.modifiers):ob.modifiers.remove(mod)
        ob.vertex_groups.clear();ob.data.calc_loop_triangles()
        v=np.array([list(p.co) for p in ob.data.vertices])*[100.,-100.,100.]
        visual.extend(v.tolist());tris.extend([[int(x)+offset for x in t.vertices] for t in ob.data.loop_triangles]);offset+=len(v)
        ob.data.transform(Matrix(CI@seat@C));copies.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in copies:ob.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();combined=bpy.context.object;combined.name='SM_SVCH_'+label
    combined['coordinate_frame']='installed magazine socket centimetres; runtime scale .01'
    combined.data.calc_loop_triangles()
    local=(np.array(visual)@seat[:3,:3].T+seat[:3,3]).tolist()
    payload[label]={'visual_component_cm':visual,'socket_cm':local,'triangles':tris}
    bpy.ops.export_scene.fbx(filepath=str(O/(combined.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
    report['meshes'][label]={'fbx':combined.name+'.fbx','vertices':len(visual),'triangles':len(tris),'materials':[m.name for m in combined.data.materials]}
    combined.hide_set(True);combined.hide_render=True
extended.hide_set(True);extended.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVCH_MagazineSeat_Editable.blend'))
with gzip.open(O/'magazine_geometry.json.gz','wt') as f:json.dump(payload,f,separators=(',',':'))
(O/'model_receipt.json').write_text(json.dumps(report,indent=2))
print('SVCH_MAGAZINES_EXPORTED',json.dumps(report['meshes']),flush=True)
