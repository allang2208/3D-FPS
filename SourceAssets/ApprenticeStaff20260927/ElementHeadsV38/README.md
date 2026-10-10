# Three staff-head replacements V38

正式接入完成：熔岩材质不规则圆球、不透明白色冰晶、持续变幻的闪电核心。翠灵水晶保持 V37。

制作说明：`../../../Docs/Weapons/staff-element-heads-v38-20261009.md`。

作者：`author_blender.py`，可编辑模型 `Staff_ElementalCrystals_V38.blend`。三份 FBX 与十二张贴图位于 `Export/`。风暴核心的实时动画由 `core_displacement.hlsl` 和 `core_radiance.hlsl` 提供，Blender 文件保留其管体和分支参数。

引擎入口：`install_ue.py`，使用现有编辑器批次互斥桥导入、编译、保存。首次接入回执失败已由 `install-02.txt` 对应修复覆盖，最终完成状态见 `install-receipt.json`。`resume_own_partial.py` 仅用于恢复首次失败中本批自身创建的未保存材质。

旧资产副本：`Before/Content/`；修改前实际模型：`Inputs/`。未进行游戏测试或效果验收。
