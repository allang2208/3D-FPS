import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
jobs=[]
for family in ('base','angled','vertical','prism','canted'):
    path='/Game/Weapons/A762/Integrated20260920/Animations/A_A762_reload_empty' if family=='base' else f'/Game/Weapons/A762/Accessories05/Animations/{family}/A_A762_{family}_reload_empty'
    a=u.load_asset(path)
    if not a:raise RuntimeError(path)
    jobs.append({'family':family,'asset':path,'source':list(a.get_editor_property('asset_import_data').extract_filenames()),
                 'seconds':a.get_play_length(),'skeleton':a.get_editor_property('skeleton').get_path_name(),
                 'compression':a.get_editor_property('bone_compression_settings').get_path_name()})
m=u.load_asset('/Game/Weapons/A762/Integrated20260920/SK_A762_Manny')
result={'animations':jobs,'mesh':{'asset':m.get_path_name(),'source':list(m.get_editor_property('asset_import_data').extract_filenames())}}
(O/'sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('A762_EMPTY_SUPPORT_SOURCES',result)
