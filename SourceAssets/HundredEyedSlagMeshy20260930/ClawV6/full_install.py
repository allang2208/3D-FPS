"""Background installation only; no PIE, rendering or automated acceptance."""
import json, re, runpy
from pathlib import Path

out = Path(__file__).resolve().parent
runpy.run_path(str(out/'install_runtime.py'))['install']()
native = json.loads((out/'native_build.json').read_text(encoding='utf-8-sig'))
completion = {
    'revision':'ClawV6', 'assets_saved':True, 'runtime_paths_preserved':True,
    'mesh_assets_saved':2, 'animation_assets_saved':1, 'skeleton_saved':True,
    'existing_physics_assets_reused':2, 'added_bones':0,
    'runtime_lod0_triangles':100000, 'runtime_lod_count':3,
    'baked_normal_and_uv_preserved':True, 'other_animation_keys_preserved':True,
    'native_code_changed':True, 'native_build_succeeded':native['succeeded'],
    'native_build_log':native['log'], 'runtime_tested':False, 'preview_rendered':False
}
root = out.parent
status_file = root/'production_status.json'
status = json.loads(status_file.read_text(encoding='utf-8-sig'))
status.update({
    'active_revision':'ClawV6', 'working_revision':'ClawV6',
    'stage':'claw_v6_skin_and_attack_saved', 'delivery':'ClawV6/Delivery',
    'claw_installation':'ClawV6/installation_complete.json',
    'targeted_animation_roles':['AttackSweep_R'], 'revision_saved_asset_count':4,
    'pending_ue_animation_installation':False, 'right_limb_skin_saved':True,
    'chase_speed_cm_s':340., 'melee_engagement_cm':300., 'melee_contact_cm':130.,
    'attack_cooldown_s':1.25, 'recovery_s':.12,
    'native_code_changed':True, 'native_build_required':False, 'native_class_built':native['succeeded'],
    'build_log':native['log'], 'ue_editor_started_by_this_task':False,
    'tested':False, 'animation_tested':False, 'runtime_tested':False,
    'pie_tested':False, 'preview_rendered':False, 'authoring_contact_checked':False,
    'scoped_asset_checks_passed':False
})
status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
readme = root/'README.md'
current = '''## 当前交付

运行时当前使用 `ClawV6`。普通攻击采用本机 Mutant3 的 `ClawC` 肩肘动作作供体，适配为大右手抬起、向前斜向挥爪、收回撑地；三条支撑肢配合躯干重心变化。重新分配右臂肩、肘、腕局部权重并降低辅助扭转骨影响。作者骨架仍为 43 根、39 根变形骨，每顶点最多四个骨骼影响。原骨架、绑定姿态、几何、UV 与其他动作的关键帧保持。

两份运行网格、普通攻击和公共骨架已后台导入保存；沿用原拟合物理资产与皮肤材质，并从新蒙皮生成三档 LOD。原生近战先播放奔跑接近，站稳后才开始攻击计时，避免前摇推着撑地姿态滑动。接敌范围沿用 300 cm，追击 340 cm/s，近战到约 130 cm 再抬手；普通攻击仍为 1.4 秒、0.54–0.73 秒伤害窗口，死亡仍于 0.42 秒转布娃娃。F6 与原生类引用保持。常规后台构建已完成；未启动交互 UE、游戏、PIE 或渲染，由用户测试。

实际保存记录见 `ClawV6/installation_complete.json`、`mesh_installation.json`、`animation_installation.json` 与 `native_build.json`；本次说明见 `Docs/Monsters/hundred-eyed-slag-claw-v6-20261001.md`。当前重建入口为 `ClawV6/Rebuild.ps1`；`-Stage Authoring` 制作导出，`-Stage Install` 常规编译并后台导入，默认执行两者。沿用十万三角形 V3 游戏表面、2K 纹理和高模烘焙；未调用 Meshy 或新增 API 费用。ClawC 供体属于现有 Epic Khaimera 派生资产，源动作不是无版权素材，不单独公开再分发。

'''
readme.write_text(re.sub(r'## 当前交付\n.*?(?=- References/V2/)', lambda _:current,
    readme.read_text(encoding='utf-8-sig'), count=1, flags=re.S), encoding='utf-8')
(out/'installation_complete.json').write_text(json.dumps(completion, indent=2))
print('HUNDRED_EYED_SLAG_CLAW_V6_INSTALLATION_COMPLETE', flush=True)
