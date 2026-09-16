import unreal
def slots(path):
    a = unreal.EditorAssetLibrary.load_asset(path)
    if not a: print('[diag] missing', path); return
    m = a.get_editor_property('static_materials')
    print('[diag] %s slots=%d' % (path.split('/')[-1], len(m)))
    for i, s in enumerate(m):
        mi = s.get_editor_property('material_interface')
        print('[diag]   slot%d -> %s' % (i, mi.get_path_name() if mi else 'EMPTY'))
def mat(path):
    a = unreal.EditorAssetLibrary.load_asset(path)
    print('[diag] material %s loaded=%s' % (path.split('/')[-1], a is not None))
    if not a: return
    ex = unreal.MaterialEditingLibrary.get_material_expressions(a)
    print('[diag]   expressions=%d' % len(ex))
    for e in ex:
        print('[diag]   ', e.get_class().get_name())
slots('/Game/Props/RomanColumn20260915/SM_RomanColumn_Detailed')
slots('/Game/Props/RomanColumn20260915/SM_BalustradeSegment_20')
mat('/Game/Building/Voxels/M_Voxel_Stone')
mat('/Game/Props/RomanColumn20260915/M_Plaster_Detailed')
