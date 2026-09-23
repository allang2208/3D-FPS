# SVD 贴图错位修复

用户截图：枪托、镜筒和旋钮显示贴图图集的错误区域。

## 根因与证据

SVD 几何来自 `svd_source.glb`，UE 材质使用原作者包中的 4096 贴图。GLB 内嵌的彩色贴图相对原包上下翻转，分件时沿用 GLB UV，却没有对原包贴图的方向作补偿。

`texture_compare.json` 比较同分辨率 RGB（0..255）的平均绝对误差：PSO 原方向 56.95，垂直翻转后 0.35；枪体原方向 29.96，垂直翻转后 0.39。其余差异来自 GLB 的图像重压缩。源模型修正前也复现错贴，排除了 UE 材质槽顺序作为根因。

## 修正

- 八个原始 SVD 分件的 UV0 使用 `V = 1 - V`，匹配原包 4K 贴图。没有改写第三方原图或 GLB。
- 更新八个源 FBX、机械分件 blend、当前完整骨骼模型 blend 及运行用 FBX。
- 更新分件脚本 `separate_svd_parts.py` 和 `Config/import_spec.json`，后续从 GLB 制作时只补偿一次。
- 手臂、枪机新增件、几何位置、骨架 rest、权重及 12 段动作不改。
- 原文件保留在 `Before/`，禁止整目录覆盖恢复其他并行修改。

`repair_source.py` 是本次已有源资产的一次性修复，不要重复运行；日后正常重制使用已修正的分件脚本。

## 记录

- `uv_repair_source.json`：源分件 UV 前后散列及几何不变记录。
- `SVD_Complete_Editable_quarter.png` / `_side.png`：修正后的源模型检查图，灰色手臂仅用于看接触。
- `import_fixed.json`：UE 重导入与保存记录，只有写入记录的目标才算已接入。

当前状态：当前骨骼模型及八个静态分件已通过后台 commandlet 重导入并保存。UE 后台正式资产渲染成功（`ue_Render_final.log`，`WeaponIconCatalog: COMPLETE failures=0`），结果为 `UE_SVD_fixed.png`，并更新目录图标。最终资产重载记录见 `final_readback.json`。未进行完整实机动作/战斗回归。

第一次导入的 9 个目标均已保存；随后额外尝试在 NullRHI 下导出骨骼 FBX 时触发引擎 MeshObject 断言，因此没有把该导出当作成功证据。修复确认改用具有图形上下文的 UE 后台正式资产渲染；图标渲染启用 `-NoTextureStreaming` 让本次离线捕获完整载入贴图。
