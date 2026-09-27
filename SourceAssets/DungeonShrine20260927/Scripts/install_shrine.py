"""Save the fixed shrine's geometry, materials and catalog. No generation or gameplay."""
import json,re,runpy,sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
revision=ROOT.parent/'DungeonShrineV2_20260927'
receipt=revision/'Receipts/install.json'
if receipt.exists() and json.loads(receipt.read_text(encoding='utf-8')).get('stage')=='saved':
    runpy.run_path(str(revision/'Scripts/install_room.py'),run_name='__main__')
    raise SystemExit(0)
BASE='/Game/Dungeons/Shrine20260927';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT:raise RuntimeError('Wrong project')
if UE.get_game_world():raise RuntimeError('Preserve active play; shrine save pending')
initial_dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+
    list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())}
if any('/gamemaps/l_dungeon_randomized' in p.lower() or p.startswith(BASE) for p in initial_dirty):
    raise RuntimeError('Preserve unsaved shrine or dungeon edits')
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve current unsaved map')
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Cannot load shrine map')
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
generator=next(a for a in actors.values() if isinstance(a,u.AuthoredDungeonGenerator))
statue=actors['DGN_Start_ShrineStatue']
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
(ROOT/'Before').mkdir(parents=True,exist_ok=True)
previous=generator.get_editor_property('module_catalog_json')
backup=ROOT/'Before/catalog.json'
if not backup.exists():backup.write_text(previous,encoding='utf-8')
report=dict(stage='preparing',materials=[],meshes=[],actors=[],tests_run=False)
def record():
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())

# Retain the approved fracture shader's projection, normal basis and bounded detail.
# StoneSurface_02A is an existing licensed stone surface, with R/H/AO/metal channels.
source='/Game/Dungeons/WallUpgrade20260924/Materials/M_MineralScanned'
master_path=BASE+'/Materials/M_ShrineStone'
master=u.load_asset(master_path) if E.does_asset_exist(master_path) else E.duplicate_asset(source,master_path)
if not master:raise RuntimeError('Missing approved mineral surface')
shader=(PROJECT/'SourceAssets/DungeonWallUpgrade20260924/Scripts/mineral_surface.ush').read_text()
shader=shader.replace('float3 orm=Texture2DSampleGrad(SurfaceTex,SurfaceTexSampler,uv,gx,gy).rgb;',
    'float4 rhaom=Texture2DSampleGrad(SurfaceTex,SurfaceTexSampler,uv,gx,gy);\nfloat3 orm=float3(rhaom.b,rhaom.r,0);')
(ROOT/'Authored/shrine_stone.ush').write_text(shader,encoding='utf-8')
sampler_for=runpy.run_path(str(PROJECT/'SourceAssets/DungeonRuinEarthwork20260921/Scripts/earthwork_materials.py'))['sampler_for']
textures={pin:u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_02A_'+suffix)
    for pin,suffix in [('ColorTex','BaseColor'),('NormalTex','Normal'),('SurfaceTex','RHAOM')]}
if not all(textures.values()):raise RuntimeError('Missing original stone PBR textures')
master.modify()
for node in L.get_material_expressions(master):
    if isinstance(node,u.MaterialExpressionCustom):node.set_editor_property('code',shader)
    elif isinstance(node,u.MaterialExpressionTextureObjectParameter):
        name=str(node.get_editor_property('parameter_name'))
        if name in textures:
            node.set_editor_property('texture',textures[name])
            node.set_editor_property('sampler_type',sampler_for(textures[name]))
L.recompile_material(master);save(master);report['materials'].append(master_path)
materials={}
for name,tile,normal,grain,brightness in [('MI_ShrineStoneWorn',115,.75,.45,.78),('MI_ShrineStoneCut',70,.95,.70,.92)]:
    path=BASE+'/Materials/'+name
    mi=u.load_asset(path) if E.does_asset_exist(path) else AT.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mi.modify();L.set_material_instance_parent(mi,master)
    for pin,tex in textures.items():L.set_material_instance_texture_parameter_value(mi,pin,tex)
    for pin,value in {'TileCm':tile,'DepthCm':0,'NormalStrength':normal,'GrainStrength':grain,
        'Brightness':brightness,'RoughnessScale':1.08,'GrainTileCm':25}.items():
        L.set_material_instance_scalar_parameter_value(mi,pin,value)
    L.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(.92,.88,.80,1))
    L.update_material_instance(mi);save(mi);materials[name]=mi;report['materials'].append(path)
