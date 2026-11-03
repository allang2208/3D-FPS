# 雷神之锤：静电场与线圈改造图标

本轮仅制作用户截图中的两项图标，并接入其实际 PNG 加载键和 UE Texture2D。模型、材质、挂点、属性和存档不变。

| 选项 | 当前模型源 | 实际图标键 |
| --- | --- | --- |
| 静电场 `static_field_grip` | `StaticFieldGripV3Game/StaticField_Editable.blend` 中的 V3 游戏合并网格 | `ue_thunder_god_hammer_grip_static_field_grip` |
| 线圈 `coil_grip` | `CoilGripV1/Coil_Editable.blend` 中的游戏合并网格 | `ue_thunder_god_hammer_grip_coil_grip` |

静电场旧图使用 `ue_thunder_god_hammer_grip_static_field`，缺少选项 ID 尾部的 `_grip`，与 `M4GunsmithLayout.cpp` 的 `武器_槽位_选项` 拼接不符。本轮添加正确键，保留旧作者素材和旧键，不修改选项 ID。

`author.py` 从当前游戏网格生成独立灰阶素材；不改写原作者场景。沿用 +Z 机械轴与安装朝向，水平正交相机绕握柄旋转约 15.6 度；不裁切、拉宽握柄。保留 PBR 法线、粗糙度与分区，灰阶助手只应用在图标专用材质副本。`*_icon.blend` 为可编辑图标源，`*_source.png` 为 1024 像素透明单件素材。

正式 `*_framed.png` 使用内置 imagegen，一项一图。以当前单件素材约束形态，以 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 约束厚倒角钢框、四角铆钉、银色内圆环和凹陷深灰底板。只在框外保留极窄透明边。完整提示词保存在各自 `*_prompt.txt`。

`mapping.json` 保存源模型、相机、素材与替换前文件信息。`install.ps1` 沿用 UE 资产批次互斥：已有编辑器则通过桥导入；否则后台 commandlet 导入并保存，不打开编辑器或游戏。`import_assets.py` 只处理表中两个键，替换前副本保存在 `Backups`，拒绝覆盖未保存的目标包。纹理设置为 UI、Editor Icon、sRGB、Never Stream、无 mipmap。

正式文件位置：`Content/ColdSteelData/AttachmentIcons20260913/<实际图标键>.png` 及同名 `.uasset`。以 `import_receipt.json` 的 `complete` 和逐项 `icons` 记录区分生成与实际保存状态。

未运行游戏、截图验收或回归测试，由用户自行查看效果。本轮无 C++ 变更，无需原生编译。
