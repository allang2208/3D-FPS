"""Record saved V13 assets and the regular native build; no tests."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
assets=json.loads((OUT/'ready_assets.json').read_text(encoding='utf-8-sig'))
build=json.loads((OUT/'build_installation.json').read_text(encoding='utf-8-sig'))
if not assets['material_saved'] or assets['animations_saved']!=3 or build['exit_code']!=0:
    raise RuntimeError('Three saved clips, material and regular module build required')
assets.update(native_build_pending=False,editor_base_dll_built=True)
(OUT/'ready_assets.json').write_text(json.dumps(assets,indent=2),encoding='utf-8')
p=OUT/'animation_installation.json';receipt=json.loads(p.read_text(encoding='utf-8-sig'))
receipt.update(native_runtime_build_pending=False,editor_base_dll_built=True)
p.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
completion=dict(revision='ThreeAttacksV13',animation_assets_saved=3,material_saved=True,
    active_attacks=['Sweep','Slam','EyeLaser'],attack_count=3,jump_attack_active=False,charge_active=False,ash_burst_active=False,
    sweep_reach_cm=260,slam_reach_cm=300,sweep_radius_cm=80,slam_radius_cm=95,melee_engagement_cm=340,
    laser_hand_raise=False,laser_charge_seconds=1.5,laser_prediction=False,eye_charge_sprite_count=64,
    eye_charge_exposure_compensated=True,mesh_revision='ArticulationV12',sweep_revision='RampageV8',slam_revision='RampageRecoverV9',
    editor_base_dll_built=True,gameplay_module_only=build['gameplay_module_only'],
    full_editor_target_built=build['full_editor_target_built'],game_executable_built=False,
    execution_mode=receipt['execution_mode'],runtime_paths_connected=True,tested=False,preview_rendered=False,editor_started=False)
(OUT/'installation_complete.json').write_text(json.dumps(completion,indent=2),encoding='utf-8')
p=ROOT/'production_status.json';status=json.loads(p.read_text(encoding='utf-8-sig'))
status.update(active_revision='ThreeAttacksV13',working_revision='ThreeAttacksV13',stage='three_attacks_and_visible_red_eye_charge_saved',
    special_attacks=['EyeLaserMagic'],active_attacks=['SweepPhysical','SlamPhysical','EyeLaserMagic'],attack_count=3,
    jump_attack_active=False,jump_slam_active=False,charge_active=False,ash_burst_active=False,
    special_attack_installation='ThreeAttacksV13/installation_complete.json',
    special_animation_installation='ThreeAttacksV13/animation_installation.json',special_animations_saved=3,
    special_runtime_build_pending=False,native_build_required=False,build_log=build['log'],
    laser_charge_seconds=1.5,laser_prediction=False,laser_hand_raise=False,
    tested=False,runtime_tested=False,pie_tested=False,preview_rendered=False)
p.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8-sig')
notice='当前使用 **ThreeAttacksV13**，只有 **横扫、下劈、眼部激光** 三种攻击。横扫／下劈前方判定分别扩展到 260／300 cm；激光保持待机、只轻微颤动眼区，1.5 秒红色粒子汇聚后发射，不计算提前量。三段激光动画与曝光补偿的红色柔光材质已保存，Editor 玩法模块基础 DLL 已常规构建；未测试，由用户试玩。跃砸已取消，下面保留历史记录。详见 `Docs/Monsters/hundred-eyed-slag-three-attacks-v13-20261001.md`。\n\n'
if notice not in text:text=text.replace('## 当前交付\n\n','## 当前交付\n\n'+notice,1)
readme.write_text(text,encoding='utf-8')
print('SLAG_V13_THREE_ATTACKS_DELIVERY_COMPLETE',flush=True)
