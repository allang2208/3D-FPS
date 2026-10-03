"""Record the actual saved assets and native build; no tests or engine launch."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
assets=json.loads((OUT/'ready_assets.json').read_text(encoding='utf-8-sig'))
build=json.loads((OUT/'build_installation.json').read_text(encoding='utf-8-sig'))
if not assets['mesh_saved'] or assets['animations_saved']!=8 or build['exit_code']!=0:
    raise RuntimeError('Saved mesh, eight clips and regular module build required')
assets.update(native_build_pending=False,editor_base_dll_built=True)
(OUT/'ready_assets.json').write_text(json.dumps(assets,indent=2),encoding='utf-8')
receipt_path=OUT/'animation_installation.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8-sig'))
receipt.update(native_runtime_build_pending=False,editor_base_dll_built=True)
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
contract=json.loads((OUT/'animation_contract.json').read_text())
completion=dict(revision='ArticulationV12',mesh_assets_saved=1,animation_assets_saved=8,
    editor_base_dll_built=True,gameplay_module_only=build['gameplay_module_only'],
    full_editor_target_built=build['full_editor_target_built'],game_executable_built=False,
    authored_support_weight_vertices=contract['authored_weight_vertices'],max_influences=4,
    lods=3,added_bones=0,giant_right_arm_skin_preserved=True,sweep_revision='RampageV8',
    slam_revision='RampageRecoverV9',laser_min_charge_seconds=1.5,eye_charge_particles=32,
    laser_prediction=False,fall_loop=False,fall_pose_clock='height_to_floor',
    runtime_paths_connected=True,execution_mode=receipt['execution_mode'],
    tested=False,pie_tested=False,preview_rendered=False,editor_started=False)
(OUT/'installation_complete.json').write_text(json.dumps(completion,indent=2),encoding='utf-8')
p=ROOT/'production_status.json';status=json.loads(p.read_text(encoding='utf-8-sig'))
status.update(active_revision='ArticulationV12',working_revision='ArticulationV12',
    stage='support_skin_articulated_jump_and_eye_charge_saved',
    special_attack_installation='ArticulationV12/installation_complete.json',
    special_animation_installation='ArticulationV12/animation_installation.json',
    mesh_installation='ArticulationV12/mesh_installation.json',
    special_animations_saved=8,special_runtime_build_pending=False,native_build_required=False,
    build_log=build['log'],laser_charge_seconds=1.5,laser_prediction=False,
    tested=False,runtime_tested=False,pie_tested=False,preview_rendered=False)
p.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8-sig')
notice='当前使用 **ArticulationV12**：三条支撑肢重新蒙皮；跃砸加入屈膝蓄力、伸腿起跳、空中收腿、按离地高度伸展和落地压缩；聚眼激光增加大手抬起、32 个内聚粒子与至少 1.5 秒蓄力，不计算提前量。新网格（三档 LOD）和八条特殊攻击片段已保存，Editor 玩法模块基础 DLL 已常规构建；未测试，由用户试玩。横扫 V8 与下劈 V9 保留。详见 `Docs/Monsters/hundred-eyed-slag-articulation-v12-20261001.md`。下面保留历次制作记录。\n\n'
if notice not in text:text=text.replace('## 当前交付\n\n','## 当前交付\n\n'+notice,1)
readme.write_text(text,encoding='utf-8')
print('SLAG_V12_SAVED_ASSETS_AND_MODULE_DELIVERED',flush=True)
