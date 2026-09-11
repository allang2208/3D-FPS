"""Persist four traversal fixtures in the initial map. Idempotent by actor label."""
import unreal,json,shutil,datetime
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
backup=root/'Saved/TraversalCourseBackups'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True,exist_ok=True)
shutil.copy2(root/'Content/GameMaps/DayNight_Lighting.umap',backup/'DayNight_Lighting.umap')
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().startswith('/Game/GameMaps/DayNight_Lighting.'), 'Open initial map before running this script'
api=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors={a.get_actor_label():a for a in api.get_all_level_actors()}
start=next(a for a in actors.values() if isinstance(a,unreal.PlayerStart));origin=start.get_actor_location();origin.z=0
mesh=unreal.load_asset('/Engine/BasicShapes/Cube')
tools=unreal.AssetToolsHelpers.get_asset_tools();dest='/Game/Movement/Traversal/TestCourse'
mat=unreal.load_asset(dest+'/M_TraversalCourse')
if not mat:
 mat=tools.create_asset('M_TraversalCourse',dest,unreal.Material,unreal.MaterialFactoryNew())
 node=unreal.MaterialEditingLibrary.create_material_expression(mat,unreal.MaterialExpressionVectorParameter,-250,0);node.set_editor_property('parameter_name','Tint');node.set_editor_property('default_value',unreal.LinearColor(.2,.4,.5,1))
 unreal.MaterialEditingLibrary.connect_material_property(node,'',unreal.MaterialProperty.MP_BASE_COLOR)
 rough=unreal.MaterialEditingLibrary.create_material_expression(mat,unreal.MaterialExpressionConstant,-250,180);rough.set_editor_property('r',.8);unreal.MaterialEditingLibrary.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
 unreal.MaterialEditingLibrary.recompile_material(mat);unreal.EditorAssetLibrary.save_loaded_asset(mat)
rows=[('Low',800,650,60,400,80,'LOW WALL\n80 cm / VAULT',(.12,.4,.18)),('Medium',800,1250,60,400,120,'MID WALL\n120 cm / VAULT',(.6,.28,.06)),('High',1550,650,200,400,180,'HIGH WALL\n180 cm / CLIMB',(.13,.28,.6)),('Platform',1550,1350,400,500,100,'PLATFORM\n100 cm / MANTLE',(.4,.15,.48))]
report=[]
for key,x,y,depth,width,height,title,color in rows:
 label='TraversalTest_'+key
 a=actors.get(label) or api.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
 a.set_actor_label(label);a.set_folder_path('Traversal Test Course');c=a.static_mesh_component;c.set_mobility(unreal.ComponentMobility.MOVABLE)
 c.set_static_mesh(mesh);a.set_actor_location(unreal.Vector(origin.x+x,origin.y+y,height/2),False,False);a.set_actor_scale3d(unreal.Vector(depth/100,width/100,height/100));c.set_collision_profile_name('BlockAll');c.set_mobility(unreal.ComponentMobility.STATIC)
 m=unreal.load_asset(dest+'/MI_'+key)
 if not m:
  m=tools.create_asset('MI_'+key,dest,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
 unreal.MaterialEditingLibrary.set_material_instance_parent(m,mat);unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(m,'Tint',unreal.LinearColor(*color,1));unreal.EditorAssetLibrary.save_loaded_asset(m);c.set_material(0,m)
 t=actors.get(label+'_Sign') or api.spawn_actor_from_class(unreal.TextRenderActor,unreal.Vector())
 t.set_actor_label(label+'_Sign');t.set_folder_path('Traversal Test Course');t.set_actor_location(unreal.Vector(origin.x+x-depth/2-2,origin.y+y,height*.55),False,False);t.set_actor_rotation(unreal.Rotator(pitch=0,yaw=180,roll=0),False)
 text=t.get_component_by_class(unreal.TextRenderComponent);text.set_text(title);text.set_world_size(20);text.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);text.set_text_render_color(unreal.Color(255,255,240,255));text.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
 center,ext=a.get_actor_bounds(False);assert abs(ext.z*2-height)<.1 and abs(center.z-ext.z)<.1
 report.append(dict(actor=label,height_cm=height,depth_cm=depth,width_cm=width,position=[center.x,center.y,center.z]))
assert level.save_current_level(),'Could not save initial map'
(root/'Saved/traversal_course_placement.json').write_text(json.dumps(report,indent=2))
unreal.log('TRAVERSAL_COURSE_SAVED four static obstacles and four signs')

eye=unreal.Vector(origin.x-100,origin.y+100,750)
target=unreal.Vector(origin.x+1150,origin.y+1050,50)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,target))
