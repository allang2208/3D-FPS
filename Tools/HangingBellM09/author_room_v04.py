"""Author and save the M09 ceiling room and anatomy physics asset. No PIE or render."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/MotionV04/Records')
DEST='/Game/Monsters/HangingBellM09/V04'
MAP='/Game/Tests/HangingBellM09/L_M09CeilingTest'
LIB=u.EditorAssetLibrary
mesh=u.load_asset(DEST+'/SK_M09')
pa=mesh.physics_asset
if not globals().get('M09_ROOM_ONLY',False):
 if not u.HangingBellM09.build_physics(mesh,pa):raise RuntimeError('M09 anatomy physics authoring failed')
 for asset in [pa,mesh]:
  if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Physics save failed '+asset.get_path_name())
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
if not world:raise RuntimeError('Could not create M09 level')
world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
ES=u.get_editor_subsystem(u.EditorActorSubsystem)
AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
def mat(name,color):
 path='/Game/Tests/HangingBellM09/Materials'
 a=AT.create_asset(name,path,u.Material,u.MaterialFactoryNew()) if not LIB.does_asset_exist(path+'/'+name) else u.load_asset(path+'/'+name)
 ME.delete_all_material_expressions(a)
 s=ME.create_material_expression(a,u.MaterialExpressionSubstrateShadingModels)
 c=ME.create_material_expression(a,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(*color,1)
 rough=ME.create_material_expression(a,u.MaterialExpressionConstant);rough.r=.72
 ME.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR);ME.connect_material_expressions(c,'',s,'BaseColor')
 ME.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS);ME.connect_material_expressions(rough,'',s,'Roughness')
 ME.connect_material_property(s,'',u.MaterialProperty.MP_FRONT_MATERIAL);ME.recompile_material(a)
 LIB.save_loaded_asset(a,False)
 return a
floor_mat=mat('M_M09Room_Floor',(.13,.16,.18))
roof_mat=mat('M_M09Room_Ceiling',(.3,.34,.37))
cover_mat=mat('M_M09Room_Cover',(.17,.22,.25))
mark_mat=mat('M_M09Room_Marker',(.65,.4,.06))
cube=u.load_asset('/Engine/BasicShapes/Cube')
def block(label,pos,size,material=cover_mat,ceiling=False):
 a=ES.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos),u.Rotator())
 a.set_actor_label(label);c=a.static_mesh_component;c.set_static_mesh(cube)
 c.set_material(0,material);c.set_collision_profile_name('BlockAll')
 a.set_actor_scale3d(u.Vector(*(v/100 for v in size)))
 if ceiling:a.set_editor_property('tags',[u.Name('M09Ceiling')])
 return a
def text(label,pos,rotation=180,size=24):
 a=ES.spawn_actor_from_class(u.TextRenderActor,u.Vector(*pos),u.Rotator(0,rotation,0))
 a.set_actor_label('Sign_'+label.split('\n')[0])
 c=a.get_component_by_class(u.TextRenderComponent)
 c.set_text(label);c.set_world_size(size);c.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
 c.set_text_render_color(u.Color(180,230,240,255))
 return a
# Main chamber: 20 x 16 m; open 4 x 4 m skylight at the far-right corner.
block('MainFloor',(0,0,-15),(2000,1600,30),floor_mat)
block('MainCeilingWest',(-200,0,430),(1600,1600,20),roof_mat,True)
block('MainCeilingEast',(800,-200,430),(400,1200,20),roof_mat,True)
block('BackWall',(1010,0,260),(20,1600,520))
block('EntryWall',(-1010,0,230),(20,1600,460))
block('SouthWall',(0,-810,230),(2000,20,460))
# Two side bays share ground access; their ceiling graphs are deliberately disconnected.
for cx,height,label in [(-500,360,'LOW 3.6 m'),(500,550,'HIGH 5.5 m')]:
 block(label+' Floor',(cx,1150,-15),(980,700,30),floor_mat)
 block(label+' Roof',(cx,1150,height+10),(980,700,20),roof_mat,True)
 block(label+' EndWall',(cx,1510,height/2),(980,20,height))
 text(label,(cx,1450,240),rotation=-90)
block('BaysOuterWest',(-1010,1150,275),(20,700,550))
block('BaysOuterEast',(1010,1150,275),(20,700,550))
block('BaysDivider',(0,1250,275),(20,500,550))
block('Pillar_A',(0,-300,210),(130,130,420))
block('Pillar_B',(420,-450,210),(130,130,420))
block('SolidTallCover',(150,100,155),(100,300,310))
block('LowCover',(-420,250,50),(180,100,100))
# Ground stripes show the unsupported skylight boundary; no invisible support is added.
block('SkylightWestStripe',(605,600,1),(10,400,2),mark_mat)
block('SkylightSouthStripe',(800,405,1),(400,10,2),mark_mat)
text('OPEN SKY\nNO CEILING SUPPORT',(970,600,240),rotation=180,size=22)
text('M-09 / CEILING CHAMBER\nF6: Hanging Bell M-09\nm09.AI 0  |  m09.Attack Gaze',(-980,0,240),rotation=0,size=22)
text('FALL AREA',(970,-550,210),rotation=180)
def route(label,points):
 a=ES.spawn_actor_from_class(u.M09CeilingRoute,u.Vector(),u.Rotator())
 a.set_actor_label(label);a.set_editor_property('grip_centers',[u.Vector(*p) for p in points])
 lookup={p:i for i,p in enumerate(points)};links=[]
 for i,(x,y,z) in enumerate(points):
  for other in [(x+200,y,z),(x,y+200,z)]:
   if other in lookup:links.append(u.IntPoint(i,lookup[other]))
 a.set_editor_property('links',links)
 return len(points),len(links)
graphs={}
graphs['main']=route('M09_Main420_Route',[(x,y,420) for x in range(-800,801,200) for y in range(-600,601,200) if not(x>=600 and y>=400)])
graphs['low']=route('M09_Low360_Route',[(x,y,360) for x in [-800,-600,-400,-200] for y in [1000,1200,1400]])
graphs['high']=route('M09_High550_Route',[(x,y,550) for x in [200,400,600,800] for y in [1000,1200,1400]])
for x,y,z in [(-650,-350,385),(150,450,385),(650,-350,385),(-500,1200,325),(500,1200,515)]:
 a=ES.spawn_actor_from_class(u.PointLight,u.Vector(x,y,z),u.Rotator());a.set_actor_label('M09Room_WorkLight')
 c=a.point_light_component;c.set_editor_property('intensity',5500.0);c.set_editor_property('attenuation_radius',1250.0)
 c.set_editor_property('light_color',u.Color(215,232,255,255));c.set_editor_property('cast_shadows',True)
 c.set_editor_property('mobility',u.ComponentMobility.MOVABLE)
start=ES.spawn_actor_from_class(u.PlayerStart,u.Vector(-750,-100,100),u.Rotator(0,0,0));start.set_actor_label('M09_PlayerStart')
portal=ES.spawn_actor_from_class(u.SceneTestPortal,u.Vector(-850,-620,0),u.Rotator(0,0,0))
portal.set_actor_label('M09_ReturnToHub');u.HangingBellM09.configure_return_portal(portal)
portal.get_component_by_class(u.TextRenderComponent).set_text('RETURN TO HUB\n[E] within 2 m')
# Save only this authored level and its newly authored materials.
if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('M09 map save failed')
pending=[p for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Tests/HangingBellM09/') or p.get_path_name().startswith(DEST)]
if pending and not u.EditorLoadingAndSavingUtils.save_packages(pending,False):raise RuntimeError('M09 pending save failed')
receipt={'map':MAP,'physics':pa.get_path_name(),'graphs':graphs,'main_ceiling_cm':420,'side_ceiling_cm':[360,550],'tested':False,'auto_spawned_monsters':0,'anatomy_physics_saved':not globals().get('M09_ROOM_ONLY',False)}
(ROOT/'ue_room_saved_v04.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('M09_ROOM_AND_PHYSICS_SAVED '+json.dumps(receipt))
