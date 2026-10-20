"""Detailed diopter/hooded-post rebuild. All non-sight geometry stays untouched."""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;B=O.parent;P=O.parents[2]
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(B/'SVCH_Replacement_Editable.blend'),load_ui=False)
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';rig.animation_data_clear()
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
def signature(ob):
 h=hashlib.sha256();me=ob.data
 h.update(np.asarray([tuple(v.co) for v in me.vertices],dtype='<f4').tobytes());h.update(str([tuple(p.vertices) for p in me.polygons]).encode())
 for uv in me.uv_layers:h.update(np.asarray([tuple(x.uv) for x in uv.data],dtype='<f4').tobytes())
 h.update(str([[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in me.vertices]).encode());return h.hexdigest()
old_sights=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m and m.name=='SVCH_New_FactorySights' for m in o.data.materials)]
protected={o.name:signature(o) for o in bpy.context.scene.objects if o.type=='MESH' and o not in old_sights}
for ob in old_sights:bpy.data.objects.remove(ob,do_unlink=True)
mat=bpy.data.materials.get('SVCH_New_FactorySights')
if mat and mat.users==0:bpy.data.materials.remove(mat)
with bpy.data.libraries.load(str(P/'SourceAssets/HK416SlapSights20261001/HK416_ModularSights_Editable.blend'),link=False) as (a,b):b.objects=['ironsight_low']
source=b.objects[0];sm=source.data;source_mat=sm.materials[0];mat=source_mat.copy();mat.name='SVCH_New_FactorySights'
texture_dir=P/'SourceAssets/HK416Reworked20260930/Original/textures'
nodes=mat.node_tree.nodes;nodes.clear();lk=mat.node_tree.links;bs=nodes.new('ShaderNodeBsdfPrincipled');outnode=nodes.new('ShaderNodeOutputMaterial');lk.new(bs.outputs['BSDF'],outnode.inputs['Surface'])
textures={}
for kind in ('albedo','metallic','roughness','normal','AO'):
 path=texture_dir/('Upper_Body_'+kind+('.png' if kind=='normal' else '.jpg'));node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(path),check_existing=True);node.image.colorspace_settings.name='sRGB' if kind=='albedo' else 'Non-Color';textures[kind]=node
color=nodes.new('ShaderNodeMixRGB');color.blend_type='MULTIPLY';color.inputs[0].default_value=1.;color.inputs[2].default_value=(.7,.7,.7,1);lk.new(textures['albedo'].outputs['Color'],color.inputs[1]);lk.new(color.outputs[0],bs.inputs['Base Color'])
rough=nodes.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.inputs[1].default_value=.4;rough.inputs[2].default_value=.28;lk.new(textures['roughness'].outputs['Color'],rough.inputs[0]);lk.new(rough.outputs[0],bs.inputs['Roughness'])
metal=nodes.new('ShaderNodeMath');metal.operation='MULTIPLY';metal.inputs[1].default_value=.5;lk.new(textures['metallic'].outputs['Color'],metal.inputs[0]);lk.new(metal.outputs[0],bs.inputs['Metallic'])
nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.85;lk.new(textures['normal'].outputs['Color'],nm.inputs['Color']);lk.new(nm.outputs[0],bs.inputs['Normal'])
(O/'material_recipe.json').write_text(json.dumps({'source_texture_root':'/Game/Weapons/HK416/Reworked20260930/Textures/T_HK416_Upper_Body_','source_files':{k:n.image.filepath for k,n in textures.items()},'color_multiplier':.7,'metallic_multiplier':.5,'roughness_scale':.4,'roughness_offset':.28,'normal_strength':.85},indent=2))
measure=json.loads((O/'donor_measurements.json').read_text());D=np.array(measure['donor_to_source_cm']);raw=np.array([tuple(v.co) for v in sm.vertices]);s=(np.c_[raw,np.ones(len(raw))]@D.T)[:,:3]
hold=json.loads((P/'SourceAssets/SVCHSketchfab20261017/Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm'])
def component(n):
 n=np.asarray(n);return np.stack((n[...,0]-18.7444,n[...,2]-1.5268,n[...,1]),axis=-1)@HR.T+HT
def bpos(n):return component(n)*[.01,-.01,.01]
old_receipt=json.loads((B/'authoring_receipt.json').read_text());rail=old_receipt['rail_top_native_cm'];height=rail+3.1
def to_native(comp):
 g=(np.asarray(comp)-HT)@HR;return np.array([g[0]+18.7444,g[2],g[1]+1.5268])
