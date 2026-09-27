"""Skin the four retained wooden staves to one eleven-bone elastic rig."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
sections=json.loads((P.parent/'BowBodyVariants20260926/donor-inputs.json').read_text())['sections']
def center(z):
 for a,b in zip(sections,sections[1:]):
  if a['z']<=z<=b['z']:
   t=(z-a['z'])/(b['z']-a['z']);return Vector([sum(a['bounds'][j])*.5*(1-t)+sum(b['bounds'][j])*.5*t for j in [0,1]]+[z])
 raise ValueError(z)
rigdata=bpy.data.armatures.new('BowElasticSkeleton');rig=bpy.data.objects.new('Armature',rigdata);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
b=rigdata.edit_bones.new('bow_body_root');b.head=(0,0,0);b.tail=(0,0,4)
chains={};restpoints={}
for side,zs,tip in [('upper',[21.5,34,46.5,58.5],(-24.082,-.095,69.51)),('lower',[-22.593,-35.093,-47.593,-59.593],(-24.081,-.152,-70.598))]:
 points=[center(z) for z in zs]+[Vector(tip)];names=[side+'_%02d'%(i+1) for i in range(4)]+[side+'_tip'];chains[side]=names
 for i,n in enumerate(names):
  b=rigdata.edit_bones.new(n);b.head=points[i];b.tail=points[i+1] if i<4 else points[i]+Vector((0,0,1 if side=='upper' else -1))
  b.parent=rigdata.edit_bones[names[i-1] if i else 'bow_body_root'];restpoints[n]=list(b.head)
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
records=[]
sources=[('Original',P.parent/'BowModular20260926/Bow_ModularParts.blend','SM_Bow_BodyModular')]+[(k,P.parent/'BowBodyVariants20260926/Bow_ThreeBodies.blend','SM_Bow_Body_'+k) for k in ['Swift','Heavy','Steady']]
for name,path,objname in sources:
 with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[objname]
 o=b.objects[0];scene.collection.objects.link(o);o.name='SK_Bow_Flex_'+name
 o.data=o.data.copy();o.parent=rig
 # Normalize cached donor winding before attaching weights; preserve positions/UVs.
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 if o.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
 o.select_set(False)
 groups={n:o.vertex_groups.new(name=n) for n in ['bow_body_root']+list(restpoints)}
 for v in o.data.vertices:
  side='upper' if v.co.z>-.5465 else 'lower';names=chains[side]
  s=1 if side=='upper' else -1;a=s*v.co.z;zs=[s*restpoints[n][2] for n in names]
  if a<=zs[0]:weights={'bow_body_root':1}
  elif a<zs[0]+5:
   t=(a-zs[0])/5;t=t*t*(3-2*t);weights={'bow_body_root':1-t,names[0]:t}
  else:
   i=next((j for j in range(4) if a<zs[j+1]),4)
   if i==4:weights={names[4]:1}
   else:
    start=zs[i]+5 if i==0 else zs[i]
    t=max(0,min(1,(a-start)/(zs[i+1]-start)));t=t*t*(3-2*t)
    weights={names[i]:1-t,names[i+1]:t}
  for n,w in weights.items():
   if w>1e-6:groups[n].add([v.index],w,'REPLACE')
 mod=o.modifiers.new('Elastic wooden limbs','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
 bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);o.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
 records.append(dict(name=name,mesh=o.name,source=str(path),source_object=objname,materials=[m.name.split('.')[0] for m in o.data.materials],vertices=len(o.data.vertices),triangles=sum(len(f.vertices)-2 for f in o.data.polygons)))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ElasticBodies.blend'))
(P/'body-authoring.json').write_text(json.dumps(dict(assets=records,bones=['bow_body_root']+list(restpoints),bone_heads_blender_cm=restpoints,units='centimetres',source_geometry_uv_colors_preserved=True,gameplay_tested=False),indent=2),encoding='utf8')
print('BOW_ELASTIC_BODIES_AUTHORED',flush=True)
