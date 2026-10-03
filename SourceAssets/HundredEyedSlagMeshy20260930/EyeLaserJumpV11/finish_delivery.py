"""Record the completed saved assets and regular native build; no engine tests."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
PROJECT=OUT.parents[2]
assets=json.loads((OUT/'ready_assets.json').read_text(encoding='utf-8-sig'))
build=json.loads((OUT/'build_installation.json').read_text(encoding='utf-8-sig'))
if build['exit_code']!=0 or assets['animations_saved']!=8 or not assets['material_saved']:
    raise RuntimeError('Saved assets and regular native build required')
receipt_path=OUT/'animation_installation.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8-sig'))
receipt.update(native_runtime_build_pending=False,editor_base_dll_built=True)
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
completion=dict(revision='EyeLaserJumpV11',editor_base_dll_built=True,animation_assets_saved=8,
    full_editor_target_built=build.get('full_editor_target_built',True),gameplay_module_only=build.get('gameplay_module_only',False),
    material_saved=True,runtime_paths_connected=True,charge_active=False,ash_burst_active=False,
    laser_damage='magic',jump_slam_damage='physical',mesh_revision='RampageV8',
    sweep_revision='RampageV8',slam_revision='RampageRecoverV9',game_executable_built=False,
    tested=False,pie_tested=False,preview_rendered=False,editor_started=False)
(OUT/'installation_complete.json').write_text(json.dumps(completion,indent=2),encoding='utf-8')
p=ROOT/'production_status.json';status=json.loads(p.read_text(encoding='utf-8-sig'))
status.update(active_revision='EyeLaserJumpV11',working_revision='EyeLaserJumpV11',
    stage='eye_laser_and_native_jump_slam_installed',charge_active=False,ash_burst_active=False,
    charge_runtime_build_pending=False,native_build_required=False,
    special_attacks=['EyeLaserMagic','JumpSlamPhysical'],special_attack_installation='EyeLaserJumpV11/installation_complete.json',
    special_animation_installation='EyeLaserJumpV11/animation_installation.json',special_animations_saved=8,
    special_runtime_build_pending=False,laser_material_saved=True,charge_animation_installation='ChargeV10/animation_installation.json',
    build_log=build['log'],tested=False,runtime_tested=False,pie_tested=False,preview_rendered=False)
p.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
doc=PROJECT/'Docs/Monsters/hundred-eyed-slag-eye-laser-jump-v11-20261001.md'
text=doc.read_text(encoding='utf-8').replace('制作与导入阶段进行中。',
    '八条动画与激光材质已导入保存，原生源码已完成 FPSGAMEEditor 目标内 FPSGAME 玩法模块的常规编译并落盘基础 DLL。整项目首次构建被共享 AutoFootstep 插件 DLL 占用挡住，因此最终采用普通 UBT 的 `-Module=FPSGAME`；没有替换或重建占用中的插件 DLL。')
doc.write_text(text,encoding='utf-8')
readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8-sig')
notice='当前使用 **EyeLaserJumpV11**：冲锋替换为原地聚眼激光（魔法伤害），灰烬爆发替换为低伏、竖直跃起下砸（物理伤害）。八条动画、专用激光材质已导入保存，基础 Editor DLL 已常规构建，未测试；横扫 V8、巨臂下劈 V9 和网格/蒙皮 V8 保留。旧 ChargeV10 已退役，下面保留历史制作记录。详见 `Docs/Monsters/hundred-eyed-slag-eye-laser-jump-v11-20261001.md`。\n\n'
if notice not in text:text=text.replace('## 当前交付\n\n','## 当前交付\n\n'+notice,1)
readme.write_text(text,encoding='utf-8')
print('SLAG_EYE_LASER_JUMP_V11_DELIVERY_COMPLETE',flush=True)
