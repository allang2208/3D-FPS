"""Machined cabinet family: real pockets and integral hardware, no floating cards."""
import math
import bpy,bmesh

def apply_v4(e,revision):
 g=e['g'];B=e['B'];rb=e['roundbox'];pipe=e['pipe'];ring=e['ring']
 active={c['body'] for c in revision['containers']}|{c['front'] for c in revision['containers']}
 changed=set();e['v3_changed']=changed
 for name in ('Armor','EdgeSteel','ReaderGlass','CabinetLining'):
  e['MATERIALS'][name]=e['BASE']+'/Materials/MI_AP4_'+name
 specs={
  'MediaConsoleCell':(.574,.45,.58,False,False),'EntryCabinetCell':(.594,.38,.95,False,False),
  'NightstandCell':(.474,.42,.48,True,False),'WardrobeCell':(.594,.62,2.65,False,False),
  'CyberArchive':(.68,.43,1.95,False,False),'KitchenBase':(.59,.65,.88,False,False),
  'KitchenSink':(.59,.65,.70,False,False),'KitchenUpper':(.59,.38,.94,False,True),
  'GymLocker':(.58,.39,1.32,False,False),'BedArchive':(.68,.40,1.85,False,False),
  'ServiceWall':(.48,.25,.72,False,True),'VanityBay':(.435,.44,.48,False,True),
  'DeskDrawer':(.43,.48,.20,True,True)}

 def solid(c,s,r):
  bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.scale=s
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  bevel=o.modifiers.new('Manufactured radius','BEVEL');bevel.width=r;bevel.segments=3;bevel.use_clamp_overlap=True
  bpy.ops.object.modifier_apply(modifier=bevel.name)
  return o
 def pocket(panel,c,s,r):
  tool=solid(c,s,r)
  bpy.context.view_layer.objects.active=panel
  mod=panel.modifiers.new('Machined recess','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
  bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
 def store(obj,key,mat):
  bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.dissolve_degenerate(bm,dist=.000025,edges=list(bm.edges))
  bm.to_mesh(obj.data);bm.free();obj.data.update()
  verts=[obj.matrix_world@v.co for v in obj.data.vertices]
  g.poly(key,verts,[tuple(p.vertices) for p in obj.data.polygons],mat)
  bpy.data.objects.remove(obj,do_unlink=True)

 for name,(w,d,h,drawer,wall_mount) in specs.items():
  body=name+'Body';front=name+'Front'
  if front not in active:continue
  changed.update((body,front))
  bottom=0. if wall_mount else .09;fw=w-.035;fh=h-bottom-.016
  g.G.pop(('Apartment',front),None);g.C.pop(('Apartment',front),None)
  # Same hinge/origin and envelope as the existing animated parts.
  x0=-fw/2 if drawer else 0.;cx=x0+fw/2
  cy=-d/2-.018 if drawer else 0.
  cz=bottom+fh/2
  panel=solid((cx,cy,cz),(fw,.036,fh),min(.008,fh*.04))
  # Grip is cut into the plate, with an inner back and a connected metal lip.
  gh=min(.22,fh*.47);gw=.042;gx=x0+fw-.072;gz=bottom+fh*.52
  if drawer:gw=fw*.49;gh=min(.035,fh*.22);gx=cx;gz=bottom+fh*.72
  pocket(panel,(gx,cy-.016,gz),(gw,.029,gh),.005)
  # Reader sits BELOW the exterior face inside a sealed chamfered recess.
  rw=min(.105,fw*.29);rh=min(.079,fh*.21)
  rx=x0+.055+rw/2;rz=h-.052-rh/2
  pocket(panel,(rx,cy-.014,rz),(rw,.030,rh),.006)
  store(panel,front,'Armor')
  g.box(None,(cx,cy,cz),(fw,.036,fh),collision=front)
  rb(front,(gx,cy-.002,gz),(gw-.006,.006,gh-.006),'Dark',.002)
  if drawer:
   rb(front,(gx,cy-.012,gz+gh*.25),(gw-.014,.009,.008),'EdgeSteel',.002)
  else:rb(front,(gx+gw*.25,cy-.011,gz),(.010,.009,gh-.018),'EdgeSteel',.002)
  rb(front,(rx,cy-.003,rz),(rw-.009,.005,rh-.009),'ReaderGlass',.003)
  # Small biometric tracks and a restrained status lamp are built into the pocket.
  for j in range(4):
   B(front,(rx-rw*.24+j*rw*.16,cy-.0063,rz),(.002,.0015,rh*.38),'Steel')
  B(front,(rx+rw*.29,cy-.0064,rz),(.003,.0015,rh*.37),'Cyan')
  # Edge channels stay within the door thickness; open/close clearance is unchanged.
  for xx in (x0+.020,x0+fw-.020):
   rb(front,(xx,cy-.0185,cz),(.010,.004,max(.02,fh-.07)),'EdgeSteel',.002)
  for z in (bottom+.026,h-.026):
   B(front,(cx,cy-.0185,z),(max(.03,fw-.06),.004,.008),'Dark')
  if fh>.8:
   # Integrated bottom louvres with a recessed dark bed and real staggered fins.
   vz=bottom+.13
   B(front,(cx,cy-.0187,vz),(fw*.63,.004,.095),'Dark')
   for j in range(6):
    zz=vz-.037+j*.014
    g.beam(front,(cx-fw*.29,cy-.022,zz),(cx+fw*.29,cy-.022,zz),.006,.008,'Teal')
  if not drawer:
   for z in (bottom+.085,h-.085):
    g.cylinder(front,(.010,cy+.009,z-.027),(.010,cy+.009,z+.027),.010,'Steel',24)
  else:
   # Bottom/side/back tray geometry moves with the new drawer front.
   B(front,(0,0,bottom+.024),(w-.085,d-.075,.018),'CabinetLining')
   for x in (-w/2+.041,w/2-.041):B(front,(x,0,bottom+fh*.35),(.014,d-.07,fh*.6),'CabinetLining')
   B(front,(0,d/2-.044,bottom+fh*.35),(w-.095,.014,fh*.6),'CabinetLining')
  # No new obstruction: all carcass details remain on existing inner/outer surfaces.
  for x in (-w/2+.018,w/2-.018):
   for z in (bottom+.06,h-.06):
    g.cylinder(body,(x,-d/2-.002,z),(x,-d/2-.009,z),.005,'EdgeSteel',16)
  if h>.8:
   B(body,(0,d/2-.028,h-.065),(w-.075,.007,.013),'Dark')
   B(body,(0,d/2-.033,h-.065),(w-.10,.003,.004),'Warm')
  for x in (-w/2+.034,w/2-.034):
   B(body,(x,d/2-.033,(bottom+h)/2),(.014,.008,h-bottom-.09),'EdgeSteel')
 revision['revision']='20261022_RefinementV4'
 revision['cabinet_upgrade']={'changed_meshes':sorted(changed),'hinges_preserved':True,
  'floating_card_panels_removed':True,'pocket_depth_m':.014,'material_roles':['Armor','EdgeSteel','ReaderGlass','CabinetLining']}
