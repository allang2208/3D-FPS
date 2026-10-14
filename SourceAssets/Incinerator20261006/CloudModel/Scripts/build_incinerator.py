import bpy, math, sys, json, pathlib
from mathutils import Vector
R=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parents[0]/'gunbench-work/src'))
import machine_props as p
bpy.ops.wm.read_factory_settings(use_empty=True)
p.materials(); p.group('Incinerator')
M=p.M
# Match the approved workshop powdercoat, blue-grey enamel, steel and amber accents.
for m in M.values():
 for n in list(m.node_tree.nodes):
  if n.type in {'TEX_NOISE','BUMP'}:m.node_tree.nodes.remove(n)
M['body']=p.mat('Incinerator grey green powdercoat',(.24,.30,.30),.55,.42)
M['lining']=p.mat('Refractory ceramic dark',(.11,.095,.075),0,.88)
M['heat']=p.mat('Low amber chamber glow',(.42,.055,.003),0,.55)
b=M['heat'].node_tree.nodes.get('Principled BSDF');b.inputs['Emission Color'].default_value=(1,.16,.01,1);b.inputs['Emission Strength'].default_value=1.8
# Floor contact feet and plinth.
for x in [-.435,.435]:
 for y in [-.32,.32]:
  p.cyl('Elastomer foot',(x,y,.021),.058,.042,M['black'])
  p.cyl('Steel levelling foot',(x,y,.057),.045,.03,M['steel'])
  p.cube('Foot support',(x,y,.097),(.10,.10,.06),M['dark'],.008)
p.cube('Reinforced lower plinth',(0,0,.16),(1.10,.84,.10),M['dark'],.018)
p.cube('Ash service housing',(0,0,.36),(1.04,.80,.30),M['body'],.015)
p.cube('Combustion body',(0,.015,.97),(1.04,.77,.92),M['body'],.022)
p.cube('Upper exhaust cowling',(0,.015,1.49),(1.08,.81,.15),M['blue'],.018)
# Formed rear skin and accessible lateral service panel.
for x in [-.529,.529]:
 p.cube('Side service gasket',(x,.035,.97),(.015,.63,.73),M['black'],.008)
 p.cube('Side enamel access cover',(x+math.copysign(.011,x),.035,.97),(.012,.60,.70),M['blue'],.009)
 for y in [-.23,.30]:
  for z in [.65,1.28]:p.bolt('Side panel captive fastener',(x+math.copysign(.02,x),y,z),'X',.007)
 # A recessed vent grille with real slats, no overlapping decals.
 p.cube('Side vent black recess',(x+math.copysign(.019,x),.055,.79),(.010,.41,.18),M['black'],.004)
 for j in range(7):p.cube('Side ventilation louvre',(x+math.copysign(.030,x),.055,.721+j*.023),(.024,.395,.010),M['steel'],.0015)
# Front opening: proud frame, recessed refractory reveal, insulated door.
p.cube('Front refractory reveal',(0,-.383,.985),(.87,.032,.75),M['lining'],.016)
for x in [-.448,.448]:p.cube('Door jamb',(x,-.411,.987),(.045,.075,.80),M['dark'],.008)
for z in [.589,1.385]:p.cube('Door frame header',(0,-.411,z),(.938,.075,.045),M['dark'],.008)
p.cube('Door graphite seal',(0,-.438,.986),(.817,.036,.715),M['black'],.024)
p.cube('Insulated loading door',(0,-.465,.986),(.78,.048,.680),M['blue'],.027)
p.cube('Front door inset',(0,-.491,1.03),(.65,.012,.455),M['body'],.016)
# Small protected inspection slot rather than an unbounded glowing facade.
p.cube('Inspection window frame',(0,-.504,1.15),(.33,.026,.116),M['dark'],.010)
p.cube('Inspection ceramic black border',(0,-.519,1.15),(.294,.007,.080),M['black'],.006)
p.cube('Amber chamber aperture',(0,-.524,1.15),(.267,.005,.052),M['heat'],.004)
for x in [-.1,-.05,0,.05,.1]:p.cube('Inspection window guard',(x,-.530,1.15),(.008,.009,.057),M['steel'],.001)
# Hinges distinct from door and jamb. Handle swept with deliberate clearance.
for z in [.75,1.25]:
 p.cube('Hinge frame leaf',(-.415,-.452,z),(.068,.033,.076),M['steel'],.004)
 p.cube('Hinge door leaf',(-.362,-.495,z),(.060,.018,.071),M['steel'],.004)
 p.cyl('Hinge barrel',(-.40,-.503,z),.018,.094,M['dark'])
 for dz in [-.046,.046]:p.cyl('Hinge pin end',(-.40,-.503,z+dz),.023,.008,M['steel'])
 for xx in [-.43,-.35]:p.bolt('Hinge bolt',(xx,-.512,z),'Y',.007)
