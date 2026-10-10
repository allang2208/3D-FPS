# Elemental staff heads V37

四款头部已接入正式路径；完整制作说明见 `../../../Docs/Weapons/staff-element-heads-v37-20261009.md`。

- 编辑源：`Staff_ElementalCrystals_V37.blend`
- 模型/贴图作者：`author_blender.py`，Blender 5.1 后台执行，仅制作和纹理烘焙，不渲染预览。
- UE 导入：`install_ue.py`，通过工程 `Tools/AssetPipeline/mcp_call_codex.ps1` 的现有编辑器互斥桥执行，PIE 活跃或目标资产未保存时停止。
- 生产 FBX 与材质清单：`Export/meshes.json`、`Export/materials.json`。
- 修改前实际 UE 输入：`Inputs/`、`inputs.json`；原包副本：`Before/Content/`。
- 制作/保存回执：`author-receipt.json`、`install-receipt.json`、`install-01.txt`。

保留四个头部的 ID、运行路径、安装面及照明参数，默认白水晶和玩法不变。未运行游戏、未测试、未获视觉验收。