materials['ShrineStoneSurface']=materials['MI_ShrineStoneWorn']
materials['ShrineStoneCut']=materials['MI_ShrineStoneCut']
materials['ShrineConcrete']=u.load_asset('/Game/Dungeons/AtmosphereV2/Materials/M_Concrete')
materials['ShrineConcreteCut']=u.load_asset('/Game/Dungeons/WallUpgrade20260924/Materials/MI_BrokenConcrete')
if not all(materials.values()):raise RuntimeError('Missing fracture material')
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_mesh_material_usage

records=json.loads((ROOT/'Authored/sections.json').read_text())['objects']
meshes={}
for item in records:
    path=BASE+'/Meshes/'+item['name']
    if E.does_asset_exist(path):
        mesh=u.load_asset(path)
    else:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.save=False
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
        options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
        task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Import failed '+path)
        original=u.load_asset(item['source_mesh'])
        settings=original.get_editor_property('nanite_settings').copy()
        mesh.set_editor_property('nanite_settings',settings)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        slot_name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        mesh.set_material(index,materials[slot_name])
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    ensure_mesh_material_usage(mesh)
    if mesh.get_editor_property('nanite_settings').enabled:
        if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Cannot build inherited Nanite geometry')
    save(mesh);meshes[item['actor']]=mesh;report['meshes'].append(path);record()

catalog=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend'](json.loads(previous))
assets={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
for entry in catalog['start_shrine']['statues']:
    mesh=u.load_asset(entry['mesh'])
    if not mesh:raise RuntimeError('Missing statue '+entry['id'])
    assets[mesh.get_path_name()]=mesh

before=[]
for label,a in actors.items():
    if label in meshes or label.startswith('DGN_A_Room_RU_') or label in (
            'DGN_A_AV2_RuinNiche_Floor','DGN_A_AV2_RuinNiche_Ceiling','DGN_A_AV2_AncientArch','DGN_A_AV2_AncientPlinth'):
        c=a.get_component_by_class(u.StaticMeshComponent)
        before.append(dict(actor=label,hidden=a.get_editor_property('hidden'),collision=a.get_actor_enable_collision(),
            mesh=c.static_mesh.get_path_name() if c and c.static_mesh else None,
            materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())] if c else []))
backup=ROOT/'Before/actors.json'
if not backup.exists():backup.write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
for label,mesh in meshes.items():
    actor=actors[label];component=actor.get_component_by_class(u.StaticMeshComponent)
    actor.modify();component.modify();component.set_static_mesh(mesh);component.set_editor_property('override_materials',[])
    report['actors'].append(label)
for label in ('DGN_A_Room_RU_OldMasonry','DGN_A_Room_RU_BackMasonry','DGN_A_Room_RU_VaultStones',
              'DGN_A_Room_RU_AncientArch','DGN_A_Room_RU_EmbeddedPlinth','DGN_A_Room_RU_BankFragments'):
    actor=actors.get(label)
    if not actor:continue
    component=actor.get_component_by_class(u.StaticMeshComponent)
    actor.modify();component.modify();component.set_material(0,materials['MI_ShrineStoneWorn'])
    report['actors'].append(label)
# These are the superseded props listed in the original room-interior manifest.
# The floor at Z=0 otherwise covers every flagstone at Z=-18 cm.
for label in ('DGN_A_AV2_RuinNiche_Floor','DGN_A_AV2_RuinNiche_Ceiling','DGN_A_AV2_AncientArch','DGN_A_AV2_AncientPlinth'):
    actor=actors.get(label)
    if not actor:continue
    actor.modify();actor.set_actor_hidden_in_game(True);actor.set_is_temporarily_hidden_in_editor(True);actor.set_actor_enable_collision(False)
    component=actor.get_component_by_class(u.StaticMeshComponent)
    if component:component.modify();component.set_visibility(False);component.set_collision_profile_name('NoCollision')
    report['actors'].append(label)
statue.modify();tags=[t for t in statue.tags if str(t)!='FutureBlessingAndQuest']
statue.set_editor_property('tags',list(dict.fromkeys(tags+[u.Name('DungeonStart.ShrineStatue')])))
generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
generator.set_editor_property('module_assets',list(assets.values()))
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if p.get_name() not in initial_dirty and ('/gamemaps/l_dungeon_randomized' in p.get_name().lower() or p.get_name().startswith(BASE))]
if not owned or not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Shrine package save failed')
(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
report.update(stage='saved',saved_packages=[p.get_name() for p in owned],statues=len(catalog['start_shrine']['statues']),
    runtime_requires_native_build=True)
record();print('SHRINE_ASSETS_AND_CATALOG_SAVED',json.dumps(report,ensure_ascii=False))
