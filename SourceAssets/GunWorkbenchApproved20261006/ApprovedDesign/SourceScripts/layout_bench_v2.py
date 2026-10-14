import bpy,pathlib,math,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
R=pathlib.Path(__file__).resolve().parents[1];P=R/'input/table/unpacked';bpy.ops.wm.read_factory_settings(use_empty=True);groups={}
def append_file(f,names=None):
 with bpy.data.libraries.load(str(f),link=False) as (src,dst):dst.objects=names if names else src.objects
 for o in dst.objects:
  if o:bpy.context.scene.collection.objects.link(o)
 return [o for o in dst.objects if o]
tableobs=append_file(P/'01_TableAndMat/01_TableAndMat.blend');lamps=append_file(P/'02_Lamp/02_Lamp.blend');tools=append_file(P/'03_Tools/03_Tools.blend');groups['OriginalTableMat']=tableobs;groups['Lamp']=lamps
for name,pos,oldx in [('Printer',(-.86,-.97,.938),-.40),('AmmoPress',(-.22,-.97,.938),.40)]:
 with bpy.data.libraries.load(str(R/'output/Machines_Design_Working.blend'),link=False) as (src,dst):dst.collections=[name]
 collection=dst.collections[0];bpy.context.scene.collection.children.link(collection);bpy.context.view_layer.update();obs=list(collection.all_objects);xf=Matrix.Translation(Vector(pos))@Matrix.Rotation(math.pi,4,'Z')@Matrix.Translation(Vector((-oldx,0,0)))
 for o in obs:o.matrix_world=xf@o.matrix_world
 groups[name]=obs
exec((R/'src/machine_props.py').read_text());materials();exec((R/'src/desk_props.py').read_text());parts_tray();bpy.context.view_layer.update()
xf=Matrix.Translation(Vector((.80,-.98,.938)))@Matrix.Rotation(-math.pi/2,4,'Z')
for o in GROUPS['ComponentsTray']:o.matrix_world=xf@o.matrix_world
groups['ComponentsTray']=GROUPS['ComponentsTray']
# Retain the original assembly mat and all ticks; add only peripheral props.
group('ToolOrganizer');cube('Peripheral tool mat',(.235,-.97,.941),(.35,.56,.006),M['black'],.006);groups['ToolOrganizer']=GROUPS['ToolOrganizer']
bpy.context.view_layer.update()
def bounds(obs):
 bpy.context.view_layer.update();vv=[o.matrix_world@Vector(p) for o in obs for p in o.bound_box];return [min(v[k] for v in vv) for k in range(3)],[max(v[k] for v in vv) for k in range(3)]
def relocate(o,xy,bottom):
 lo,hi=bounds([o]);o.location+=Vector((xy[0]-(lo[0]+hi[0])/2,xy[1]-(lo[1]+hi[1])/2,bottom-lo[2]))
for o in tools:
 if 'Screwdriver' in o.name:relocate(o,(.235,-.965),.9445);groups['Screwdriver']=[o]
 elif 'Wrench' in o.name:relocate(o,(.235,-.78),.9445);groups['Wrench']=[o]
 elif 'Pliers' in o.name:relocate(o,(.235,-1.15),.9445);groups['Pliers']=[o]
 elif 'OilCan' in o.name:relocate(o,(1.095,-1.11),.9386);groups['OilCan']=[o]
 else:bpy.data.objects.remove(o,do_unlink=True)
