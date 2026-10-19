# 法师套装背包图标标准化

范围：`ue_blue_mage_robe`、`ue_blue_mage_hat`、`ue_blue_mage_gloves` 的正式背包图标和图标专用展示网格。

## 显示入口与修正

三件物品除了目录 `ue_icon` PNG，还设置了 `ue_equipment_icon_mesh`。运行时 `ColdSteelEquipmentIcon.cpp` 将展示网格按物品保存的图标旋转放置，再由固定在 -X、朝 +X 的镜头拍摄。对于此类动态缩略图物品，背包和提示面板等待或失败时读取的是 `Content/ColdSteelData/Icons/<物品ID>.png`，并非条目 `ue_icon` 指向的家族子目录，也不读取本次保存的 UE Texture2D。制作必须同时发布该根目录 PNG、家族目录 PNG 和展示网格。

本次从当前模型和生产材质建立独立展示副本。PNG 镜头的相机空间同时导出为图标网格：朝向镜头的一面映射到 -X，画面右方映射 +Y，上方映射 +Z；保存时再抵消原目录的 `ue_icon_pitch/yaw/roll`。这样保持原物品和已持有实例的引用、角度字段不变，也让模型通道使用同一姿态。帽子显示正面与帽扣，手套从平放网格转为正对镜头；长袍显示完整空衣身。

## 正式图标合同

- 三件均用当前模型及 PBR，透明 RGBA、正交镜头、轮廓居中，主轴约 91% 填充。
- 长袍按 3×4 占格输出 240×320，完整保留领口和下摆；独立展示副本的双上臂各放低 12°。
- 帽子按 2×2 输出 320×320，保留弯尖和完整帽檐。
- 手套按 2×2 输出 320×320，单只空手套、自然分指，保留真实腕口，不出现皮肤、人台或第二只手套。
- 离线材质保留生产图集和材质分区，补入 ORM 的遮蔽信息；由同一机位的材质固有色计算目标亮度，再有限校准灯光渲染曝光，修正此前偏亮的蓝色。校准记录保存在各 `*-production.json`。
- Blender 的 `ortho_scale` 按图像长边定义，UE 的 `OrthoWidth` 始终按横向定义，两个端分别计算取景，避免竖幅裁掉衣物。

## 文件与后续制作

统一入口：`Tools/BlueMageSetIcons/render_icons.py`。只制作正式 PNG、独立展示场景和图标展示网格数据。`save_icons.py` 只保存三个已有图标展示 StaticMesh 和三个 UI Texture2D，不重导穿戴网格、掉落模型、骨架、动画或衣物物理。

作者输出：`SourceAssets/BlueMageSetIcons20261019/`，包含正式 PNG、每件独立 `.blend`、相机坐标展示几何、生产回执及 `Before/` 中的旧图备份。PNG 同步回各装备作者目录和当前 `Content/ColdSteelData/Icons/...` 路径。背包、装备栏和仓库继续共用现有引用。

三件装备原有完整作者／导入脚本已转接此标准入口，防止未来重新制作恢复旧曝光、画幅或展示朝向。物品属性、占格、目录路径和存档内容保持原样；不需要新增 C++。

UE 保存已完成：用户授权停止 PIE 后，执行时编辑器已退出，因此通过后台 commandlet 完成。最终 `hipfit-import-03` 返回 0，`SourceAssets/BlueMageSetIcons20261019/saved_icons.json` 已记录长袍、帽子、手套三个展示网格和三个 UI 纹理的实际保存路径与 PNG 哈希。长袍使用本轮修正后的腰胯轮廓。图标保存入口沿用项目的 commandlet 子系统构造方式，不要求启动编辑器。

本轮图标渲染及颜色、构图处理属于用户明确要求的制作内容；没有运行游戏、UI 回归或额外验收截图。已打开的 UI 可能保留旧 PNG／动态图缓存，下一次进入游戏会重新载入。

## 背包空白修复（2026-10-19）

用户反馈三件图标仍不显示后，定位到 `ColdSteelInventoryWidget.cpp:119` 与 `ColdSteelItemTooltip.cpp:124` 的动态物品回退路径。已有游戏日志分别报告 `Icons/ue_blue_mage_robe.png`、`Icons/ue_blue_mage_hat.png`、`Icons/ue_blue_mage_gloves.png` 不存在；同期动态长袍/帽子准备出现 `MaterialShader` 延后，后续帽子与手套已有动态捕获成功记录。上轮 UE 网格和纹理保存回执真实，但漏发根目录 PNG，不能据此认定背包显示链路完成。

已将三张现有标准 PNG 发布到上述根目录路径，复制后与生产源 SHA-256 一致；发布前这三个文件均不存在。`render_icons.py` 和 `save_icons.py` 均增加根目录 PNG 发布，后续制作与 UE 保存都保留此合同。未改 C++、装备数据或当前试玩状态，不需要重新编译与重导网格。

证据：`SourceAssets/BlueMageSetIcons20261019/runtime-fallback-missing-evidence.txt`；落盘回执：同目录 `runtime-fallback-publication.json`。背包 `FailedIcons` 与提示面板空纹理缓存会在当前控件生命周期内保留失败，因此用户需重新进入一次试玩以重新加载。此次未启动或重启游戏进行视觉验收。
