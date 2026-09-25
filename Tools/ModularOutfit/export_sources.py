"""Export only the active viewmodel/body inputs for modular clothing authoring."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ModularOutfit20260924'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'Inputs').mkdir(exist_ok=True)
paths = {
 'Traversal': '/Game/Movement/Traversal/Native/SK_TraversalArms_AnimatedBounds',
 'Body': '/Game/Characters/Mannequins/PlayerBodySkin/SKM_Manny_PlayerSkin',
 'M4': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
 'AKM': '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
 'QBZ191': '/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny',
 'ASH12': '/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface',
 'M16': '/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny',
 'M1911': '/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny',
 'DW715': '/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny',
 'A762': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
 'SVD': '/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock',
 'PKM': '/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
 'RuneSword': '/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny',
 'FrostSword': '/Game/Weapons/FrostCrystalSword20260915/SK_FrostCrystalSword_Manny',
 'FrostArms': '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms',
 'Axe': '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe',
 'Pickaxe': '/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe',
}
for gun in ('DW715', 'M1911'):
    for side in ('l', 'r'):
        paths[f'{gun}_{side}'] = f'/Game/Weapons/PistolDualWield20260914/{gun}/{side}/SK_Dual_{gun}_{side}'
report = {}
for key, path in paths.items():
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Required current source missing: '+path)
    filename = OUT / 'Inputs' / (key+'.fbx')
    if not filename.exists():
        task = u.AssetExportTask()
        task.object = mesh
        task.filename = str(filename)
        task.automated = True
        task.prompt = False
        task.replace_identical = False
        task.exporter = u.SkeletalMeshExporterFBX()
        options = u.FbxExportOption()
        options.set_editor_property('level_of_detail', False)
        options.set_editor_property('collision', False)
        task.options = options
        if not u.Exporter.run_asset_export_task(task):
            raise RuntimeError('Export failed '+path)
    mats = mesh.get_editor_property('materials')
    report[key] = {'mesh': mesh.get_path_name(), 'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
        'materials': [{'slot': str(m.material_slot_name), 'material': m.material_interface.get_path_name() if m.material_interface else ''} for m in mats],
        'fbx': str(filename)}
(OUT / 'inputs.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MODULAR_OUTFIT_INPUTS', len(report))
