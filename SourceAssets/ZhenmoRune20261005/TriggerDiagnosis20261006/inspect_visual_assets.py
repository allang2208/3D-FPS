from pathlib import Path
import sys,json
import unreal as u
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(u.Paths.project_dir())/'Tools/Skills'))
from build_fireball_assets import API,ref
s=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold')
r={'system_summary':API.call_method('GetSystemSummary',(s,)).export_text()}
for method in ('GetSystemData','GetEmitterData','GetEmitterTopology'):
    try:r[method]=API.call_method(method,(s,) if method=='GetSystemData' else (ref(s,'BaguaRisingGold'),)).export_text()
    except Exception as ex:r[method]=str(ex)
for en,stage in (('BaguaRisingGold','EmitterUpdateScript'),('','SystemUpdateScript')):
    for name in ('Life Cycle Mode','Loop Behavior','Loop Duration','Inactive Response'):
        try:r[en+'/'+name]=u.RainAssetEditor.read_input(s,en,stage,'EmitterState' if en else 'SystemState',name)
        except Exception as ex:r[en+'/'+name]=str(ex)
for label,path in (('material','/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/SoftGroundV3/M_ZhenmoSoftGround'),('texture','/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Textures/T_ZhenmoBaguaField')):
    asset=u.load_asset(path)
    r[label]={'path':asset.get_path_name()}
    for name in (('blend_mode','two_sided','shading_model','disable_depth_test') if label=='material' else ('srgb','compression_settings','virtual_texture_streaming')):
        r[label][name]=str(asset.get_editor_property(name))
(OUT/'visual_assets.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('ZHENMO_VISUAL_ASSETS '+json.dumps(r))