targets={label:to_native(old_receipt['landmarks_component_cm'][key])[0] for label,key in [('rear','RearSight'),('front','FrontSight')]}
rear_eye=np.array(measure['rear_center_source_cm']);front_top=s[(raw[:,1]>.3)&(abs(s[:,0])<.15)&(s[:,2]>14.5093)].mean(0)
seat={'rear':11.886,'front':11.934};extra=3.1-(front_top[2]-seat['front']);normal=np.array([tuple(n.vector) for n in sm.corner_normals]);source_loops=np.array([l.vertex_index for l in sm.loops])
def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
def warp(p,label):
 out=p.copy()
 if label=='front':out[:,2]+=extra*smooth((p[:,2]-13.65)/.55)*(1-smooth((abs(p[:,0])-.15)/.12))
 return out
report={'source':'HK416 detailed factory diopter and hooded post','source_blend':'SourceAssets/HK416SlapSights20261001/HK416_ModularSights_Editable.blend','parts':{},'unchanged_mesh_signatures':protected,'sight_height_above_rail_cm':3.1,'front_post_extension_cm':float(extra),'source_profile_preserved':True,'V9_preserved':True,'animations_modified':False}
new=[]
for label in ('rear','front'):
 polys=[p for p in sm.polygons if (raw[p.vertices[0],1]<.3)==(label=='rear')];ids=sorted({i for p in polys for i in p.vertices});idx={v:i for i,v in enumerate(ids)};verts=s[ids];p=warp(verts,label)
 anchor=rear_eye if label=='rear' else front_top
 n=np.column_stack((p[:,1]-anchor[1]+targets[label],-(p[:,0]-anchor[0]),p[:,2]-seat[label]+rail))
 if label=='rear':n[:,2]+=3.1-(rear_eye[2]-seat[label])
 me=bpy.data.meshes.new('Detailed_'+label);me.from_pydata(bpos(n).tolist(),[],[[idx[i] for i in p.vertices] for p in polys]);me.update();me.materials.append(mat)
 for p0,p1 in zip(polys,me.polygons):p1.use_smooth=p0.use_smooth
 for layer in sm.uv_layers:
  uv=me.uv_layers.new(name=layer.name)
  for p0,p1 in zip(polys,me.polygons):
   for l0,l1 in zip(p0.loop_indices,p1.loop_indices):uv.data[l1].uv=layer.data[l0].uv
 # Preserve original split normals across rigid fitting and the post extension.
 lin=np.column_stack([bpos(np.eye(3)[i])-bpos([0,0,0]) for i in range(3)])@np.array([[0,1,0],[-1,0,0],[0,0,1]])
 jac=np.empty((len(verts),3,3));eps=1e-4
 for axis in range(3):
  delta=np.eye(3)[axis]*eps;jac[:,:,axis]=(warp(verts+delta,label)-warp(verts-delta,label))/(2*eps)
 inverse=np.linalg.inv(np.einsum('ij,njk,kl->nil',lin,jac,D[:3,:3])).transpose(0,2,1);normals=[]
 for p0 in polys:
  for l in p0.loop_indices:
   a=inverse[idx[source_loops[l]]]@normal[l];normals.append(a/max(np.linalg.norm(a),1e-12))
 me.normals_split_custom_set(normals);ob=bpy.data.objects.new('SVCH_Detailed_'+label,me);bpy.context.scene.collection.objects.link(ob);ob.parent=rig;ob.vertex_groups.new(name='WPN_root').add(list(range(len(me.vertices))),1.,'REPLACE');ob.modifiers.new('RigidRoot','ARMATURE').object=rig;new.append(ob);me.calc_loop_triangles()
 report['parts'][label]={'vertices':len(me.vertices),'triangles':len(me.loop_triangles),'bounds_native_cm':[n.min(0).tolist(),n.max(0).tolist()],'eye_native_cm':[targets[label],0.,height]}
bpy.data.objects.remove(source,do_unlink=True)
for name,digest in protected.items():
 if signature(bpy.data.objects[name])!=digest:raise RuntimeError('Non-sight geometry changed: '+name)
landmarks=dict(old_receipt['landmarks_component_cm']);landmarks['RearSight']=component([targets['rear'],0,height]).tolist();landmarks['FrontSight']=component([targets['front'],0,height]).tolist();report['landmarks_component_cm']=landmarks
bpy.ops.object.select_all(action='DESELECT');export=[o for o in bpy.context.scene.objects if o.type=='MESH']
for ob in [rig]+export:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=rig;bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVCH_SightsR2_Editable.blend'))
# Export a single skinned mesh to avoid FBX's per-object bind-pose ambiguity.
copies=[]
for ob in export:
 c=ob.copy();c.data=ob.data.copy();bpy.context.scene.collection.objects.link(c);copies.append(c)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();combined=bpy.context.object;combined.name='SVCH_SightsR2_Combined';rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_SVCH_SightsR2.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
report['export']='single mesh, shared rig, no animation export';report['sight_triangles']=sum(r['triangles'] for r in report['parts'].values());(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2));print('SIGHTS_R2_AUTHORED',report['sight_triangles'],flush=True)
