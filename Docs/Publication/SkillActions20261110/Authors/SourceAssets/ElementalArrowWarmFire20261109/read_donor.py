import json, sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API,ref
system=u.load_asset('/Game/Skills/FlameArmor20261108/AllWeaponsV12/NS_FlameArmorWeapon')
rows=[]
for script in ['EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript']:
    for module in API.call_method('GetScriptStackInputValues',(ref(system,'WeaponFireballCore',script),)):
        name=str(module.get_editor_property('module_name'))
        rows.append(dict(script=script,module=name,inputs=[dict(name=str(i.get_editor_property('name')),
            value=str(u.RainAssetEditor.read_input(system,'WeaponFireballCore',script,name,str(i.get_editor_property('name')))))
            for i in module.get_editor_property('inputs')]))
result=dict(pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),core=rows)
(OUT/'donor-inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ELEMENTAL_FIRE_DONOR',json.dumps(result))
