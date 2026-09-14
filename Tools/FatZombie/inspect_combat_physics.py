"""Report stored body flags through C++; UE does not expose these arrays to Python."""
import unreal as u

mesh = u.load_asset('/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy')
if not u.FatZombie.prepare_combat_physics(mesh, False):
    raise RuntimeError('Cannot read fat zombie combat physics')
u.log('FAT_COMBAT_PHYSICS_READ')