p.cube('Door latch plate',(.318,-.508,.943),(.080,.024,.182),M['dark'],.008)
for z in [.891,.995]:p.cyl('Handle standoff',(.318,-.554,z),.014,.072,M['steel'],'Y')
p.rod('Cool touch handle',(.318,-.594,.890),(.318,-.594,.997),.018,M['black'])
p.cube('Latch cam',(.401,-.475,.94),(.080,.024,.050),M['steel'],.005)
# Lower clean-out hatch (not a gameplay output drawer).
p.cube('Maintenance hatch seal',(0,-.410,.355),(.79,.025,.195),M['black'],.010)
p.cube('Maintenance hatch',(0,-.431,.355),(.755,.025,.163),M['blue'],.008)
p.text('Hatch service marking','SERVICE ACCESS',(0,-.446,.310),.022,M['paper'])
for x in [-.12,.12]:p.cyl('Service handle spacer',(x,-.46,.38),.008,.032,M['steel'],'Y')
p.rod('Service hatch handle',(-.12,-.480,.38),(.12,-.480,.38),.011,M['steel'])
for x in [-.344,.344]:p.bolt('Service captive screw',(x,-.451,.35),'Y',.006)
# Narrow control fascia mounted above the door.
p.cube('Control fascia',(0,-.423,1.475),(.97,.036,.114),M['dark'],.007)
p.cube('Status screen bezel',(-.25,-.448,1.475),(.25,.023,.074),M['steel'],.005)
p.cube('Status screen',(-.25,-.462,1.475),(.222,.006,.052),M['screen'],.003)
p.text('Screen lettering','STANDBY',(-.25,-.467,1.461),.027,M['cyan'])
for i,col in enumerate(['green','orange']):
 p.cyl('Panel indicator collar',(.020+i*.078,-.449,1.485),.017,.016,M['steel'],'Y')
 p.cyl('Panel indicator',(.020+i*.078,-.460,1.485),.011,.009,M[col],'Y')
p.cyl('Selector knob',(.208,-.463,1.480),.024,.035,M['black'],'Y')
p.cube('Selector index',(.208,-.484,1.495),(.004,.003,.011),M['paper'],.0004)
p.cyl('Stop button collar',(.365,-.451,1.477),.029,.019,M['orange'],'Y')
p.cyl('Red stop button',(.365,-.468,1.477),.021,.019,M['red'],'Y')
# Identification and geometric caution markers; separate typography, no texture stretching.
p.cube('Identity plate',(0,-.504,.823),(.29,.009,.067),M['dark'],.003)
p.text('Name plate','INCINERATOR',(0,-.510,.824),.027,M['paper'])
p.text('Unit mark','CS / 01',(0,-.510,.802),.012,M['steel'])
for x in [-.25,.25]:
 p.cube('Warning plate',(x,-.503,.716),(.086,.008,.044),M['orange'],.004)
 p.text('Warning text','HOT',(x,-.509,.706),.020,M['black'])
for x in [-.45,.45]:
 for z in [.23,1.54]:p.bolt('Front chassis fastener',(x,-.436,z),'Y',.007)
# Roof exhaust stack, believable external shroud with bands and rain cap.
p.cube('Exhaust mounting saddle',(0,.145,1.585),(.42,.38,.05),M['dark'],.008)
p.cyl('Exhaust lower flange',(0,.145,1.62),.164,.033,M['steel'])
p.cyl('Exhaust shield',(0,.145,1.80),.138,.35,M['dark'],verts=48)
for z in [1.66,1.94]:
 p.ring('Exhaust steel clamp',(0,.145,z),.140,.009,M['steel'])
for a in range(0,360,60):
 t=math.radians(a);p.bolt('Flange anchor',(.147*math.cos(t),.145+.147*math.sin(t),1.643),'Z',.006)
