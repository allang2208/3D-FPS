"""Cook the Root Crown-specific continuous corpse and preserve its current PBR."""
import json,shutil,sys,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/RootCrown20261014/SoftDeathV01'
DEST='/Game/Monsters/RootCrown/SoftDeathV01';E=u.EditorAssetLibrary
sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'))
import corpse_materials
corpse_materials.DEST=DEST+'/Materials'
report={'stage':'binding_corpse','saved':[],'gameplay_tested':False,'rendered':False}
def record():(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(asset):
    if not asset or not E.save_loaded_asset(asset,False):raise RuntimeError('Corpse save failed: '+str(asset))
    report['saved'].append(asset.get_path_name());record()
try:
    if any(p.get_path_name().startswith('/Game/Monsters/RootCrown') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved Root Crown assets')
    item=json.loads((ROOT/'sources.json').read_text('utf8'))[0];source=u.load_asset(item['source']);mesh=u.load_asset(item['corpse'])
    source_file=PROJECT/'Content'/(item['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
    backup=ROOT/'Before/SK_RootCrown.uasset';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(source_file,backup)
    skeleton_path=DEST+'/SKEL_RootCrown_SoftCorpse'
    skeleton=u.load_asset(skeleton_path) or E.duplicate_asset(item['skeleton'],skeleton_path)
    data=u.load_asset(DEST+'/DA_RootCrown_SoftCorpse')
    if not data:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
        data=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_RootCrown_SoftCorpse',DEST,u.M14SoftBodyData,factory)
    if data.get_editor_property('corpse_mesh')!=mesh:
        count=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh)
        if count>1 and not u.SkeletalMeshEditorSubsystem.remove_lods(mesh,list(range(1,count))):raise RuntimeError('Cannot remove unmatched corpse LODs')
        folder=ROOT/'RootCrown'
        if not u.M14SoftBodyData.build_corpse(mesh,skeleton,data,str(folder/'cage.json'),str(folder/'embedding.bin')):raise RuntimeError('Root Crown corpse binding failed')
    slots=list(source.get_editor_property('materials'));materials=set()
    bp=u.load_asset('/Game/Monsters/RootCrown/BP_RootCrownRigPreview');defaults=u.get_default_object(bp.generated_class())
    for i,slot in enumerate(slots):
        current=defaults.get_editor_property('slash_material') if i==0 else slot.get_editor_property('material_interface')
        slot.set_editor_property('material_interface',corpse_materials.make(current,materials))
    mesh.set_editor_property('materials',slots);report['saved'].extend(sorted(materials))
    save(mesh);save(skeleton);save(data)
    u.M14SoftBodyData.bind_to_living_mesh(source,data);save(source)
    report.update(stage='soft_corpse_saved',source=source.get_path_name(),corpse=mesh.get_path_name(),data=data.get_path_name(),
                  unsupported_nodes=len(data.get_editor_property('unsupported_nodes')),collapse_in_place=data.get_editor_property('collapse_in_place'),
                  standard='M14 V19 continuous XPBD',ground_handoff_seconds=.65,airborne_handoff='current visible pose immediately',corpse_seconds=25)
    record();print('ROOT_CROWN_SOFT_CORPSE_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
