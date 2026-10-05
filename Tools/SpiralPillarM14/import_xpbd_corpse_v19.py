"""Rebuild M14 continuous corpse from live V15; reuse V18 normal repair materials."""
from pathlib import Path
import json, shutil, traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004'
OUT=ROOT/'ProductionV19'
DEST='/Game/Monsters/SpiralPillarM14'
E=u.EditorAssetLibrary
(OUT/'Records').mkdir(parents=True,exist_ok=True)
report={'complete':False,'saved':[],'tested':False,'rendered':False,'user_testing_pending':True}

def record():
    (OUT/'Records/ue_revision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def duplicate(source,path):
    return u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)

def main():
    backup=OUT/'Before/BP_SpiralPillarM14.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():
        shutil.copy2(PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset',backup)
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14')
    cdo=u.get_default_object(bp.generated_class())
    living=cdo.get_editor_property('visual_mesh')
    report['live_mesh_preserved']=living.get_path_name()
    report['previous_death_data']='V18 independent rigid frames and tissue tethers retired; one continuous deformation field'
    mesh=duplicate(living.get_path_name(),DEST+'/SK_M14_XPBDCorpse_v19')
    skeleton=duplicate(living.skeleton.get_path_name(),DEST+'/SKEL_M14_XPBDCorpse_v19')
    data_path=DEST+'/DA_M14_XPBDCorpse_v19'
    if E.does_asset_exist(data_path):
        data=u.load_asset(data_path)
    else:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
        data=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_M14_XPBDCorpse_v19',DEST,u.M14SoftBodyData,factory)
    if data.get_editor_property('corpse_mesh')!=mesh and not u.M14SoftBodyData.build_corpse(mesh,skeleton,data,str(OUT/'Exports/cage.json'),str(OUT/'Exports/embedding.bin')):
        raise RuntimeError('Could not build soft-body binding')
    materials=[];slots=list(living.get_editor_property('materials'))
    for slot in slots:
        source=slot.get_editor_property('material_interface')
        material=u.load_asset(DEST+'/SoftCorpseV18/'+source.get_name()+'_SoftCorpse')
        if not material:raise RuntimeError('Missing V18 normal repair material')
        slot.set_editor_property('material_interface',material);materials.append(material)
    mesh.set_editor_property('materials',slots)
    save(mesh);save(skeleton);save(data)
    # Preserve the repaired asset's actual binding for this defect investigation.
    export=u.AssetExportTask();export.object=data
    export.filename=str(OUT/'Records/repaired_data.t3d');export.automated=True
    export.exporter=u.ObjectExporterT3D()
    if not u.Exporter.run_asset_export_task(export):
        raise RuntimeError('Could not record repaired binding')
    cdo.set_editor_property('soft_body_death_data',data)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,corpse_mesh=mesh.get_path_name(),data=data.get_path_name(),
                  active_death='continuous XPBD tissue and metal field, local reinforcement, inelastic contact and strain damping',
                  living_mesh_changed=False,combat_changed=False)
    record()
    manifest_path=ROOT/'source_manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    manifest['current_revision']='ProductionV19'
    if 'pending_production_revisions' in manifest:
        manifest['pending_production_revisions']=[item for item in manifest['pending_production_revisions'] if item['revision']!='ProductionV19']
    manifest['production_v19']={'scope':'Remove detached rigid fields and long tethers; inelastic settling and continuous skin',
        'live_mesh_revision':'ProductionV15','venom_revision':'ProductionV16',
        'corpse_mesh':report['corpse_mesh'],'data':report['data'],
        'authoring':'Tools/SpiralPillarM14/author_continuous_corpse_v19.py',
        'importer':'Tools/SpiralPillarM14/import_xpbd_corpse_v19.py',
        'ue_saved':True,'tested':False,'user_testing_pending':True}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('M14_V19_XPBD_CORPSE_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
