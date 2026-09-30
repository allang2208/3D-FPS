# 201 R29 模型接入（Install30）

用户要求：替换当前 UE 201；旧版保留。

来源为 `../Refine29/LMG201_R29_Editable.blend`：新参考图生成的 Meshy 候选，经表面局部平整、端部重建、材质烘焙及分件。适配源保存为 `LMG201_R30_NativeFit.blend`，不修改 R29 原件。

## 接入范围

- 现用入口仍为 `/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`。替换该资产内的枪体表面，游戏、枪匠及物品预览继续使用原有资源身份。
- 当前 UE 内的 V7 手臂、原装弹匣、扳机和拉栓活动件直接保留其原生骨骼权重；不从旧 Blender 手臂回导，不导入动作，不更改玩法或存档。
- 新枪托、后握把与枪口保留可替换材质槽前缀。新瞄具写入现用独立静态部件，保持折叠轴；准星底座留在主体内，避免折叠时带走枪管套环。
- 上盖独立刚性绑定原有 `LMG201_Cover`。当前仍为弹匣换弹。
- 弹药袋和弹链仅导入独立静态部件，不加入现用持枪模型、不恢复已退役的弹箱换弹。
- 使用 R29 的颜色／法线／ORM 烘焙；法线导入时翻转绿色通道一次。袋体 ClothAtlas 放入 UV0，布料绒毛沿同源细节分布。枪械材质带 `WeaponWetness` 接口。

## 旧版保留及恢复

`delivery.json` 记录真正保存的 UE 备份路径与原始文件备份。

- UE 独立备份目录：`/Game/Weapons/LMG201/Install30/Previous`。
- 原始 uasset 字节备份：`Before/Weapons/LMG201/...`；旧材质及旧源文件均保留。
- 新版独立装配资产：`/Game/Weapons/LMG201/Install30/SK_LMG201_R30_Installed`。
- `restore_previous.py` 为明确请求恢复时使用的桥接脚本；安装不会执行它。
- 正式资产的导入来源更新为完整装配 FBX，避免常规重导回到旧枪体或只导入无手臂的部件 FBX。
- Material21 的当前绑定清单同步保留新版槽位，以防旧材质恢复钩子覆盖新版绑定。

## 制作入口

1. `author_fit.py`：适配、绑骨与 FBX 导出。
2. `materials.py`：贴图导入、材质编译与保存。
3. `install.py`：先保存旧资产，再导入部件、装配当前原生手臂、替换并保存现用模型。

UE 已打开时只经 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript ...` 的批次互斥接入。UE 已关闭时使用 `run_headless.ps1`，通过同一互斥锁运行无界面 Python commandlet 完成导入，不打开编辑器窗口。未启动游戏、未渲染或执行实机测试，外观及握持效果交由用户测试。实际完成状态以 `delivery.json` 为准，脚本存在不代表已导入。
