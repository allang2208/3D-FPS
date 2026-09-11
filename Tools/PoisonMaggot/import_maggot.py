import unreal,json,math,sys
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME');source=root/'SourceAssets/PoisonMaggot20260911/delivery';out=root/'Saved/PoisonMaggot';out.mkdir(exist_ok=True)
dest='/Game/Monsters/PoisonMaggot';tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.EditorAssetLibrary;mel=unreal.MaterialEditingLibrary
report={}
sys.path.insert(0,str(root/'Tools/PoisonMaggot'))
from substrate_materials import connect_surface
def imp(path,name,options=None,folder=dest):
 t=unreal.AssetImportTask();t.filename=str(path);t.destination_path=folder;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True
 if options:t.options=options
 tools.import_asset_tasks([t]);a=unreal.load_asset(folder+'/'+name);assert a,(name,t.imported_object_paths);return a
opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
mesh=imp(source/'SK_PoisonMaggot.fbx','SK_PoisonMaggot',opt);clips={}
for name,duration in [('Idle',3),('Move',2.5),('Spit',3),('Death',1.8),('Hit',.6)]:
 opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
 a=imp(source/f'A_PoisonMaggot_{name}.fbx',f'A_PoisonMaggot_{name}',opt);assert abs(a.get_play_length()-duration)<.01;a.set_editor_property('enable_root_motion',False);a.set_preview_skeletal_mesh(mesh);lib.save_loaded_asset(a,False);clips[name]=a
report['clips']={k:v.get_play_length() for k,v in clips.items()}
def mat(name):
 m=unreal.load_asset(dest+'/Materials/'+name)
 if m:mel.delete_all_material_expressions(m)
 else:m=tools.create_asset(name,dest+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
 return m
skin=mat('M_PoisonMaggot_Skin');skin.set_editor_property('used_with_skeletal_mesh',True);skin.set_editor_property('two_sided',False);skin.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
for sem,prop in [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('Normal_DirectX',unreal.MaterialProperty.MP_NORMAL),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS)]:
 tex=imp(source/f'T_Maggot_{sem}.png',f'T_PoisonMaggot_{sem}',folder=dest+'/Textures');tex.set_editor_property('srgb',sem=='BaseColor')
 if sem=='Normal_DirectX':tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
 lib.save_loaded_asset(tex,False);n=mel.create_material_expression(skin,unreal.MaterialExpressionTextureSample);n.texture=tex
 if sem=='Normal_DirectX':n.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
 elif sem=='Roughness':n.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
 mel.connect_material_property(n,'R' if sem=='Roughness' else 'RGB',prop)
for prop,val in [(unreal.MaterialProperty.MP_SPECULAR,.32)]:
 n=mel.create_material_expression(skin,unreal.MaterialExpressionConstant);n.r=val;mel.connect_material_property(n,'',prop)
connect_surface(skin,True)
slots=mesh.get_editor_property('materials')
for i,slot in enumerate(slots):slot.material_interface=skin;slots[i]=slot
mesh.set_editor_property('materials',slots);pa=unreal.PoisonMaggotMonster.create_physics_asset(mesh);assert pa;lib.save_loaded_asset(pa,False);lib.save_loaded_asset(mesh,False);lib.save_loaded_asset(mesh.skeleton,False)
venom=mat('M_PoisonMaggot_Venom')
for prop,value in [(unreal.MaterialProperty.MP_BASE_COLOR,unreal.LinearColor(.025,.20,.004,1)),(unreal.MaterialProperty.MP_EMISSIVE_COLOR,unreal.LinearColor(.015,.06,.002,1))]:
 n=mel.create_material_expression(venom,unreal.MaterialExpressionConstant3Vector);n.constant=value;mel.connect_material_property(n,'',prop)
