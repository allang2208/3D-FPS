"""Read-only pre-build check: collision availability and editor dirty state."""
import unreal

meshes = [
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Wall',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Foundation',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Stairs',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Doorframe',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Ceiling',
]
for p in meshes:
    m = unreal.load_asset(p)
    if not m:
        unreal.log('PRE_MISSING ' + p)
        continue
    name = p.split('/')[-1]
    try:
        bs = m.get_editor_property('body_setup')
        if bs is None:
            unreal.log(f'PRE_COLL {name} body_setup=None')
            continue
        agg = bs.get_editor_property('agg_geom')
        box = agg.get_editor_property('box_elems')
        convex = agg.get_editor_property('convex_elems')
        sphyl = agg.get_editor_property('sphyl_elems')
        trace = bs.get_editor_property('collision_trace_flag')
        unreal.log(f'PRE_COLL {name} boxes={len(box)} convex={len(convex)} sphyl={len(sphyl)} trace={trace}')
    except Exception as e:
        unreal.log(f'PRE_COLL_ERR {name} {e}')

try:
    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    unreal.log('PRE_DIRTY_MAPS ' + ','.join(p.get_name() for p in dirty))
except Exception as e:
    unreal.log('PRE_DIRTY_ERR ' + str(e))
unreal.log('PRE_CHECK_DONE')