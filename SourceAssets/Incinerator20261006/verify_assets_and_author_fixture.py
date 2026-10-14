import unreal as u,json,re
from pathlib import Path
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/incinerator_20261006')
P=Path('D:/FPS3D/FPSGAME');E=u.EditorAssetLibrary
assert '-IncineratorAssetVerify' in u.SystemLibrary.get_command_line()
assert Path(u.Paths.project_dir()).resolve()==P.resolve()
report=json.loads((W/'ue_import_receipt.json').read_text(encoding='utf-8'))
mesh=u.load_asset('/Game/Building/Incinerator20261006/SM_Incinerator')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
assert sub.get_lod_count(mesh)==3
assert len(mesh.static_materials)==13
assert [mesh.get_num_triangles(n) for n in range(3)]==[40152,20076,8029]
checks=[]
for i,m in enumerate(mesh.static_materials):
    assert m.material_interface and m.material_interface.get_path_name()==report['materials'][i]['path']
    checks.append({'index':i,'slot':str(m.material_slot_name),'material':m.material_interface.get_path_name()})
sections=[]
for lod in range(3):
    slots=[sub.get_lod_material_slot(mesh,lod,s) for s in range(mesh.get_num_sections(lod))]
    assert len(slots)==13 and set(slots)==set(range(13)),(lod,slots)
    sections.append(slots)
convex=sub.get_convex_collision_count(mesh);assert convex==1,convex
pal=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
def norm(x):return re.sub(r'0x[0-9A-Fa-f]+','POINTER',str(x))
assert [norm(e) for e in pal.components if str(e.id)!='incinerator']==report['palette_entries_before'],'Other palette entries differ from before import'
entry=next(e for e in pal.components if str(e.id)=='incinerator')
assert entry.surface is None and entry.mesh==mesh
assert abs(entry.pivot_offset_cm.z+6.0500030517578125)<.001
report['verified_saved_reload']=True;report['simple_primitive_count']=sub.get_simple_collision_count(mesh);report['convex_collision_count']=convex
report['collision_count']=report['simple_primitive_count']+convex;report['lod_section_material_indices']=sections
(W/'ue_import_receipt.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
(P/'SourceAssets/Incinerator20261006/import_receipt.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('INCINERATOR_ASSET_RELOAD_PASS '+json.dumps({'slots':len(checks),'lod_sections':sections,'convex':convex,'unrelated_palette_entries_unchanged':True}))
MAP='/Game/Tests/Incinerator20261006/L_IncineratorAudit'
assert not E.does_asset_exist(MAP),'Test map already exists'
world=u.EditorLoadingAndSavingUtils.new_blank_map(False);assert world
world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
ES=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
floor=ES.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-10),u.Rotator())
floor.set_actor_label('Incinerator audit floor - isolated fixture')
floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
floor.static_mesh_component.set_collision_profile_name('BlockAll');floor.set_actor_scale3d(u.Vector(12,12,.2))
start=ES.spawn_actor_from_class(u.PlayerStart,u.Vector(0,-240,100),u.Rotator(0,90,0));start.set_actor_label('Isolated audit spawn')
sun=ES.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,500),u.Rotator(-40,-30,0));sun.light_component.set_editor_property('intensity',20.)
ES.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(),u.Rotator())
sky=ES.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,400),u.Rotator());sky.light_component.set_editor_property('real_time_capture',True)
pp=ES.spawn_actor_from_class(u.PostProcessVolume,u.Vector(),u.Rotator());pp.set_editor_property('unbound',True)
settings=pp.get_editor_property('settings')
for name,value in {'override_auto_exposure_min_brightness':True,'override_auto_exposure_max_brightness':True,'auto_exposure_min_brightness':2.,'auto_exposure_max_brightness':2.}.items():settings.set_editor_property(name,value)
pp.set_editor_property('settings',settings)
assert u.EditorLoadingAndSavingUtils.save_map(world,MAP)
fixture={'map':MAP,'floor_surface_z_cm':0,'actor_count':len(ES.get_all_level_actors()),'contains_placed_incinerator':False,'gameplay_tested':False,'note':'Runtime audit places one incinerator using real building API. This is a newly authored isolated fixture; no existing map was saved.'}
(W/'fixture_receipt.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
print('INCINERATOR_FIXTURE_SAVED '+json.dumps(fixture))
# Exit normally; never switch to another map to clean up Python-held world references.