# New ammo boxes are actual-scale meshes, not gallery transforms.
AR=R/'input/ammo/unpacked/AmmoBatch'
for gid,xy in [('ammo_762',(.70,.805)),('ammo_556',(.70,1.10)),('ammo_9',(1.005,.805))]:
 ob=append_file(AR/'Families'/gid/(gid+'.blend'),['SM_'+gid+'_LOD0'])[0];ob.hide_set(False);ob.hide_render=False;ob.matrix_world=Matrix.Translation(Vector((xy[0],xy[1],.9412)))@Matrix.Rotation(-math.pi/2,4,'Z');groups[gid]=[ob]
 group(gid+'_Pad');lo,hi=bounds([ob]);pad=cube(gid+'_SupportPad',((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,.9395),(hi[0]-lo[0]+.012,hi[1]-lo[1]+.012,.003),M['black'],.003);groups[gid].append(pad)
# Restore only the known shared/label texture paths; original table assets are packed.
files={p.name:p for p in AR.rglob('*.png')}
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  bn=pathlib.Path(im.filepath).name
  if bn in files:im.filepath=str(files[bn]);im.reload()
for name,obs in groups.items():
 for o in obs:o['layout_group']=name
# Whole-group mesh intersections; intended fasteners, frame joints, support contacts within a prop excluded.
dg=bpy.context.evaluated_depsgraph_get()
def bvh(obs):
 vv=[];ff=[]
 for o in obs:
  if o.type not in ['MESH','CURVE','FONT','SURFACE']:continue
  ev=o.evaluated_get(dg);me=ev.to_mesh();off=len(vv);vv.extend(ev.matrix_world@v.co for v in me.vertices);ff.extend(tuple(off+i for i in p.vertices) for p in me.polygons);ev.to_mesh_clear()
 return BVHTree.FromPolygons(vv,ff,all_triangles=False,epsilon=0) if vv else None
B={name:bounds(obs) for name,obs in groups.items()};trees={name:bvh(obs) for name,obs in groups.items()};collisions=[]
for i,a in enumerate(groups):
 for b in list(groups)[i+1:]:
  if a=='OriginalTableMat' and b=='Lamp':continue
  if 'ToolOrganizer' in [a,b] and any(k in [a,b] for k in ['Screwdriver','Pliers','Wrench']):continue
  alo,ahi=B[a];blo,bhi=B[b]
  if all(ahi[k]>=blo[k] and bhi[k]>=alo[k] for k in range(3)):
   hits=trees[a].overlap(trees[b]) if trees[a] and trees[b] else []
   if hits:collisions.append({'groups':[a,b],'triangle_pairs':len(hits)})
keepout=[]
for name,(lo,hi) in B.items():
 if name in ['OriginalTableMat','Lamp']:continue
 if hi[0]>.53 and lo[0]<1.13 and hi[1]>-.65 and lo[1]<.65:keepout.append(name)
report={'units':'meters; original table source origin retained','groups':{n:{'min':l,'max':h} for n,(l,h) in B.items()},'inter_group_surface_intersections':collisions,'static_props_over_existing_assembly_drag_region':keepout,'original_mat_preserved':True,'tabletop_height':.93774986267,'contact_reference':.938,'notes':['Checks are cloud source geometry, not UE runtime.','Within-machine assembly joints and intentional support contacts are excluded.','Old hammer and old ammo were omitted from the redesigned cloud scene only.','Overall height changes; prefab placement uses bounds centre and requires explicit compensation at later integration.']}
(R/'output/layout_validation.json').write_text(json.dumps(report,indent=2));print('COLLISION_REPORT',json.dumps({'hits':collisions,'keepout':keepout}))
# Presentation lighting and orthographic checks.
matfloor=mat('Studio floor',(.023,.030,.040),0,.82);group('Studio');cube('Studio ground',(0,0,-.045),(200,200,.07),matfloor,0)
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def light(name,loc,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;aim(o,(0,0,.8))
light('Key',(-3,2,5),1400,4);light('Fill',(3,1,4),1050,4);light('Rim',(0,-4,4.5),1500,3)
bpy.ops.object.camera_add(location=(-3.9,4.2,3.6));c=bpy.context.object;aim(c,(0,0,.78));c.data.type='ORTHO';c.data.ortho_scale=4.8;s=bpy.context.scene;s.camera=c;s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True;s.world=bpy.data.worlds.new('Studio World');s.world.color=(.15,.15,.15);s.view_settings.view_transform='AgX';s.render.resolution_x=1800;s.render.resolution_y=1500;s.render.image_settings.file_format='PNG'
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'output/GunWorkbench_Layout_Cloud_V2.blend'))
s.render.filepath=str(R/'output/GunWorkbench_Layout_Perspective_V2.png');bpy.ops.render.render(write_still=True)
c.location=(0,0,5.4);aim(c,(0,0,0));c.data.ortho_scale=3.35;s.render.resolution_x=1600;s.render.resolution_y=1600;s.render.filepath=str(R/'output/GunWorkbench_Layout_Top_V2.png');bpy.ops.render.render(write_still=True)
