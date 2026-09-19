"""Retopology fitted to the accepted 5080 reconstruction, author units in cm.
Preserve its measured open rear-frame silhouette. Separate fused details.
Each rifle exports its own UV atlas fit and receiver adapter, at the same size.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;P=R.parent;OLD=P.parent/'SkeletonStock20260912'
records={}
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def bevel(o,w=.055):
 active(o);m=o.modifiers.new('Defined edge radius','BEVEL');m.width=w;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
 for f in o.data.polygons:f.use_smooth=True
 m=o.modifiers.new('Planar face normals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)
 return o
def cube(name,loc,size,mat,w=.055):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);parts.append(o);return bevel(o,w)
def prism(name,profile,width,mat,w=.055):
 vs=[(x,y,z) for y in [-width/2,width/2] for x,z in profile];n=len(profile);fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat);parts.append(o);return bevel(o,w)
def tube(name,x0,x1,r,inner,z,mat):
 # Four profile loops form a closed annulus, with a continuous open passage.
 rings=[(x0,r),(x1,r),(x1,inner),(x0,inner)];N=96;vs=[(x,rr*math.cos(i*2*math.pi/N),z+rr*math.sin(i*2*math.pi/N)) for x,rr in rings for i in range(N)];fs=[]
 for j in range(4):
  for i in range(N):fs.append((j*N+i,j*N+(i+1)%N,((j+1)%4)*N+(i+1)%N,((j+1)%4)*N+i))
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat);parts.append(o);return bevel(o,.035)
def bolt(x,y,z,mat):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.22,depth=.12,location=(x,y,z),rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='Recessed_hex_fastener';o.data.materials.append(mat);parts.append(o)
 bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.105,depth=.09,location=(x,y+math.copysign(.045,y),z),rotation=(math.pi/2,0,0));cut=bpy.context.object;active(o);m=o.modifiers.new('Hex socket recess','BOOLEAN');m.operation='DIFFERENCE';m.object=cut;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True);bevel(o,.017)
def hole(o,profile):
 cut=prism('Window_cut',profile,5,metal,.15);parts.remove(cut);active(o);m=o.modifiers.new('Open frame window','BOOLEAN');m.operation='DIFFERENCE';m.object=cut;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True)
def simple(name,color,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;return m
for key in ['m4','akm']:
 bpy.ops.wm.open_mainfile(filepath=str(P/'ReferenceStock5080_Game_Editable.blend'))
 for o in list(bpy.data.objects):
  if o.name!='SM_SkeletonStock':bpy.data.objects.remove(o,do_unlink=True)
 frame=bpy.data.objects['SM_SkeletonStock'];frame.hide_render=False;frame.hide_set(False);parts=[frame]
 # Capture source UVs before assigning the body atlas fit.
 if frame.data.uv_layers:frame.data.uv_layers[0].name='GeneratedSourceUV'
 bm=bmesh.new();bm.from_mesh(frame.data)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(13.5,0,0),plane_no=(1,0,0),clear_inner=True)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(21.62,0,0),plane_no=(1,0,0),clear_outer=True)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().z>1.18],context='FACES')
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.002)
 # Remove only tiny disconnected generation specks, not the large open frame.
 bm.to_mesh(frame.data);bm.free();frame.name='Retained_5080_Open_Frame'
 with bpy.data.libraries.load(str(OLD/(key+'_fit_reference.blend')),link=False) as (a,b):
  b.materials=[n for n in a.materials if n==('Body.001' if key=='m4' else 'M_AKM_Soviet_PBR')]
 if key=='m4':metal=b.materials[0]
 else:
  metal=simple('AKM_receiver_steel',(.06,.065,.07),.5);nt=metal.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');tp=P.parent/'AKMSoviet20260911/Source/ak47fbx_extracted/textures'
  for label,socket in [('Base_color','Base Color'),('Metallic','Metallic'),('Roughness','Roughness'),('Normal_OpenGL','Normal')]:
   im=bpy.data.images.load(str(tp/('AK_'+label+'.png')),check_existing=True);node=nt.nodes.new('ShaderNodeTexImage');node.image=im
   if label!='Base_color':im.colorspace_settings.name='Non-Color'
   if label=='Normal_OpenGL':n=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(node.outputs['Color'],n.inputs['Color']);nt.links.new(n.outputs['Normal'],bs.inputs[socket])
   else:nt.links.new(node.outputs['Color'],bs.inputs[socket])
 metal=metal.copy();metal.name='StockMetal';poly=simple('StockPolymer',(.021,.024,.027),.49);rubber=simple('StockRubber',(.008,.009,.010),.83)
 frame.data.materials.clear();frame.data.materials.append(metal)
 for f in frame.data.polygons:f.material_index=0
 # The first inspection exposed torn boundaries and fused screw holes in the
 # retained generated frame. Rebuild the same measured outline and its two
 # windows, rather than hiding those defects with a dark material.
 parts.remove(frame);bpy.data.objects.remove(frame,do_unlink=True)
 frame=prism('5080_Frame_Retopology',[(13.38,1.26),(20.65,1.30),(21.60,1.05),(21.60,-8.90),(20.95,-9.08),(13.20,-8.75),(13.15,-7.35),(15.50,-6.80),(16.05,-6.15),(16.05,-2.55),(13.38,-2.36)],2.10,metal,.12)
 hole(frame,[(16.92,-2.58),(19.34,-2.58),(19.45,-5.72),(19.22,-6.12),(17.17,-6.10),(16.92,-5.80)])
 hole(frame,[(13.95,-7.83),(16.08,-7.24),(17.05,-6.93),(19.35,-6.93),(19.40,-8.27),(13.95,-8.11)])
 for side in [-1,1]:
  for loc,size in [((17.73,side*1.075,-.08),(3.04,.32,1.44)),((17.68,side*1.075,-1.96),(3.60,.28,.16))]:
   cut=cube('Machined_panel_recess',loc,size,metal,.07);parts.remove(cut);active(frame);m=frame.modifiers.new('Shallow side recess','BOOLEAN');m.operation='DIFFERENCE';m.object=cut;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True)
 bevel(frame,.045)
 cube('Rear_carrier_sleeve',(20.70,0,-3.88),(1.72,2.81,10.37),metal,.22)
 for x in [19.91,21.37]:cube('Rear_carrier_edge',(x,0,-3.86),(.12,2.88,10.26),metal,.055)
 tube('Upper_tube',.78,14.12,1.09,.79,0,metal)
 tube('Front_coupling',0,.86,1.22,.82,0,metal)
 tube('Front_lip',0,.17,1.27,.82,0,metal)
 tube('Collar_ring',.44,.57,1.247,1.19,0,metal)
 tube('Lower_tube',4.22,14.22,.565,.39,-1.735,metal)
 # The lower end cap is independent of the upper tube and keeps a visible gap.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=16,radius=.565,location=(4.22,0,-1.735));cap=bpy.context.object;cap.name='Lower_tube_end_cap';cap.scale.x=.65;cap.data.materials.append(metal);parts.append(cap)
 prism('Cheek_carrier',[(6.85,1.18),(7.12,1.69),(15.95,1.91),(16.57,1.49),(16.57,.96),(7.02,.96)],2.12,metal,.075)
 prism('Separate_cheek_pad',[(7.18,1.77),(7.52,1.94),(15.68,2.045),(16.0,1.91),(15.94,1.77),(7.23,1.59)],1.99,poly,.06)
 for i in range(11):
  x=8.2+i*.59;z=1.947+(x-7.52)*.0129;cube('Cheek_grip_rib_%02d'%i,(x,0,z),(.18,1.62,.075),poly,.032)
 # Clean clamp shoulders replace the indistinct ribbed bridge at the tube/frame junction.
 for side in [-1,1]:
  cube('Clamp_side_cheek',(14.22,side*1.12,-.55),(1.22,.26,2.86),metal,.085)
  for i in range(3):
   rib=prism('Clamp_diagonal_rib',[(14.98+i*.4,.84),(15.17+i*.4,.84),(15.66+i*.4,-1.30),(15.45+i*.4,-1.30)],.20,metal,.035);rib.location.y=side*1.10
  for x,z in [(13.99,-1.58),(14.47,.47),(18.50,-.08),(13.62,-8.28)]:bolt(x,side*(.965 if x>18 else 1.29 if z>-2 else 1.105),z,metal)
 # Clear carrier/pad seam and a rounded pad with individually readable tread ribs.
 carrier=prism('Buttpad_carrier',[(21.30,1.30),(21.68,1.17),(21.78,.84),(21.78,-8.55),(21.55,-8.94),(21.27,-8.97)],2.84,metal,.07)
 pad=prism('Rubber_buttpad',[(21.83,1.13),(22.24,1.02),(22.65,.55),(22.89,-.15),(22.89,-7.74),(22.63,-8.40),(22.13,-8.88),(21.83,-8.89)],2.72,rubber,.15)
 for i in range(22):
  z=-7.65+i*.353;cube('Buttpad_tread_%02d'%i,(22.93,0,z),(.19,2.45,.12),rubber,.045)
 if key=='akm':
  plate=cube('AKM_receiver_cover',(.16,0,-.25),(.5,4.1,3.8),metal,.055)
  bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1.35,depth=1.5,location=(.16,0,0),rotation=(0,math.pi/2,0));cut=bpy.context.object;active(plate);m=plate.modifiers.new('Tube passage','BOOLEAN');m.object=cut;m.operation='DIFFERENCE';bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True)
 # Map only metal polygons into a visually inspected clean receiver region.
 # UV1 keeps the imported source unwrap for authoring. No gun logos or wood islands.
 box=(.54,.73,.655,.85) if key=='m4' else (.055,.053,.285,.092)
 for o in parts:
  active(o);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  # Weld within each part, never across touching but separate rings or pads.
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_area()<1e-10],context='FACES');bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bm.to_mesh(o.data);bm.free()
  if key=='akm':
   # Split at physical tile boundaries so no face interpolates across atlas
   # islands. The verified receiver patch covers 12 x 2.5 cm, as on AKM mounts.
   bm=bmesh.new();bm.from_mesh(o.data)
   for axis,step in [(0,12.0),(1,2.5),(2,2.5)]:
    low=min(v.co[axis] for v in bm.verts);high=max(v.co[axis] for v in bm.verts)
    for k in range(math.floor(low/step)+1,math.ceil(high/step)):
     p=[0,0,0];p[axis]=k*step;n=[0,0,0];n[axis]=1;bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=p,plane_no=n)
   bm.to_mesh(o.data);bm.free()
  if not o.data.uv_layers:o.data.uv_layers.new(name='GeneratedSourceUV')
  uv=o.data.uv_layers.new(name='ReceiverAtlasUV');o.data.uv_layers.active=uv;uv.active_render=True
  for f in o.data.polygons:
   normal=f.normal;dominant=max(range(3),key=lambda i:abs(normal[i]));ua=2 if dominant==0 else 0;va=2 if dominant==1 else 1
   center=f.center;tile_u=math.floor(center[ua]/12);tile_v=math.floor(center[va]/2.5)
   for li in f.loop_indices:
    co=o.data.vertices[o.data.loops[li].vertex_index].co
    # Side projection with a small depth contribution avoids degenerate top UVs.
    a=(co.x+.14*co.y+.5)/24.1;b=(co.z+.18*co.y+9.6)/12.2
    if key=='akm':a=co[ua]/12-tile_u;b=co[va]/2.5-tile_v
    uv.data[li].uv=(box[0]+(box[2]-box[0])*max(.005,min(.995,a)),box[1]+(box[3]-box[1])*max(.005,min(.995,b)))
  # FBX consumers use channel zero. Preserve the old layer as channel one.
  saved=[tuple(d.uv) for d in o.data.uv_layers[0].data];mapped=[tuple(d.uv) for d in uv.data]
  for i,v in enumerate(mapped):o.data.uv_layers[0].data[i].uv=v
  for i,v in enumerate(saved):uv.data[i].uv=v
  o.data.uv_layers[0].name='ReceiverAtlasUV0';uv.name='GeneratedSourceUV1';o.data.uv_layers.active_index=0;o.data.uv_layers[0].active_render=True
 out=R/key;out.mkdir(exist_ok=True)
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'Stock_Refined_Parts.blend'))
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=frame;bpy.ops.object.join();frame.name='SM_SkeletonStock'
 oldslots=list(frame.data.materials);newslots=[metal,poly,rubber];indices=[newslots.index(oldslots[f.material_index]) if oldslots[f.material_index] in newslots else 0 for f in frame.data.polygons]
 frame.data.materials.clear()
 for mat in newslots:frame.data.materials.append(mat)
 for f,i in zip(frame.data.polygons,indices):f.material_index=i
 frame.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(frame.data);deg=[f for f in bm.faces if f.calc_area()<1e-10];bmesh.ops.delete(bm,geom=deg,context='FACES');bm.to_mesh(frame.data);bm.free();frame.data.calc_loop_triangles()
 records[key]={'triangles':len(frame.data.loop_triangles),'dimensions_cm':list(frame.dimensions),'method':'retopology fitted to accepted RTX5080 master; rebuilt torn frame windows, fused fasteners and upper details','material_slots':[m.name for m in frame.data.materials],'body_atlas_uv_box':box,'removed_degenerate_faces':len(deg)}
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'Stock_Refined_Editable.blend'))
 mod=frame.modifiers.new('Export triangulation','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.ops.export_scene.fbx(filepath=str(out/'SM_SkeletonStock.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 print('STOCK_REFINED_EXPORT_PASS',key,records[key],flush=True)
(R/'geometry_report.json').write_text(json.dumps(records,indent=2))
