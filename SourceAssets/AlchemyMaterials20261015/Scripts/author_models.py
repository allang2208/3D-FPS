"""Six original detailed reagent packages; editable masters, FBX/GLB and UCX."""
from pathlib import Path
import bpy,bmesh,sys,json,math,random
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Scripts'))
import geometry as H
R=random.Random(261015);MATS={}
GLASS={
 'GlassClear':([.91,.965,.98],.10,[.94,.98,.99]),
 'GlassAmber':([.55,.29,.09],.16,[.81,.54,.26]),
 'GlassOlive':([.40,.53,.30],.17,[.76,.85,.58]),
 'LiquidBase':([.67,.88,.90],.12,[.86,.96,.97]),
 'LiquidRed':([.36,.018,.034],.16,[.55,.07,.11]),
 'LiquidSilver':([.69,.53,.20],.14,[.91,.80,.46]),
 'LiquidStable':([.24,.52,.55],.17,[.56,.82,.84])}
def materials(key):
 global MATS
 H.MAT=H.material(key);MATS={'Surface':H.MAT}
 for name,(color,rough,tint) in GLASS.items():
  m=bpy.data.materials.new('M_Alchemy_'+name);m.use_nodes=True
  b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*tint,1)
  b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=.96 if name.startswith('Glass') else .82
  b.inputs['IOR'].default_value=1.46 if name.startswith('Glass') else 1.33
  MATS[name]=m
