"""Current 201 grip interfaces and material-ready authored surfaces."""
from pathlib import Path
O=Path(__file__).parent;S=O.parent
helpers=(S/'Assembly40/model.py').read_text().split('# Preserve the edited receiver')[0]
helpers=helpers.replace('HardSurface39/LMG201_HardSurface39.blend','SurfaceReform42/LMG201_SurfaceReform42.blend').replace(".replace('M_LMG201_R38_','M_LMG201_A40_')",".replace('M_LMG201_R38_','M_LMG201_G43_')")
exec(compile(helpers,str(O/'model.py'),'exec'),globals())
previous=json.loads((S/'SurfaceReform42/model.json').read_text());parts=[bpy.data.objects[n] for n in previous['parts']];report={}
poly=material('Polymer');coat.name='M_LMG201_G43_EdgeCoat';poly.name='M_LMG201_G43_GripPolymer'

def colors(ob):
 me=ob.data;me.update();attr=me.color_attributes.get('G43FinishRegions') or me.color_attributes.new(name='G43FinishRegions',type='FLOAT_COLOR',domain='CORNER');me.color_attributes.active_color=attr;me.color_attributes.render_color_index=list(me.color_attributes).index(attr)
 xf=root.inverted()@ob.matrix_world if ob.parent==rig else Matrix.Identity(4)
 for p in me.polygons:
  n=(xf.to_3x3().inverted().transposed()@p.normal).normalized();bevel=.5 if p.area<.000009 and max(abs(x) for x in n)<.995 else 0
  for i in p.loop_indices:attr.data[i].color=(bevel,0,0,1)

for n in ['ReceiverSideSkins_S42','TriggerGuard_S42']:
 ob=bpy.data.objects[n]
 for i,m in enumerate(ob.data.materials):
  if m.name=='M_LMG201_S42_Cover':ob.data.materials[i]=coat
 colors(ob)
lid=bpy.data.objects['TopCover_ReferenceRepair38'];lidcoat=coat.copy();lidcoat.name='M_LMG201_G43_LidCoat'
for i,m in enumerate(lid.data.materials):
 if m.name=='M_LMG201_R38_Cover':lid.data.materials[i]=lidcoat
colors(lid);parts.append(lid)

def collar(name):
 # Continuous shoulder from the upper grip body into the receiver web. The
 # forward return overlaps the S42 guard seat while retaining the trigger hole.
 rows=[]
 for y,w,bottom,top in [(-.0125,.0115,-.0105,.0048),(-.009,.0144,-.012,.0060),(.029,.0155,-.012,.0060),(.040,.0130,-.010,.0050),(.045,.0105,-.007,.0035)]:
  rows.append((y,[(cx-w,bottom),(cx-w,top-.0012),(cx-w+.0012,top),(cx+w-.0012,top),(cx+w,top-.0012),(cx+w,bottom)]))
 return loft(name,rows,poly,.00045)

factory=bpy.data.objects['PistolGrip'];localize(factory)
# Preserve the original grip silhouette/UVs; its visible shoulder is replaced
# with a continuous polymer return instead of a floating metal plate.
factory_mat=bpy.data.materials.new('M_LMG201_G43_FactoryGrip');factory.data.materials[0]=factory_mat
facpart=collar('G43_FactoryGripSeat');bind(facpart,'WPN_root');bind(factory,'WPN_root');parts+=[factory,facpart]
factory.name='PistolGrip_G43';facpart.name='FactoryGripSeat_G43'

# Use measured contact-section centrelines, not the overall object bounds.
factory_data=np.load(O/'factory.npz')['v'];zs=np.array([-.095,-.080,-.065,-.050,-.035,-.020,-.010])
target=[]
for z in zs:
 band=factory_data[abs(factory_data[:,2]-z)<.004];target.append(float((np.quantile(band[:,1],.04)+np.quantile(band[:,1],.96))*.5))
paths={}
for key in ['stable','balanced','phantom']:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('Before_'+key+'.fbx')),use_anim=False);added=set(bpy.data.objects)-old
 ob=max((q for q in added if q.type=='MESH' and not q.name.startswith(('UCX_','UBX_'))),key=lambda q:len(q.data.vertices));xf=ob.matrix_world.copy();me=ob.data;norm=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in me.corner_normals];me.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);me.normals_split_custom_set(norm)
 # Slot zero is the old common mount, confirmed by the per-asset slot capture.
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==0],context='FACES');bm.to_mesh(me);bm.free();me.update()
 original=np.array([v.co[:] for v in me.vertices]);sources=[]
 for z in zs:
  q=original[abs(original[:,2]-z)<.004];sources.append(float((np.quantile(q[:,1],.04)+np.quantile(q[:,1],.96))*.5))
 delta=np.array(target)-np.array(sources)
 def mapped(p):
  x,y,z=p;w=float(np.clip((-z-.010)/.012,0,1)*np.clip((z+.117)/.014,0,1));dy=float(np.interp(z,zs,delta));return np.array([cx+(x-cx)*(1+.22*w),y+dy*w,z])
 oldnorm=[n.vector.copy() for n in me.corner_normals]
 matrices=[]
 for i,v in enumerate(me.vertices):
  p=original[i];e=.00001;J=np.column_stack([(mapped(p+np.eye(3)[k]*e)-mapped(p-np.eye(3)[k]*e))/(2*e) for k in range(3)]);matrices.append(Matrix(J.tolist()).inverted().transposed());v.co=mapped(p)
 me.update();me.normals_split_custom_set([(matrices[l.vertex_index]@n).normalized() for l,n in zip(me.loops,oldnorm)])
 # New head gets its own UV; source grip UV and corner normals are retained.
 head=joined('G43_'+key+'_Seat',[collar('G43_'+key+'_ReceiverReturn')],None);select([ob,head]);bpy.context.view_layer.objects.active=ob;bpy.ops.object.join();ob.name='RearGrip_'+key+'_G43'
 path=O/'Exports'/('SM_LMG201_G43_'+key+'.fbx');select([ob]);bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE');paths[key]=str(path)
 report[key]={'section_z_m':zs.tolist(),'section_center_delta_y_m':delta.tolist(),'contact_width_scale':1.22,'new_seat_top_m':.006}
 for q in added:
  if q!=ob and q.name in bpy.data.objects:bpy.data.objects.remove(q,do_unlink=True)
 ob.hide_render=True;ob.hide_set(True)
select(parts+[rig]);fbx=O/'Exports/SK_LMG201_G43_Parts.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_GripFinish43.blend'))
(O/'model.json').write_text(json.dumps({'body_fbx':str(fbx),'grip_fbx':paths,'parts':[o.name for o in parts],'interfaces':report,'factory_grip_top_before_m':-.00643666,'grip_seat_top_after_m':.006},indent=2));print('G43_MODEL_SAVED',flush=True)
