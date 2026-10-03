"""Record actual save/build products; no tests or engine startup."""
import json,shutil
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
assets=json.loads((OUT/'ready_assets.json').read_text(encoding='utf-8-sig'))
build=json.loads((OUT/'build_installation.json').read_text(encoding='utf-8-sig'))
if build['exit_code']!=0:raise RuntimeError('Native build not complete')
receipt={
 'revision':'EyeChargeV14','assets':assets,'native_build':build,
 'active_attacks':['Sweep','Slam','EyeLaser'],'laser_animation_revision':'ThreeAttacksV13',
 'sweep_reach_cm':320,'sweep_hit_radius_cm':90,'sweep_contact_cm':250,
 'slam_reach_cm':300,'slam_hit_radius_cm':95,'slam_contact_cm':215,'melee_engagement_cm':340,
 'laser_focus':'Primary eye + forward 3 cm','laser_windup_seconds':1.5,
 'f6_entry_id':'HundredEyedSlag','native_class':'/Script/FPSGAME.HundredEyedSlagMonster',
 'runtime_tested':False,'preview_rendered':False,'editor_started':False}
(OUT/'installation_complete.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
status_file=ROOT/'production_status.json'
backup=OUT/'Before/production_status.json'
if not backup.exists():shutil.copy2(status_file,backup)
status=json.loads(status_file.read_text(encoding='utf-8-sig'))
status.update(active_revision='EyeChargeV14',working_revision='EyeChargeV14',
 stage='extended_sweep_and_reused_eye_charge_saved_and_built',revision_saved_asset_count=len(assets['assets_saved']),
 build_log=build['log'],native_build_required=False,native_class_built=True,
 melee_engagement_cm=340,melee_contact_cm=250,sweep_reach_cm=320,slam_reach_cm=300,
 sweep_contact_cm=250,slam_contact_cm=215,eye_charge_installation='EyeChargeV14/installation_complete.json',
 mesh_revision='ArticulationV12',eye_charge_revision='EyeChargeV14',laser_animation_revision='ThreeAttacksV13',
 tested=False,pie_tested=False,runtime_tested=False,preview_rendered=False)
status_file.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8-sig')
backup=OUT/'Before/README.md'
if not backup.exists():shutil.copy2(readme,backup)
marker='## 当前交付\n\n'
notice='当前使用 **EyeChargeV14**，普通横扫实际判定加长到 **320 cm**、查询半径为 **90 cm**，约 **250 cm** 即开始前摇；下劈维持 300 cm。眼部凝聚复用已有 MayuOrbs 红色能量材质、旋涡贴图与 ElectricMagic 蓄能粒子结构，改成贴眼核心、向内光丝和缩圈，取消悬浮汇聚球。六个新资产已后台保存，Editor 玩法模块基础 DLL 已常规构建；激光仍为待机、眼区轻微颤动、至少 1.5 秒蓄能，无提前量，仅横扫／下劈／激光三种攻击。未测试，由用户试玩。详见 `Docs/Monsters/hundred-eyed-slag-eye-charge-v14-20261001.md`。以下保留制作历史。\n\n'
if '**EyeChargeV14**' not in text:text=text.replace(marker,marker+notice,1)
readme.write_text(text,encoding='utf-8')
print('SLAG_V14_ASSETS_AND_BASE_EDITOR_DLL_DELIVERED_UNTESTED')
