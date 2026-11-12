"""Assign the existing Project Nature flower meshes to the local forest clearings."""
import unreal as u


DATA = '/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming'
FLOWERS = '/Game/PN_FoliageCollection/Meshes/flowerMesh'


def assign_clearing_flowers(assets):
    families = []
    for names in (('04_02', '04_03', '04_04'), ('02_01', '02_03', '02_04')):
        variants = []
        for name in names:
            path = f'{FLOWERS}/flower_{name}'
            mesh = u.load_asset(path)
            if not isinstance(mesh, u.StaticMesh):
                raise RuntimeError(f'Flower mesh unavailable: {path}')
            variants.append(mesh)
        family = u.TemperateFlowerFamily()
        family.set_editor_property('variants', variants)
        families.append(family)
    assets.set_editor_property('clearing_flowers', families)


if __name__ == '__main__':
    if any(p.get_path_name() == DATA for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError(f'Forest palette has unsaved edits: {DATA}')
    assets = u.load_asset(DATA)
    if not isinstance(assets, u.TemperateHillsAssets):
        raise RuntimeError(f'Forest palette unavailable: {DATA}')
    assign_clearing_flowers(assets)
    if not u.EditorAssetLibrary.save_loaded_asset(assets, False):
        raise RuntimeError(f'Unable to save {DATA}')
    u.log(f'CLEARING_FLOWERS_SAVED {DATA} families=2 variants=6')
