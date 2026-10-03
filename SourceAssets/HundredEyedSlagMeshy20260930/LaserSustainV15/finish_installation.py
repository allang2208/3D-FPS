"""Record the native build and laser balance without starting any application/test."""
import json,shutil
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
build=json.loads((OUT/'build_installation.json').read_text(encoding='utf-8-sig'))
if build['exit_code']!=0:raise RuntimeError('Native build not complete')
contract={'revision':'LaserSustainV15','native_build':build,'first_damage_pulse_s':0.,
 'laser_duration_s':.65,'laser_damage_interval_s':.13,'laser_damage_multiplier_per_pulse':.4,
 'default_magic_attack':35,'default_raw_damage_per_pulse':14,'default_pulse_count':5,'default_full_raw_damage':70,
 'expiry_damage_pulse_included':False,'damage_type':'UHandBrainMagicDamage',
 'active_attacks':['Sweep','Slam','EyeLaser'],'visual_revision':'EyeChargeV14',
 'assets_modified':False,'runtime_tested':False,'editor_started':False,'preview_rendered':False}
(OUT/'installation_complete.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
status_file=ROOT/'production_status.json';backup=OUT/'Before/production_status.json'
if not backup.exists():shutil.copy2(status_file,backup)
status=json.loads(status_file.read_text(encoding='utf-8-sig'))
status.update(active_revision='LaserSustainV15',working_revision='LaserSustainV15',
 stage='sustained_eye_laser_magic_damage_built',build_log=build['log'],native_build_required=False,native_class_built=True,
 laser_sustain_installation='LaserSustainV15/installation_complete.json',laser_continuous_damage=True,
 laser_damage_interval_s=.13,laser_damage_multiplier_per_pulse=.4,laser_full_raw_damage=70,
 laser_default_pulse_count=5,tested=False,pie_tested=False,runtime_tested=False)
status_file.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8-sig');backup=OUT/'Before/README.md'
if not backup.exists():shutil.copy2(readme,backup)
marker='## 当前交付\n\n'
notice='当前使用 **LaserSustainV15**：激光存续期间每 **0.13 秒**造成一次魔法伤害，默认 **0.65 秒共 5 次、每次基础 14、完整命中基础合计 70**（实际扣血经过原魔防与状态公式）。固定攻击时钟、每跳去重、当前遮挡过滤、打断／死亡／结束后停止伤害；V14 贴眼凝聚效果沿用，仍只有横扫／下劈／激光。Editor 玩法模块基础 DLL 已常规构建落盘，未运行测试。详见 `Docs/Monsters/hundred-eyed-slag-laser-sustain-v15-20261001.md`。以下保留制作历史。\n\n'
if '**LaserSustainV15**' not in text:text=text.replace(marker,marker+notice,1)
readme.write_text(text,encoding='utf-8')
print('SLAG_V15_CONTINUOUS_LASER_DAMAGE_BUILT_UNTESTED')
