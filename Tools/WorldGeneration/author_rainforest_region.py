"""Bind the river-bank rainforest field to the existing hills materials and PCG grass."""
from pathlib import Path
import runpy
import unreal as u

BASE='/Game/WorldGeneration/TemperateHills/'

def bind_grass_weight(graph):
    for pcg_node in graph.get_editor_property('nodes'):
        settings=pcg_node.get_settings()
        if not isinstance(settings,u.PCGStaticMeshSpawnerSettings):
            continue
        packer=settings.get_editor_property('instance_data_packer_parameters')
        if packer is None:
            settings.set_instance_packer_type(u.PCGInstanceDataPackerByAttribute)
            packer=settings.get_editor_property('instance_data_packer_parameters')
        if not isinstance(packer,u.PCGInstanceDataPackerByAttribute):
            raise RuntimeError('Grass instance data already uses a different packer')
        binding='PCGBegin(RainforestWeight)PCGEnd'
        selectors=list(packer.get_editor_property('attribute_selectors'))
        if selectors and selectors[0].export_text()!=binding:
            raise RuntimeError('Grass material custom data slot zero is already occupied')
        if not selectors:
            selector=u.PCGAttributePropertyInputSelector()
            selector.import_text(binding)
            packer.set_editor_property('attribute_selectors',[selector])

def author():
    names={'M_TemperateGround':'ground','PebbleShore/M_PebbleShoreGround':'ground',
           'Grass/M_TemperateMeadow':'grass'}
    paths=[BASE+key for key in (*names,'PCG_HillsGrass')]
    scripts=Path(u.Paths.project_dir())/'Tools/WorldGeneration'
    parameters=runpy.run_path(str(scripts/'restore_hills_grass_parameters.py'))
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    pending=dirty.intersection([*paths,parameters['COLLECTION']])
    if pending:
        raise RuntimeError('Unsaved changes in '+str(pending))
    # A fresh copy of the Fab pack only contains the stock wind fields. Restore
    # the published IDs before loading shaders that reference the hills fields.
    parameters['restore']()
    assets={p:u.load_asset(p) for p in paths}
    if not all(assets.values()):
        raise RuntimeError('Missing hills asset '+str([p for p,a in assets.items() if not a]))
    graph=assets[BASE+'PCG_HillsGrass']
    bind_grass_weight(graph)
    wet=runpy.run_path(str(scripts/'forest_wet_materials.py'))
    for name,source in names.items():
        mat=assets[BASE+name]
        wet['biome_region'](mat,source)
        errors=list(u.MaterialEditingLibrary.recompile_material(mat))
        if errors:
            raise RuntimeError(mat.get_name()+' '+str(errors))
    for path,asset in assets.items():
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):
            raise RuntimeError('Could not save '+path)
        u.log('HILLS_RAINFOREST_SAVED '+path)

if __name__=='__main__':
    author()
