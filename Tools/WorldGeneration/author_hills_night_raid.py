"""Background authoring only: save violet veil and map-local dynamic navigation; no gameplay."""
import json
import shutil
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
OUT=ROOT/'SourceAssets/HillsNightRaid20261115'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/WorldGeneration/HillsNightRaid'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
report={'gameplay_started':False,'saved':[]}

def save(asset):
    package=u.load_package(asset.get_path_name().split('.')[0])
    if not u.EditorLoadingAndSavingUtils.save_packages([package],False):
        raise RuntimeError('Package save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())

material=u.load_asset(DEST+'/M_NightPortalVeil')
if material is None:
    material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_NightPortalVeil',DEST,u.Material,u.MaterialFactoryNew())
elif E.get_metadata_tag(material,'HillsNightRaidOwner')!='20261115':
    raise RuntimeError('Preserve unowned portal material')
L.delete_all_material_expressions(material)
material.set_editor_property('two_sided',True)
material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
nodes={}
nodes['UV']=L.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-600,-160)
nodes['Time']=L.create_material_expression(material,u.MaterialExpressionTime,-600,-40)
for name,value,y in [('FlowTimeOffset',0.,100),('OpenAmount',1.,220)]:
    node=L.create_material_expression(material,u.MaterialExpressionScalarParameter,-600,y)
    node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value);nodes[name]=node
flow=L.create_material_expression(material,u.MaterialExpressionCustom,-220,0)
flow.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
inputs=[]
for name in nodes:
    entry=u.CustomInput();entry.set_editor_property('input_name',name);inputs.append(entry)
flow.set_editor_property('inputs',inputs)
flow.set_editor_property('code',(OUT/'NightPortalVeil.ush').read_text(encoding='utf-8'))
for name,node in nodes.items():
    if not L.connect_material_expressions(node,'',flow,name):raise RuntimeError('Material input: '+name)
if not L.connect_material_property(flow,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Emissive connection failed')
errors=L.recompile_material(material)
if errors:raise RuntimeError(str(errors))
E.set_metadata_tag(material,'HillsNightRaidOwner','20261115')
save(material)

report['portal_geometry']={}
for name in ('SM_GamedevPortal_Frame','SM_GamedevPortal_Energy'):
    mesh=u.load_asset('/Game/Props/GamedevPortal20260922/'+name)
    if not mesh:raise RuntimeError('Missing existing portal mesh '+name)
    bounds=mesh.get_bounding_box()
    report['portal_geometry'][name]={'min':[bounds.min.x,bounds.min.y,bounds.min.z],
                                   'max':[bounds.max.x,bounds.max.y,bounds.max.z]}
for path in ('/Game/Monsters/NurseZombie/BP_NurseZombie','/Game/Monsters/AI/BP_MonsterAIController'):
    if not u.load_asset(path):raise RuntimeError('Missing monster dependency '+path)

map_path=ROOT/'Content/GameMaps/L_TemperateHills_Initial.umap'
backup=OUT/'Before/Content/GameMaps/L_TemperateHills_Initial.umap'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(map_path,backup)
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_TemperateHills_Initial')
if not world:raise RuntimeError('Hills map unavailable')
report['previous_navigation']=[a.get_path_name() for a in u.GameplayStatics.get_all_actors_of_class(world,u.NavMeshBoundsVolume)]
if not u.HillsNavigationSystem.install_on_map(world):raise RuntimeError('Navigation authoring failed')
save(world)
report['map_backup']=str(backup)
report['navigation_system']='/Script/FPSGAME.HillsNavigationSystem'
(OUT/'authoring-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('HILLS_NIGHT_RAID_SAVED '+json.dumps(report,ensure_ascii=False))
