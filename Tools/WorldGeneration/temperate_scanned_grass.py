"""Keep the same low, upright and bank slots when rebuilding the hills palette."""
import unreal as u

DEST = '/Game/WorldGeneration/TemperateHills/WetForest/ScannedGrass'
NAMES = ('SM_SoftWildGrassLow', 'SM_SoftWildGrassTuft')
BANK_REED = '/Game/WorldGeneration/TemperateHills/RiverEcologyDense/SM_RiverDense_grass_04_03_mesh'


def load_grass_palette():
    paths = [f'{DEST}/{name}' for name in NAMES]
    paths.append(BANK_REED)
    meshes = []
    for path in paths:
        mesh = u.load_asset(path)
        if not isinstance(mesh, u.StaticMesh):
            raise RuntimeError('Missing hills grass mesh: '+path)
        meshes.append(mesh)
    return meshes
