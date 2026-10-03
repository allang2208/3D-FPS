"""Save the signature hand repair without running PIE, diagnostics or rendering a preview."""
from pathlib import Path
import runpy, json, re, unreal as u

out=Path(__file__).resolve().parent
module=runpy.run_path(str(out/'install_runtime.py'))
phases=('animations',) if '-herohandanimationsonly' in u.SystemLibrary.get_command_line().lower() else ('meshes','animations')
for phase in phases:
    module['install'](phase)
completion={
    'revision':'HeroHandV4','assets_saved':True,'runtime_paths_preserved':True,
    'mesh_assets_saved':2,'animation_assets_saved':19,'skeleton_saved':True,
    'physics_assets_saved':2,'added_deform_bones':6,
    'runtime_lod0_triangles':100000,'runtime_lod_count':3,
    'baked_normal_and_uv_preserved':True,'native_build_required':False,
    'runtime_tested':False,'preview_rendered':False
}
root=out.parent
status_file=root/'production_status.json'
status=json.loads(status_file.read_text(encoding='utf-8-sig'))
if 'saved_ue_checks' in status:
    status['runtime_v3_saved_ue_checks']=status.pop('saved_ue_checks')
status.update({
    'active_revision':'HeroHandV4','working_revision':'HeroHandV4',
    'stage':'hero_hand_v4_body_skin_actions_saved','delivery':'HeroHandV4/Delivery',
    'hero_hand_installation':'HeroHandV4/installation_complete.json',
    'bone_count':43,'deform_bone_count':39,'ue_bone_count':44,
    'added_support_bones':json.loads((out/'animation_contract.json').read_text())['added_bones'],
    'targeted_animation_roles':['Move','Run','AttackSweep_R','AttackSlam_R'],
    'animation_count':16,'animation_asset_count':19,'revision_saved_asset_count':24,
    'pending_ue_animation_installation':False,'hero_hand_meshes_saved':True,
    'preview_rendered':False,'authoring_contact_checked':False,'scoped_asset_checks_passed':False,
    'tested':False,'animation_tested':False,'runtime_tested':False,'pie_tested':False,
    'native_code_changed':False,'native_build_required':False,'ue_editor_started_by_this_task':False
})
status_file.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
readme=root/'README.md'
current='''## 当前交付

运行时当前使用 `HeroHandV4`。现有躯干骨骼已分段驱动重心、腰胸和背壳；大右臂新增六根辅助变形骨，并重分肩、肘、腕及指爪局部权重。奔跑/回程、普通横扫、抬手重击重新制作，其他动作同步新骨架。作者骨架 43 根骨骼、39 根变形骨，每顶点最多四个骨骼影响。两份网格、公共骨架、两份物理资产及十九个动画资产已后台导入保存，F6、原生类及 V1/PolishV2 引用保留。实际记录见 `HeroHandV4/installation_complete.json`、`mesh_installation.json` 和 `animation_installation.json`。

沿用 RuntimeV3 的十万三角形游戏表面、UV、高模烘焙法线、2K 运行纹理预算和三档 LOD。追击 280 cm/s、回程 120 cm/s、原伤害窗口和死亡 0.42 秒转布娃娃保持原合同。未运行游戏、PIE、截图或新预览渲染，由用户试玩。详细说明见 `Docs/Monsters/hundred-eyed-slag-hero-hand-v4-20260930.md`。

当前重建入口为 `HeroHandV4/Rebuild.ps1`：`-Stage Authoring` 只制作与导出，`-Stage Install` 后台安装已有导出，默认执行两者。V3 游戏表面及烘焙作为本次源保留；不要把原始百万面 FBX 重新作为游戏网格导入。没有重新调用 Meshy 或产生 API 费用。

'''
readme.write_text(re.sub(r'## 当前交付\n.*?(?=- References/V2/)',lambda m:current,readme.read_text(encoding='utf-8-sig'),count=1,flags=re.S),encoding='utf-8')
(out/'installation_complete.json').write_text(json.dumps(completion,indent=2))
print('HERO_HAND_V4_INSTALLATION_COMPLETE',flush=True)