def assign(o,key):o.data.materials.clear();o.data.materials.append(MATS[key]);return o
def label(key,r,z,height,angle=1.3,start=-math.pi/2):
 # Curved paper conforms to the actual bottle wall; positive U reads left-to-right.
 n=48;vs=[];fs=[]
 for zz in (z-height/2,z+height/2):
  for j in range(n+1):
   t=start-angle/2+angle*j/n;vs.append((r*math.cos(t),r*math.sin(t),zz))
 for j in range(n):fs.append((j,j+1,n+2+j,n+1+j))
 o=H.mesh(key+' original curved printed label',vs,fs,key);o['authored_decal']=True
 u0,v0,u1,v1=H.rect(key)
 for f in o.data.polygons:
  for li in f.loop_indices:
   idx=o.data.loops[li].vertex_index;o.data.uv_layers.active.data[li].uv=(u0+(idx%(n+1))/n*(u1-u0),v0+(idx//(n+1))*(v1-v0))
 return o
def shell(name,profile,mat='GlassClear',thick=.18):
 # Continuous base, outer shoulder, rolled mouth and actual inner wall.
 inside=[(z,max(.08,r-thick)) for z,r in reversed(profile)]
 inside[-1]=(profile[0][0]+.28,max(.08,profile[0][1]-thick))
 # Close the entire underside and the internal floor, not only an annular heel.
 # Two small end rings are capped individually to avoid coincident axial vertices.
 solid=[(profile[0][0],.015)]+profile+inside+[(profile[0][0]+.28,.015)]
 o=H.lathe(name,(0,0,0),solid,'white',segments=112,closed=False)
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 H.uv(o,'white');return assign(o,mat)
def liquid(name,r,z0,z1,mat):
 p=[(z0,.015),(z0,r-.12),(z0+.10,r),(z1-.08,r),(z1,r-.035),(z1-.06,r*.80),(z1-.075,.015)]
 return assign(H.lathe(name,(0,0,0),p,'white',segments=96),mat)
def cap(name,r,z,h,region='blacksteel',knurls=48):
 H.lathe(name+' rounded cap',(0,0,z),[(-h/2,r*.94),(-h/2+.07,r),(h/2-.11,r),(h/2,r*.94),(h/2,.02),(-h/2,.02)],region,segments=96)
 for j in range(knurls):
  t=2*math.pi*j/knurls;o=H.box(name+' grip rib %02d'%j,(r*math.cos(t),r*math.sin(t),z),(.09,.11,h*.66),region,.024);o.rotation_euler.z=t
 H.ring(name+' lower gasket',(0,0,z-h/2+.02),r*.98,r*.89,.10,'rubber')
def seal(r,z,region='teal'):
 H.ring('tamper collar',(0,0,z),r,r-.07,.24,region)
 for j in range(16):
  t=j*math.tau/16;o=H.box('tear band bridge',(r*math.cos(t),r*math.sin(t),z+.16),(.06,.06,.12),region,.01);o.rotation_euler.z=t
def graduations(r,z0,count=8):
 for i in range(count):
  z=z0+i*.55;span=.25 if i%2 else .48
  H.cord('etched volume mark',[(r*math.cos(t),r*math.sin(t),z) for t in [(-.60-span/2)+j*span/8 for j in range(9)]],.013,'white',2)
def crystal(name,p,scale,region,seed):
 rnd=random.Random(seed);n=6;vs=[]
 for z,rad in [(0,.70),(.12,1),(.76,.76),(1,.14)]:
  for j in range(n):
   a=j*math.tau/n;rr=rad*(.88+rnd.random()*.22);vs.append((math.cos(a)*rr,math.sin(a)*rr,z))
 fs=[tuple(reversed(range(n))),tuple(3*n+j for j in range(n))]
 for k in range(3):
  for j in range(n):fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
 o=H.mesh(name,vs,fs,region);o.location=p;o.scale=scale;o.rotation_euler=(rnd.uniform(-.25,.25),rnd.uniform(-.25,.25),rnd.random()*math.tau)
 return H.bevel(o,.018,2)
def basefluid():
 shell('thick graduated reagent vessel',[(.25,2.35),(.38,2.68),(.65,2.8),(8.9,2.8),(9.3,2.66),(10.2,1.43),(10.5,1.38),(11.5,1.38),(11.58,1.49)])
 liquid('high purity fluid',2.57,.55,8.4,'LiquidBase')
 H.ring('reinforced bottle heel',(0,0,.55),2.88,2.72,.42,'teal')
 cap('machined polymer closure',1.66,12.0,1.10,'white',52);seal(1.67,11.4)
 H.cylinder('cap top laboratory disc',(0,0,12.58),1.10,.035,'teal')
 label('BaseFluid',2.815,5.0,4.6,1.32);graduations(2.82,2.4,11)
 H.COLLISIONS=[((0,0,5.0),(5.5,5.5,9.7)),((0,0,11.15),(3.3,3.3,2.9))]
def stabilizer():
 H.rounded('moulded dual ampoule carrier',(0,0,.55),(8.4,6.6,1.0),'white',.65,.09)
 H.frame('raised carrier walls',(0,0,1.15),(8.4,6.6,1.25),.25,'teal',.65)
 H.rounded('closed cell insert',(0,0,1.0),(7.65,5.85,.55),'foam',.40,.07)
 for i,x in enumerate((-1.85,1.85)):
  start=len(H.PARTS)
  shell('ampoule %d borosilicate walls'%i,[(0,.67),(.12,.79),(4.05,.79),(4.35,.62),(4.65,.34),(5.0,.31),(5.3,.05)],thick=.10)
  liquid('separate stabilizer fraction',.66,.2,3.90,'LiquidStable' if i==0 else 'LiquidBase')
  H.ring('snap neck scoring',(0,0,4.61),.365,.32,.065,'white')
  H.transform_since(start,Matrix.Translation((x,2.65,1.9))@Matrix.Rotation(math.pi/2,4,'X'))
  for y in (-1.65,1.65):
   H.box('vial cushioned cradle',(x,y,1.32),(2,.45,.48),'teal',.13)
   H.cord('spring retaining clip',[(x-.9,y,1.42),(x-.93,y,2.1),(x-.65,y,2.63),(x,y,2.74),(x+.65,y,2.63),(x+.93,y,2.1),(x+.9,y,1.42)],.045,'steel',5)
 H.box('partition',(0,0,1.25),(.22,5.7,.55),'white',.07)
 H.panel('front identification label',(0,-3.312,1.17),5.9,1.5,'Stabilizer','-Y')
 for x in (-3.8,3.8):
  H.screw('carrier fastener',(x,-2.9,1.78),.13)
  H.screw('carrier fastener',(x,2.9,1.78),.13)
 H.COLLISIONS=[((0,0,1.45),(8.4,6.6,2.9))]
def catalyst():
 shell('catalyst observation vial',[(.45,2.1),(.60,2.28),(5.35,2.28),(5.65,2.05)],thick=.17)
 H.cylinder('sealed catalyst cradle',(0,0,.55),2.40,.6,'blacksteel',sides=96)
 H.ring('gold base rim',(0,0,.46),2.48,2.32,.18,'gold')
 for j in range(11):
  a=j*2.399;r=.40 if j<3 else 1.28
  crystal('active violet crystal %02d'%j,(r*math.cos(a),r*math.sin(a),.88),(.38+.1*(j%3),.32,1.6+(j%4)*.48),'crystal',j+10)
 for j in range(3):
  a=math.radians(30+j*120);x,y=2.37*math.cos(a),2.37*math.sin(a)
  H.box('protective bridge',(x,y,3.2),(.22,.22,4.8),'blacksteel',.07)
  H.screw('cage bolt',(x,y,5.65),.18)
 H.ring('upper cage band',(0,0,5.4),2.48,2.27,.31,'blacksteel')
 cap('sealed catalyst closure',2.52,6.0,.85,'blacksteel',48)
 H.cylinder('catalyst cap insert',(0,0,6.44),1.87,.045,'gold')
 H.stamp('embossed catalyst code','AC-03',(0,-.08,6.47),.48,'blacksteel')
 label('Catalyst',2.495,1.25,1.02,1.5)
 H.COLLISIONS=[((0,0,3.4),(4.9,4.9,6.45))]
def redroot():
 shell('amber root extraction bottle',[(.2,1.9),(.38,2.16),(.65,2.23),(7.4,2.23),(8.3,1.28),(9.15,1.18)],'GlassAmber',.17)
 liquid('deep red root extract',2.01,.5,6.85,'LiquidRed')
 for i in range(15):
  x=R.uniform(-1.2,1.2);y=R.uniform(-1.2,1.2)
  H.cord('settled botanical fibre',[(x,y,.52),(x+.16,y-.12,.75),(x+.35,y+.1,1.0+R.random()*.30)],.018,'root',3)
 H.cylinder('glass dropper stem',(0,0,4.9),.105,7.0,'white',sides=32)
 cap('pipette threaded collar',1.39,9.5,.82,'blacksteel',42);seal(1.4,9.03,'red')
 H.lathe('squeezable pipette bulb',(0,0,9.93),[(0,1.0),(.35,.94),(1.05,.79),(1.85,.64),(2.2,.41),(2.28,.03),(0,.03)],'rubber',segments=96)
 label('RedRoot',2.245,4.45,4.45,1.65);H.ring('root bottle heel',(0,0,.5),2.28,2.15,.28,'red')
 H.COLLISIONS=[((0,0,4.45),(4.45,4.45,8.7)),((0,0,10.2),(2.8,2.8,3.65))]
def bluefungus():
 shell('wide dry specimen jar',[(.25,2.85),(.45,3.15),(.7,3.25),(4.9,3.25),(5.2,3.05),(5.55,3.05)],thick=.20)
 H.cylinder('specimen dry base',(0,0,.45),2.96,.20,'foam')
 for i in range(35):
  a=R.random()*math.tau;r=math.sqrt(R.random())*2.30
  crystal('dry blue fungal crystalline grain %02d'%i,(r*math.cos(a),r*math.sin(a),.61+R.uniform(0,.4)),(.26+R.random()*.36,.3+R.random()*.25,.6+R.random()*1.6),'bluecrystal',i+60)
 H.rounded('desiccant packet',(1.4,1.5,2.10),(1.5,.45,2.0),'white',.23,.06)
 cap('knurled dry jar lid',3.36,5.89,.82,'blue',68);seal(3.36,5.42,'blue')
 H.cylinder('specimen closure seal',(0,0,6.32),2.65,.04,'white')
 H.panel('specimen top printed label',(0,0,6.345),3.8,3.8,'BlueFungus')
 label('BlueFungus',3.27,3.0,2.3,1.04)
 H.COLLISIONS=[((0,0,3.2),(6.65,6.65,6.35))]
def silverleaf():
 shell('olive botanical essence flask',[(.22,1.6),(.4,1.98),(.72,2.08),(6.9,2.08),(7.50,1.87),(8.25,1.0),(8.68,1.0)],'GlassOlive',.17)
 liquid('pale gold flower essence',1.87,.5,6.7,'LiquidSilver')
 H.ring('protective heel',(0,0,.62),2.18,2.02,.55,'green')
 H.ring('neck brass collar',(0,0,8.35),1.11,.98,.27,'gold')
 cap('silverleaf capped dispenser',1.25,9.15,1.05,'gold',52);seal(1.28,8.57,'green')
 H.cylinder('dispenser crown',(0,0,9.72),.92,.10,'green')
 # Protective ribs flank a clear observation window and the broad paper label.
 for a in (0,math.pi):
  x,y=2.10*math.cos(a),2.10*math.sin(a);H.box('bottle protection rib',(x,y,4.0),(.15,.20,6.5),'green',.06)
 label('Silverleaf',2.095,4.3,4.8,1.5)
 for j in range(2):
  side=-1 if j else 1
  outline=[(0,0),(.25*side,.30),(.6*side,.45),(.8*side,.9),(.4*side,.88),(.05*side,.50)]
  o=H.extrude('embossed leaf emblem',outline,0,.035,'gold',.015)
  o.rotation_euler.x=math.pi/2;o.location=(0,-1.95,7.25)
 H.COLLISIONS=[((0,0,3.9),(4.3,4.3,7.6)),((0,0,8.75),(2.6,2.6,2.1))]
BUILDERS={'BaseFluid':basefluid,'Stabilizer':stabilizer,'Catalyst':catalyst,'RedRoot':redroot,'BlueFungus':bluefungus,'Silverleaf':silverleaf}
report={'stage':'authoring','assets':{},'glass_materials':GLASS,'runtime_tested':False,'preview_rendered':False}
for key,builder in BUILDERS.items():
 print('ALCHEMY_MODEL_START',key,flush=True);bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
 H.PARTS=[];H.COLLISIONS=[];materials(key);builder();bpy.context.view_layer.update()
 spec=H.SPEC['assets'][key];source=ROOT/'Authored'/(spec['mesh']+'_Source.blend')
 scene['unit_contract']='centimetres; +Z up; bottom centre export pivot';scene['crafting_implemented']=False
 bpy.ops.wm.save_as_mainfile(filepath=str(source));deps=bpy.context.evaluated_depsgraph_get();exports=[]
 for o in H.PARTS:
  data=bpy.data.meshes.new_from_object(o.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
  e=bpy.data.objects.new(o.name+'_Export',data);scene.collection.objects.link(e);e.matrix_world=o.matrix_world.copy();H.select(e)
  tri=e.modifiers.new('Triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
  if not o.get('authored_decal'):H.uv(e,o['surface_region'])
  exports.append(e)
 bpy.ops.object.select_all(action='DESELECT')
 for e in exports:e.select_set(True)
 bpy.context.view_layer.objects.active=exports[0];bpy.ops.object.join();game=bpy.context.object;game.name=spec['mesh']
 game.data.transform(game.matrix_world);game.matrix_world=Matrix.Identity(4)
 pts=[v.co for v in game.data.vertices];lo=Vector([min(p[k] for p in pts) for k in range(3)]);hi=Vector([max(p[k] for p in pts) for k in range(3)])
 shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z));game.data.transform(Matrix.Translation(shift))
 game.data.calc_loop_triangles();triangles=len(game.data.loop_triangles)
 collisions=[]
 for i,(p,size) in enumerate(H.COLLISIONS):
  bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(p)+shift);c=bpy.context.object;c.name='UCX_'+game.name+'_'+str(i).zfill(2);c.scale=size
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);collisions.append(c)
 H.select(game)
 for c in collisions:c.select_set(True)
 fbx=ROOT/'Export'/(game.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',bake_space_transform=True,mesh_smooth_type='FACE',use_mesh_modifiers=True,use_tspace=True,path_mode='STRIP',add_leaf_bones=False)
 H.select(game);scene.unit_settings.scale_length=1;game.scale=(.01,.01,.01)
 glb=ROOT/'Export'/(game.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT')
 report['assets'][key]={**spec,'source':str(source),'fbx':str(fbx),'glb':str(glb),'triangles_lod0':triangles,'source_components':len(H.PARTS),'actual_dimensions_cm':list(hi-lo),'collision_hulls':len(collisions),'material_slots':[m.name for m in game.data.materials],'geometry_features':[o.name for o in H.PARTS],'nanite_requested':False}
 (ROOT/'model_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
 print('ALCHEMY_MODEL_EXPORTED',key,triangles,flush=True)
report['stage']='sources_and_exports_saved';(ROOT/'model_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print('ALCHEMY_MODELS_COMPLETE',flush=True)
