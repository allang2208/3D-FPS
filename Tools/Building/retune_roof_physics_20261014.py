import unreal as u
pal = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette')
NEW = {'thatch': 110000., 'roof_tile': 420000., 'roof_slate': 420000.}
entries = list(pal.get_editor_property('materials'))
for e in entries:
    eid = str(e.get_editor_property('id'))
    if eid in NEW:
        ph = e.get_editor_property('physics')
        ph.set_editor_property('tension_pa', NEW[eid])
        e.set_editor_property('physics', ph)
pal.set_editor_property('materials', entries)   # 整表回写(TArray 元素代理不会自动写回)
if not u.EditorAssetLibrary.save_loaded_asset(pal, False):
    raise RuntimeError('save failed')
for e in u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette').get_editor_property('materials'):
    ph = e.get_editor_property('physics')
    u.log('[tune] %s tens=%.0f shear=%.0f' % (e.get_editor_property('id'), ph.tension_pa, ph.shear_pa))
