"""Install only; no runtime test or preview rendering."""
import json, re, runpy
from pathlib import Path
out = Path(__file__).resolve().parent
runpy.run_path(str(out/'install_runtime.py'))['install']()
completion = {
    'revision':'ApeRecoveryV7','assets_saved':True,'mesh_assets_saved':2,
    'animation_assets_saved':2,'skeleton_saved':True,'runtime_paths_preserved':True,
    'skin_attachment':'Shoulder-to-wrist arclength replaces height-based trunk pinning',
    'attack_rotation':'One transported bend plane, elbow hinge and outward recovery',
    'motion_source':'Original authoring; marketplace references not downloaded or retargeted',
    'runtime_lod0_triangles':100000,'runtime_lod_count':3,'added_bones':0,
    'native_code_changed':False,'native_build_required':False,
    'runtime_tested':False,'preview_rendered':False
}
root = out.parent
status_path = root/'production_status.json'
status = json.loads(status_path.read_text(encoding='utf-8-sig'))
status.update({
    'active_revision':'ApeRecoveryV7','working_revision':'ApeRecoveryV7',
    'stage':'ape_v7_skin_and_two_attacks_saved','delivery':'ApeRecoveryV7/Delivery',
    'ape_recovery_installation':'ApeRecoveryV7/installation_complete.json',
    'targeted_animation_roles':['AttackSweep_R','AttackSlam_R'],'revision_saved_asset_count':5,
    'pending_ue_animation_installation':False,'right_limb_skin_saved':True,
    'native_code_changed':False,'native_build_required':False,
    'tested':False,'animation_tested':False,'runtime_tested':False,'pie_tested':False,
    'preview_rendered':False,'ue_editor_started_by_this_task':False
})
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
readme = root/'README.md'
current = '''## 当前交付

运行时当前使用 `ApeRecoveryV7`。本轮针对大右臂仍然扭曲的问题，把按高度分配的躯干附着改成沿肩、肘、腕的实际臂链分配，并减少刚性臂段的辅助骨混合。普通挥爪与抬手重击改为统一弯曲平面和单肘铰链：抬臂、挥击、从身体外侧收手、最后回到撑地点。动作是本地原创的猩猩式重臂适配，没有下载或重定向商城源动作。

两份运行网格、两条攻击和公共骨架已后台导入保存。沿用十万三角形 LOD0、三档 LOD、2K 纹理、皮肤材质、UV、绑定姿态及原物理资产；其余动画关键帧保持。原有追击 340 cm/s、300 cm 接敌、约 130 cm 站稳再攻击、原伤害窗口与 0.42 秒死亡布娃娃交接保持。F6 和原生类引用保持。此次仅资产修改，不需要新增 C++ 构建，沿用 ClawV6 已完成的构建。

制作与保存记录见 `ApeRecoveryV7/installation_complete.json`、`mesh_installation.json`、`animation_installation.json`；复现入口为 `ApeRecoveryV7/Rebuild.ps1`。详细诊断和商城参考见 `Docs/Monsters/hundred-eyed-slag-ape-recovery-v7-20261001.md`。未启动交互 UE、游戏、PIE 或验收渲染，最终视觉效果由用户试玩确认；本轮没有调用 Meshy。

'''
readme.write_text(re.sub(r'## 当前交付\n.*?(?=- References/V2/)',lambda _:current,
    readme.read_text(encoding='utf-8-sig'),count=1,flags=re.S),encoding='utf-8')
(out/'installation_complete.json').write_text(json.dumps(completion,indent=2))
print('HUNDRED_EYED_SLAG_APE_RECOVERY_V7_SAVED',flush=True)
