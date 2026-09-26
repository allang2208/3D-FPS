"""补齐采集素材在游戏中的材质使用标志（2026-09-25）。

症状与证据（用户实测编辑器日志 Saved/Logs/FPSGAME.log，树倒下的同一秒）：
    LogMaterial: Warning: Material /Game/Items/HarvestTimber/M_FallingCutEnd ... missing usage
        flag Nanite! Default Material will be used in game.
    LogMaterial: Warning: Material /Game/Items/HarvestTimber/M_TreeCutSurface ... missing usage
        flag InstancedStaticMeshes! Default Material will be used in game.
两个材质都缺"当前渲染路径所需"的使用标志，游戏里会被替换成默认材质：倒树的断面、
树桩的切面都会变成默认灰。根因在制作脚本里：SourceAssets/HarvestTimber20260913/
import_tree_sections.py 第 18-23 行只设了 two_sided 与 used_with_skeletal_mesh，
从未设 used_with_nanite / used_with_instanced_static_meshes。

本脚本只读检查 + 只改缺失的那几个标志，改完重编译并保存；可重复执行（幂等）。
按项目规则不启动编辑器：在编辑器空闲批次里用 Tools/AssetPipeline/mcp_call_codex.ps1
-PythonScript 或后台 UnrealEditor-Cmd -run=pythonscript 运行。
"""
import unreal as u

E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary

# 材质 -> 该材质实际渲染路径必须带的标志。倒树上半段是 Nanite 骨骼网格（断面材质在槽 2），
# 树桩切面画在静态实例上（ISM）。
FIXES = (
    ('/Game/Items/HarvestTimber/M_FallingCutEnd', ('used_with_skeletal_mesh', 'used_with_nanite')),
    ('/Game/Items/HarvestTimber/M_TreeCutSurface', ('used_with_instanced_static_meshes',)),
)

changed = []
checked = 0
for path, flags in FIXES:
    material = u.load_asset(path)
    if not material:
        u.log('HARVESTFLAG_MISSING_ASSET ' + path)
        continue
    checked += 1
    before = {flag: bool(material.get_editor_property(flag)) for flag in flags}
    if any(not value for value in before.values()):
        material.modify()
        for flag in flags:
            material.set_editor_property(flag, True)
        # 无头 commandlet 里 recompile_material 一定返回假（没有渲染/着色器编译环境），
        # 这**不是**失败：使用标志是 UPROPERTY，保存即持久化，着色器映射会在编辑器或游戏
        # 加载该资产时重建。2026-09-26 实测：这里直接 raise 会让整轮修复白跑（资产还没保存）。
        if not L.recompile_material(material):
            u.log('HARVESTFLAG_RECOMPILE_DEFERRED ' + path)
        if not E.save_loaded_asset(material, False):
            raise RuntimeError('Material save failed ' + path)
        changed.append(path)
    after = {flag: bool(material.get_editor_property(flag)) for flag in flags}
    u.log('HARVESTFLAG %s blend=%s before=%s after=%s' % (
        path, material.get_editor_property('blend_mode'), before, after))

u.log('HARVESTFLAG_DONE checked=%d changed=%d' % (checked, len(changed)))