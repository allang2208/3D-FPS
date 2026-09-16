import unreal
D = '/Game/Props/RomanColumn20260915'; STONE = D + '/M_RomanStone_V2'
PAL = '/Game/Building/Voxels/DA_VoxelBuildPalette'
SV = unreal.ModelingService
col = unreal.EditorAssetLibrary.load_asset(D + '/SM_RomanColumn_Detailed')
print('[fix] column slots=%d' % len(col.get_editor_property('static_materials')))
print('[fix] column mat=%s' % col.get_editor_property('static_materials')[0].get_editor_property('material_interface').get_path_name())
pal = unreal.EditorAssetLibrary.load_asset(PAL)
soft = unreal.SoftObjectPath(STONE + '.' + STONE.split('/')[-1])
entries = pal.get_editor_property('components')
n = 0
for e in entries:
    if e.get_editor_property('id') in ('roman_column', 'balustrade_segment'):
        e.set_editor_property('surface', soft); n += 1
pal.set_editor_property('components', entries)
saved = unreal.EditorAssetLibrary.save_asset(PAL, False)
print('[fix] soft-path assign=%d saved=%s' % (n, saved))
back = unreal.EditorAssetLibrary.load_asset(PAL).get_editor_property('components')
for e in back:
    s = e.get_editor_property('surface')
    print('[fix]   %-20s -> %s' % (e.get_editor_property('id'), s.get_path_name() if s else None))