for x in [-.112,.112]:p.rod('Rain hood support',(x,.145,1.961),(x,.145,2.048),.009,M['steel'])
p.cyl('Rain cap',(0,.145,2.057),.191,.024,M['blue'],verts=48)
p.cyl('Rain cap inset',(0,.145,2.074),.13,.010,M['dark'],verts=48)
# Side utility enclosure and guarded conduit, outside the front access area.
p.cube('Electrical junction housing',(.557,.232,.51),(.12,.22,.17),M['dark'],.011)
for y in [.153,.31]:p.bolt('Junction cover screw',(.62,y,.51),'X',.006)
p.cable('Protected utility conduit',[(.592,.23,.42),(.596,.28,.28),(.49,.39,.23),(.28,.414,.23)],.012)
# Single rear fan shroud.
p.cyl('Rear fan housing',(0,.438,1.17),.153,.085,M['dark'],'Y',40)
for x in [-.11,-.073,-.036,0,.036,.073,.11]:
 half=math.sqrt(.139**2-x*x);p.rod('Rear fan guard',(x,.486,1.17-half),(x,.486,1.17+half),.004,M['steel'],8)
# Source remains editable. Game copy converts all curves/modifiers and uses compact constant PBR.
objects=list(p.GROUPS['Incinerator']);bpy.context.view_layer.update()
coords=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
bounds={'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)]}
manifest={'units':'meters','up':'Z','front':'-Y','origin':'floor origin (0,0,0)','bounds':bounds,'objects':len(objects),'notes':['Fictional game prop exterior; no real engineering dimensions or functionality.','Cloud model, separate independent incinerator; no output or recipe designed.','Game physical destruction is a separate UI/runtime implementation.'],'materials':[]}
for m in bpy.data.materials:
 if not m.use_nodes:continue
 bs=m.node_tree.nodes.get('Principled BSDF')
 if not bs:continue
 # Consistent UE mapping. No required Blender-only procedural dependencies.
 for n in list(m.node_tree.nodes):
  if n.type in {'TEX_NOISE','BUMP'}:m.node_tree.nodes.remove(n)
 manifest['materials'].append({'name':m.name,'base_color':list(bs.inputs['Base Color'].default_value),'metallic':bs.inputs['Metallic'].default_value,'roughness':bs.inputs['Roughness'].default_value,'emission_color':list(bs.inputs['Emission Color'].default_value),'emission_strength':bs.inputs['Emission Strength'].default_value})
bpy.ops.wm.save_as_mainfile(filepath=str(R/'output/Incinerator_Editable.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.convert(target='MESH');bpy.ops.object.join();o=bpy.context.object;o.name='SM_Incinerator';bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
# Per-material shading preserved; lightmap UV available rather than overlapping project-space UV.
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
o.data.calc_loop_triangles();manifest['triangles_lod0']=len(o.data.loop_triangles);manifest['material_slots']=len(o.data.materials)
bpy.ops.export_scene.fbx(filepath=str(R/'output/SM_Incinerator_LOD0.fbx'),use_selection=True,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False)
for level,ratio in [(1,.50),(2,.20)]:
 dec=o.modifiers.new('LOD simplification','DECIMATE');dec.ratio=ratio
 dg=bpy.context.evaluated_depsgraph_get();eo=o.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles();manifest['triangles_lod'+str(level)]=len(me.loop_triangles);eo.to_mesh_clear()
 bpy.ops.export_scene.fbx(filepath=str(R/f'output/SM_Incinerator_LOD{level}.fbx'),use_selection=True,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False);o.modifiers.remove(dec)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'output/Incinerator_Game.blend'))
(R/'output/material_and_geometry_manifest.json').write_text(json.dumps(manifest,indent=2))
# Studio is excluded from exports and sources above.
p.group('Studio');p.cube('Studio floor',(0,0,-.035),(200,200,.06),p.mat('Studio backdrop',(.037,.049,.061),0,.85),0)
def light(name,loc,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;ob=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
light('Key',(-3,-4,5),950,3);light('Fill',(4,-2,3),750,3);light('Rim',(1,3,4),1100,2.5)
bpy.ops.object.camera_add(location=(3,-4.5,2.8));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,1.02))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.9
s=bpy.context.scene;s.camera=cam;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.world=bpy.data.worlds.new('StudioWorld');s.world.color=(.2,.2,.2);s.view_settings.view_transform='AgX';s.render.resolution_x=1400;s.render.resolution_y=1500;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(R/'output/Incinerator_Perspective.png');bpy.ops.render.render(write_still=True)
cam.location=(0,-5,1.3);cam.rotation_euler=(Vector((0,0,1.03))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/'output/Incinerator_Front.png');bpy.ops.render.render(write_still=True)
print('INCINERATOR_COMPLETE',json.dumps(manifest))
