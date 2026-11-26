"""Save four source shapes per mineral without rebuilding the ore surface graph."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/OreRockScaleVariants20261110'
DEST='/Game/WorldGeneration/TemperateHills/OreRocks'
MINERALS=('Iron','Copper','Silver','Gold')
E=u.EditorAssetLibrary

def backup(path):
    relative=path.split('.')[0].removeprefix('/Game/')
    for ext in ('.uasset','.uexp','.ubulk'):
        src=PROJECT/'Content'/(relative+ext);dst=ROOT/'Backups/Content'/(relative+ext)
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def build_variants():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Do not author during PIE')
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
    if dirty:raise RuntimeError('Preserve unsaved ore packages: '+repr(dirty))
    report={'saved':[],'source_shapes':{},'map_modified':False,'game_run':False,'visual_tested':False}
    materials={name:u.load_asset(DEST+'/MI_HillsOre_'+name) for name in MINERALS}
    for name,mi in materials.items():
        if not mi:raise RuntimeError('Missing ore material '+name)
    for shape in range(4):
        stem='SM_LS_Rock_0'+str(shape)+'A'
        source=u.load_asset('/Game/UnrealNormandy/StaticMeshes/'+stem)
        if not source:raise RuntimeError('Missing rock source '+stem)
        b=source.get_bounding_box();s=b.max-b.min
        report['source_shapes'][stem]={'size_cm':[s.x,s.y,s.z],
            'min_cm':[b.min.x,b.min.y,b.min.z],'sphere_radius_cm':source.get_bounds().sphere_radius,
            'nanite':source.get_editor_property('nanite_settings').enabled}
        for name in MINERALS:
            path=DEST+'/'+stem+'_'+name;backup(path)
            # Keep the existing 00A geometry/settings; add the three missing shapes.
            mesh=u.load_asset(path) or E.duplicate_loaded_asset(source,path)
            if not mesh:raise RuntimeError('Cannot create '+path)
            slots=list(mesh.get_editor_property('static_materials'))
            if not slots:raise RuntimeError('No material slot: '+path)
            # Per-shape dimensions keep the contact band independent of an
            # ISM component's combined bounds. Mineral appearance is inherited.
            material_path=DEST+'/MI_HillsOre_'+name+'_0'+str(shape)+'A'
            backup(material_path)
            mi=u.load_asset(material_path) or u.AssetToolsHelpers.get_asset_tools().create_asset(
                material_path.rsplit('/',1)[1],DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
            if not mi:raise RuntimeError('Cannot create '+material_path)
            u.MaterialEditingLibrary.set_material_instance_parent(mi,materials[name])
            bounds=mesh.get_bounding_box()
            u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'SourceMinZ',bounds.min.z)
            u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'SourceHeightCm',bounds.max.z-bounds.min.z)
            u.MaterialEditingLibrary.update_material_instance(mi)
            if not E.save_loaded_asset(mi,False):raise RuntimeError('Cannot save '+material_path)
            report['saved'].append(mi.get_path_name())
            for index in range(len(slots)):mesh.set_material(index,mi)
            if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+path)
            report['saved'].append(mesh.get_path_name())
    report['finished_at']=datetime.now().astimezone().isoformat()
    (ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
    (ROOT/'Receipts/assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.log('ORE_VARIANTS_SAVED '+str(len(report['saved'])))
    return report

if __name__=='__main__':build_variants()
