import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;SA=O.parent;reports={}
for gun,src,frames in [('M4','ExtMagRebuild20260919/M4_ExtMag_reload_Editable.blend',[61,76,95]),('AKM','AKMReloadPolish20260911/base/A_AKM_reload.blend',[130,148,178])]:
 bpy.ops.wm.open_mainfile(filepath=str(SA/src));rig=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 arms=bpy.data.objects.get('SK_Manny_Arms_Export')
 if not arms:arms=next(o for o in s.objects if o.type=='MESH' and any('hand_l'==g.name for g in o.vertex_groups) and len(o.data.vertices)>1000)
 with bpy.data.libraries.load(str(SA/'ExtMagPattern20260919'/(gun+'_ExtMag_Editable.blend')),link=False) as (a,b):b.objects=['SM_ExtMag_'+gun+'40']
 mag=b.objects[0];s.collection.objects.link(mag);mag.hide_set(False);mag.hide_render=False
 bm=bmesh.new();bm.from_mesh(mag.data);edges={e for e in bm.edges if e.is_boundary};components=[]
 while edges:
  e=edges.pop();group={e};stack=list(e.verts)
  while stack:
   v=stack.pop()
   for edge in list(v.link_edges):
    if edge in edges:edges.remove(edge);group.add(edge);stack.extend(edge.verts)
  vs=set(v for edge in group for v in edge.verts)
  components.append({'edges':len(group),'length_mm':sum(e.calc_length() for e in group)*1000,'bounds':[[min(v.co[k] for v in vs),max(v.co[k] for v in vs)] for k in range(3)]})
 bm.free();reports[gun]={'source':src,'action':rig.animation_data.action.name,'fps':s.render.fps,'range':list(rig.animation_data.action.frame_range),'arms':arms.name,'boundaries':components,'frames':{}}
 for o in s.objects:o.hide_render=o not in [arms,mag]
 arms.hide_set(False);arms.hide_render=False
 s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;arms.color=(.22,.35,.6,1);mag.color=(.65,.48,.18,1)
 cam=bpy.data.objects.new('ContactCamera',bpy.data.cameras.new('ContactCamera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.38
 s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100
 W=rig.matrix_world.copy();rest=rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();M=W@rig.pose.bones['WPN_SOCKET_Magazine'].matrix@rest.inverted()@W.inverted();mag.matrix_world=M
  points=[M@v.co for v in mag.data.vertices];tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in mag.data.polygons]);center=sum(points,Vector())/len(points)
  report={n:{'position':list(W@rig.pose.bones[n].matrix.translation),'distance_mm':tree.find_nearest(W@rig.pose.bones[n].matrix.translation)[3]*1000} for n in ['hand_l','thumb_03_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l']}
  report['mag_transform']=[list(row) for row in M];reports[gun]['frames'][f]=report
  for view,offset in [('palm',(-.38,-.3,.09)),('side',(.4,-.12,.08))]:
   cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(gun+'_'+str(f)+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
(O/'diagnosis.json').write_text(json.dumps(reports,indent=2))
