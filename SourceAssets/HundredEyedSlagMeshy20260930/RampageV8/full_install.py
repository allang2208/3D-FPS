"""Save the source-driven revision; no gameplay, tests or rendering."""
import json, re, runpy
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
runpy.run_path(str(OUT/'install_runtime.py'))['install']()
mode='background_commandlet' if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else 'existing_editor_bridge'
completion = {'revision':'RampageV8','assets_saved':True,'mesh_assets_saved':2,
    'animation_assets_saved':2,'skeleton_saved':True,'runtime_paths_preserved':True,
    'motion_source':{'AttackSweep_R':'Epic Rampage Attack_Biped_Melee_A',
                     'AttackSlam_R':'Epic Rampage Ability_GroundSmash_Start + Ability_GroundSmash_End'},
    'skin_source':'Rampage source FBX skin profile, adapted to the existing right arm',
    'runtime_lod0_triangles':100000,'runtime_lod_count':3,'added_bones':0,
    'native_code_changed':False,'native_build_required':False,'hit_windows_preserved':True,
    'runtime_tested':False,'preview_rendered':False,'user_accepted_animation':False}
completion['execution_mode']=mode
(OUT/'installation_complete.json').write_text(json.dumps(completion,indent=2),encoding='utf-8')
status_path = ROOT/'production_status.json'
status = json.loads(status_path.read_text(encoding='utf-8-sig'))
status.update(active_revision='RampageV8',working_revision='RampageV8',stage='rampage_source_skin_and_two_attacks_saved',
    delivery='RampageV8/Delivery',rampage_installation='RampageV8/installation_complete.json',
    targeted_animation_roles=['AttackSweep_R','AttackSlam_R'],revision_saved_asset_count=5,
    pending_ue_animation_installation=False,right_limb_skin_saved=True,
    motion_source_available=True,motion_source_revision='Epic Rampage',
    native_code_changed=False,native_build_required=False,tested=False,animation_tested=False,
    runtime_tested=False,pie_tested=False,preview_rendered=False,user_accepted_animation=False,
    ue_editor_started_by_this_task=False)
status.pop('current_installation_blocker',None)
status.pop('candidate_delivery',None)
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
document=ROOT.parents[1]/'Docs/Monsters/hundred-eyed-slag-rampage-v8-20261001.md'
if document.exists():
    text=document.read_text(encoding='utf-8')
    text=text.replace('Blender 制作文件、实际供体数据、蒙皮和两条攻击 FBX 已导出。首次安装遇到正在播放的 PIE，接入脚本保留现场并退出，没有替换运行资产。最终保存状态以 `RampageV8/installation_complete.json` 为准；该文件生成之前不声称 UE 已使用新版本。',
        'Blender 制作文件、实际供体数据、蒙皮和两条攻击 FBX 已导出。现已互斥保存两份运行网格、两条攻击和公共骨架，三档 LOD 已重建并保存。实际执行方式记录在 `RampageV8/installation_complete.json` 的 `execution_mode`；网格和动作保存记录见 `mesh_installation.json` 与 `animation_installation.json`。当前 F6 及原生类继续引用原路径，使用新保存的资产；制作与落盘不代表视觉或玩法验收通过。')
    document.write_text(text,encoding='utf-8')
readme = ROOT/'README.md'
current = '''## 当前交付

运行时当前使用 `RampageV8`。ApeRecoveryV7 已被用户判定大右手打击力度、抬起幅度和关节不合格，不作为认可基准。

本轮使用已实际取得的 Epic Rampage 源动画：普通挥击适配 `Attack_Biped_Melee_A`；抬手重击适配 `Ability_GroundSmash_Start` 与 `Ability_GroundSmash_End`。读取完整肩臂、肘、腕关节运动，保留源动作的抬臂、快速落击和收势；躯干与肩部动作按目标体型适配，其他三肢支撑，大右手接地按实际掌部范围约束。蒙皮根据 Rampage 源 FBX 的真实骨骼权重分布沿目标肩—肘—腕臂链映射，配合肘腕体积支撑骨；不是再次自拟一套猩猩式攻击。

两份运行网格、两条攻击和公共骨架已导入并保存。保留原几何、UV、皮肤材质、绑定姿态、物理资产、十万三角形 LOD0、三档 LOD 和每顶点四个权重影响。源动作分段调整节奏以对齐现有普通攻击 0.54–0.73 秒、重击 0.84–1.00 秒伤害窗口；攻击总时长仍为 1.4/1.8 秒。F6、现有原生类及其他动作引用保持，此轮无需新增 C++ 编译。

实际来源、适配范围和保存记录见 `RampageV8/installation_complete.json`、`authoring_receipt.json` 以及 `Docs/Monsters/hundred-eyed-slag-rampage-v8-20261001.md`。使用已经运行的主工程编辑器完成互斥资产保存，没有主动打开、关闭或重启编辑器，没有启动游戏、PIE、渲染或测试。新效果仍需用户试玩，未宣称质量验收通过。

'''
old=readme.read_text(encoding='utf-8-sig')
if mode=='background_commandlet':
    current=current.replace('使用已经运行的主工程编辑器完成互斥资产保存，没有主动打开、关闭或重启编辑器',
        '使用无界面 commandlet 完成互斥资产保存，没有主动打开、关闭或重启交互编辑器')
readme.write_text(re.sub(r'## 当前交付\n.*?(?=- References/V2/)',lambda _:current,old,count=1,flags=re.S),encoding='utf-8')
print('HUNDRED_EYED_SLAG_RAMPAGE_V8_SAVED',flush=True)