n=mel.create_material_expression(venom,unreal.MaterialExpressionConstant);n.r=.45;mel.connect_material_property(n,'',unreal.MaterialProperty.MP_ROUGHNESS);connect_surface(venom)
sound=imp(source/'S_Maggot_Spit.wav','S_PoisonMaggot_Spit',folder=dest+'/Audio')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);temp=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector());comp=temp.skeletal_mesh_component;comp.set_skeletal_mesh_asset(mesh);a=comp.get_socket_location('head');b=comp.get_socket_location('body_02');yaw=-math.degrees(math.atan2(a.y-b.y,a.x-b.x));report['rest_sockets']={n:str(comp.get_socket_location(n)) for n in ['body_02','body_05','head','mouth_socket']};actors.destroy_actor(temp)
bp=unreal.load_asset(dest+'/BP_PoisonMaggot')
if not bp:
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.PoisonMaggotMonster);bp=tools.create_asset('BP_PoisonMaggot',dest,unreal.Blueprint,f)
unreal.BlueprintEditorLibrary.compile_blueprint(bp);cdo=unreal.get_default_object(bp.generated_class());cdo.set_editor_property('visual_mesh',mesh);cdo.mesh.set_skeletal_mesh_asset(mesh);cdo.mesh.set_relative_rotation(unreal.Rotator(yaw=yaw),False,False);cdo.capsule_component.set_capsule_size(70,70,False);cdo.mesh.set_relative_location(unreal.Vector(0,0,-70),False,False)
for prop,key in [('idle_clip','Idle'),('move_clip','Move'),('spit_clip','Spit'),('death_clip','Death')]:cdo.set_editor_property(prop,clips[key])
cdo.get_editor_property('combat').set_editor_property('hit_clip',clips['Hit']);cdo.set_editor_property('venom_material',venom);cdo.set_editor_property('spit_sound',sound)
controller=unreal.load_class(None,'/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C');assert controller;cdo.set_editor_property('ai_controller_class',controller);cdo.set_editor_property('auto_possess_ai',unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED);lib.save_loaded_asset(bp,False)
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);test='/Game/Tests/PoisonMaggot/L_PoisonMaggot';assert level.new_level(test);world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();cube=unreal.load_asset('/Engine/BasicShapes/Cube')
ground=mat('M_AuditGround');n=mel.create_material_expression(ground,unreal.MaterialExpressionConstant3Vector);n.constant=unreal.LinearColor(.12,.14,.13,1);mel.connect_material_property(n,'',unreal.MaterialProperty.MP_BASE_COLOR);mel.recompile_material(ground);lib.save_loaded_asset(ground,False)
connect_surface(ground)
assert unreal.PoisonMaggotMonster.compile_material_assets([skin,venom,ground])
for material in [skin,venom,ground]:lib.save_loaded_asset(material,False)
def box(name,p,scale):
 a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*p));a.set_actor_label(name);a.static_mesh_component.set_static_mesh(cube);a.static_mesh_component.set_material(0,ground);a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_collision_profile_name('BlockAll');return a
box('Maggot_Floor',(0,0,-50),(60,60,1));box('Maggot_Obstacle',(0,0,180),(1.2,7,3.6))
start=actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(700,0,100));start.set_actor_rotation(unreal.Rotator(yaw=180),False)
spawner=actors.spawn_actor_from_class(unreal.PoisonMaggotSpawner,unreal.Vector(-700,0,72));spawner.set_actor_label('PoisonMaggot_TestSpawn');spawner.set_editor_property('monster_class',bp.generated_class())
sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,800),unreal.Rotator(pitch=-50,yaw=-35));sun.light_component.set_editor_property('intensity',3.0)
sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,700));sky.light_component.set_editor_property('intensity',1.0)
fill=actors.spawn_actor_from_class(unreal.PointLight,unreal.Vector(-500,-1300,450));fill.point_light_component.set_editor_property('intensity',60);fill.point_light_component.set_editor_property('attenuation_radius',2200)
assert unreal.MonsterAIController.build_navigation_bounds(world,unreal.Vector(0,0,250),unreal.Vector(2900,2900,700))
# Do not serialize empty, unfinished commandlet NavData. Runtime creates and builds it.
for a in actors.get_all_level_actors():
 if isinstance(a,unreal.RecastNavMesh):actors.destroy_actor(a)
assert level.save_current_level();assert level.load_level(test)
loaded=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.PoisonMaggotSpawner)];assert len(loaded)==1;assert loaded[0].get_editor_property('monster_class')==bp.generated_class()
report.update(mesh=mesh.get_path_name(),physics=pa.get_path_name(),blueprint=bp.get_path_name(),mesh_yaw=yaw,test_map=test,materials=[str(s.material_slot_name) for s in slots],saved_and_reloaded=True)
(out/'import.json').write_text(json.dumps(report,indent=2));unreal.log('MAGGOT_IMPORT_COMPLETE '+json.dumps(report))
