"""Fit existing attachment geometry to QBZ interfaces and split factory sections."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;I=json.loads((O/'geometry_inputs.json').read_text());sources=json.loads((O/'sources.json').read_text())
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191ContactWear20260913/QBZ191_ContactWear_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];low=bpy.data.collections['QBZ_LOW'];r.data.pose_position='REST';bpy.context.view_layer.update()
root=r.data.bones['WPN_root'].matrix_local.copy();rootInv=root.inverted();mag0=Matrix(I['qbz']['mag0'])
bindings={};auth={'parts':{},'factory_sections':{},'source':'ContactWear20260913'}
for name in ['QBZ_Stock','QBZ_Part12']:
 ob=bpy.data.objects[name];original=ob.data.materials[0];mat=original.copy();mat.name='M_QBZ191_FactoryStock_'+('Polymer' if name=='QBZ_Stock' else 'Metal')
 ob.data.materials[0]=mat;bindings[mat.name]=original.name;auth['factory_sections'][name]=mat.name
barrel=bpy.data.objects['QBZ_Part19'];original=barrel.data.materials[0];flash=original.copy();flash.name='M_QBZ191_Flash_Hider';barrel.data.materials.append(flash);bindings[flash.name]=original.name
for face in barrel.data.polygons:
 if sum((rootInv@barrel.data.vertices[v].co).y for v in face.vertices)/len(face.vertices)<-.5005:face.material_index=1
auth['factory_sections']['muzzle']={'object':barrel.name,'material':flash.name,'section_cut_y_m':-.5005}
attachment_col=bpy.data.collections.new('QBZ_FITTED_ATTACHMENTS');s.collection.children.link(attachment_col)
for ob in bpy.context.view_layer.objects:
 if ob.type=='MESH':ob.hide_set(True)

def activate(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def export(ob,name):
 activate([ob]);bpy.ops.export_scene.fbx(filepath=str(O/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
def importpart(key):
 before=set(s.objects);bpy.ops.import_scene.fbx(filepath=sources[key]['fbx']);obs=[ob for ob in s.objects if ob not in before and ob.type=='MESH']
 for ob in obs:
  ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
  for c in list(ob.users_collection):c.objects.unlink(ob)
  attachment_col.objects.link(ob)
 activate(obs)
 if len(obs)>1:bpy.ops.object.join()
 ob=bpy.context.object;mapping={}
 for idx,mat in enumerate(list(ob.data.materials)):
  replacement=mat.copy();replacement.name='QBZ_SRC_'+key+'_'+str(idx);ob.data.materials[idx]=replacement
  mapping[replacement.name]=sources[key]['slots'][idx]
 return ob,mapping
def cube(name,center,size,mat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.name=name;ob.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(mat)
 be=ob.modifiers.new('Machined adapter edges','BEVEL');be.width=.0005;be.segments=3;be.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=be.name)
 return ob
adapter=bpy.data.materials.new('QBZ_AdapterMetal');adapter.diffuse_color=(.028,.032,.036,1)
for key in ['skeleton','qr_performance']:
 ob,mapping=importpart(key);minimum=min(v.co.x for v in ob.data.vertices)
 # Shared stock dimensions stay intact; only the receiver adapter is new.
 transform=Matrix.Translation((.000688,.065,.0615))@Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Translation((-minimum,0,0))
 ob.data.transform(transform)
 a=cube('QBZ receiver adapter',(.000688,.0585,.0615),(.034,.014,.042),adapter)
 # A shallow sleeve seats over the existing receiver tail and meets the stock.
 lip=cube('QBZ adapter shoulder',(.000688,.0645,.0615),(.029,.006,.033),adapter)
 activate([a,lip,ob]);bpy.context.view_layer.objects.active=ob;bpy.ops.object.join()
 ob.name='SM_QBZ191_'+key;mapping['QBZ_AdapterMetal']={'slot':'AdapterMetal','material':None,'class':'authored'}
 export(ob,ob.name);ob.hide_set(True);ob.hide_render=True
 auth['parts'][key]={'name':ob.name,'file':str(O/(ob.name+'.fbx')),'bindings':mapping,'bone':'WPN_root','mount':'identity_cm_mesh','shared_scale':1.,'receiver_plane_y_m':.0557}

base=Vector((.000759,-.500835,.060775))
for key in ['suppressor','brake','titanium_brake']:
 ob,mapping=importpart(key);length=max(v.co.y for v in ob.data.vertices)
 ob.data.transform(Matrix.Translation(base)@Matrix.Rotation(math.pi,4,'Z'));ob.name='SM_QBZ191_'+key
 export(ob,ob.name);ob.hide_set(True);ob.hide_render=True
 auth['parts'][key]={'name':ob.name,'file':str(O/(ob.name+'.fbx')),'bindings':mapping,'bone':'WPN_root','mount':'identity_cm_mesh','tip_ue_cm':[base.x*100,(-base.y+length)*100,base.z*100],'axis_ue':[0,1,0]}

ob,mapping=importpart('drum');donorRoot=Matrix(I['donor']['root_rest']);toRoot=donorRoot.inverted()
raw=[toRoot@v.co for v in ob.data.vertices];top=max(v.z for v in raw);neck=[v for v in raw if v.z>top-.012]
qbzmag=bpy.data.objects['QBZ_Magazine'];r.data.pose_position='POSE';a=bpy.data.actions['QBZ191_base_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
MI=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['WPN_SOCKET_Magazine'].matrix@r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()
targetverts=[MI@v.co for v in qbzmag.data.vertices];targetTop=max(v.z for v in targetverts);targetNeck=[v for v in targetverts if v.z>targetTop-.012]
def midpoint(pts,axis):return (min(v[axis] for v in pts)+max(v[axis] for v in pts))*.5
delta=Vector((midpoint(targetNeck,0)-midpoint(neck,0),midpoint(targetNeck,1)-midpoint(neck,1),targetTop-top))
toQBZ=Matrix.Translation(delta)@toRoot
sx=(max(v.x for v in targetNeck)-min(v.x for v in targetNeck))/(max(v.x for v in neck)-min(v.x for v in neck))
sy=(max(v.y for v in targetNeck)-min(v.y for v in targetNeck))/(max(v.y for v in neck)-min(v.y for v in neck))
cx=midpoint(neck,0);cy=midpoint(neck,1)
for v,point in zip(ob.data.vertices,raw):
 t=max(0,min(1,(point.z-(top-.050))/.025));t=t*t*(3-2*t)
 point.x=cx+(point.x-cx)*(1+(sx-1)*t);point.y=cy+(point.y-cy)*(1+(sy-1)*t)
 v.co=mag0.inverted()@(point+delta)
ob.name='SM_QBZ191_drum';export(ob,ob.name);ob.hide_set(True);ob.hide_render=True
auth['parts']['drum']={'name':ob.name,'file':str(O/(ob.name+'.fbx')),'bindings':mapping,'bone':'WPN_SOCKET_Magazine','mount':'identity_cm_mesh','asset_to_qbz_root':rows(toQBZ) if False else [list(v) for v in toQBZ],'neck_xy_scale':[sx,sy],'body_scale':1.,'grasp_in_mag':[list(v) for v in mag0.inverted()@toQBZ@Matrix(I['donor']['grasp_in_asset'])]}
auth['gun_bindings']=bindings
r.data.pose_position='REST';bpy.context.view_layer.update()
sys.path.insert(0,str(S/'QBZ191Hero20260913'));from export_mesh import export_joined
objects=[x for x in low.objects if x.type=='MESH' and not x.get('is_static_head')]
export_joined(r,bpy.data.objects['SK_Manny_Arms_Export'],objects,O)
r.data.pose_position='POSE';s.frame_set(0)
for x in low.objects:x.hide_set(False);x.hide_render=False
bpy.data.objects['SK_Manny_Arms_Export'].hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Attachments_Editable.blend'))
(O/'models.json').write_text(json.dumps(auth,indent=2));print('QBZ_ATTACHMENT_MODELS_EXPORTED',flush=True)
