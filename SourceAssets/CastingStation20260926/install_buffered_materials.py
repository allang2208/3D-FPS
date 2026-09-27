"""Save two queue-timed variants; preserve the legacy casting materials and mesh."""
import sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir())
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
import author_furnace_casting as casting
names=['M_CastingStreamBuffered','M_CastingPoolBuffered']
targets={casting.DEST+'/'+name for name in names}
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Unsaved buffered casting target packages')
casting.solid_material(names[0],False)
casting.solid_material(names[1],True)
for metal in ['ironIngot','copperIngot','silverIngot','goldIngot']:
    instance=u.load_asset('/Game/Items/Smelting/Ingot/MI_'+metal)
    base=instance.get_base_material()
    if not base.get_editor_property('used_with_instanced_static_meshes'):
        if base.get_path_name().split('.')[0] in dirty:
            raise RuntimeError('Unsaved ingot parent material; keep editor work intact')
        base.set_editor_property('used_with_instanced_static_meshes',True)
        casting.save(base)
print('BUFFERED_CASTING_SAVED',casting.SAVED)
