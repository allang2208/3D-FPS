# RSH-12 装备栏与背包图标修复

用户要求排查不符合标准的 RSH 手枪装备／背包图标。

## 原因

实际读取的目录图为 `Content/ColdSteelData/Icons/ue_rsh12.png`。旧图是 512×512 方图，枪口朝右、握把朝上，枪身上下颠倒。旧制作入口 `SourceAssets/RSH12Integration20261003/prepare_delivery.py` 对原始模型做独立软件投影，其 `up = cross(direction, right)` 指向负 Z，未沿用 UE 图标的瞄线和上方向。同时只使用原包 albedo 加简化光照，没有使用当前 UE 枪身材质。

`ColdSteelInventoryWidget::LoadIcons` 为该武器读取上述 PNG；`ItemBrush` 在运行时改造图准备完成后优先显示动态配方图，等待或失败时回退到目录 PNG。装备栏、背包和拖动共用此选择过程，不是装备栏单独读了另一张图片。

## 修改

- 通过现有 `ColdSteelWeaponIconCatalog -Definition=ue_rsh12` 制作正式图，采用 `/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny`、当前原厂装配、私有姿态层及 UE 材质；隐藏手臂，按可见枪械轮廓构图。
- 输出 480×320 RGBA 横图，对应现有 3×2 占格；枪口朝左、握把朝下，完整保留枪口、弹巢、护圈和握把，透明背景，无改造栏金属框。
- 替换正式 PNG 并通过当前编辑器的互斥桥导入保存 `/Game/ColdSteelData/Icons/ue_rsh12`：UI 纹理组、Editor Icon 压缩、sRGB、Never Stream、无 mipmap。
- 将原 `prepare_delivery.py` 改为调用新的 UE 制作入口，避免后续发布再次写回倒置的旧模型贴图。保留旧脚本、PNG 和 Texture2D 备份。

首次修订不修改武器材质、模型、数值、占格、玩家存档、UI 布局或动态改造缓存，没有 C++ 改动。用户随后指出枪身仍未保持水平，追加修订见下文。

## 交付

- 制作目录：`SourceAssets/RSH12InventoryIcon20261006`
- 可重建入口：该目录的 `export_icon.ps1` 与 `import_icon.py`
- 正式成图及备份：`ue_rsh12.png`、`ue_rsh12_previous.png`、`ue_rsh12_previous.uasset`
- 生产日志：`export-v1-commandlet.log`，目标写入完成，`failures=0`
- 已保存回执：`import_receipt.json`、`import-editor-01.txt`

按本次排查范围读取了实际图标和 UI 引用，并查看了新生成图的朝向、完整轮廓与构图。离线出图只读取已保存 UE 包并生成目录 PNG；纹理在已有编辑器内保存，没有启动／重启交互编辑器、进入游戏或改写玩家状态。未进行游戏内实测，已加载的图标缓存由用户重新进入游玩后刷新。

## 水平基准追加修订

用户对照其他手枪指出第一次修订的枪身仍有倾斜。参考当前 M1911 和 Dan Wesson 715 的目录图后，定位到图标统一使用 `WPN_FrontSight - WPN_RearSight` 作为水平轴，RSH 的瞄准挂点轴与实体枪管／导轨轴有偏差。第一次只重出了图，并未消除该偏差。

`ColdSteelWeaponIcons.cpp` 对 RSH 单独使用现有 `RSH12MuzzleAssets::Mount()` 的真实枪管安装方向，经当前 `WPN_root` 姿态转换后找平；其他手枪保持原流程。此修正同时用于目录图和运行时带配件的动态图。RSH 图标配方键增加 `barrel_frame=2`，使旧方向的图片及包围盒缓存失效。没有修改瞄准挂点、实战持枪、弹道或掉落物姿态。

本轮源文件和图标备份保存在 `SourceAssets/RSH12InventoryIcon20261006/BeforeHorizontal`。用户已保存并关闭 UE。共享工程随后完成的正式 Editor 构建包含本次 `ColdSteelWeaponIcons.cpp` 编译与 DLL 链接，摘录保存为同目录 `horizontal-build-evidence.txt`；源日志为 `SourceAssets/Monsters/LurkerM08/AudioV01/build-FPSGAMEEditor-20261006-045041.log`，结果 `Succeeded`。

只读出图使用已保存模型和新 DLL，不覆盖 UE 内容包；`horizontal-v2-commandlet.log` 记录 `key=ue_rsh12|barrel_frame=2` 并成功写入 PNG。最终图为 `ue_rsh12_horizontal_v2.png`，正式目录仍使用 `Content/ColdSteelData/Icons/ue_rsh12.png`。后续复用 `export_icon.ps1` 制作图片，`import_icon.py` 通过互斥接入窗口保存 UE 纹理。没有启动游戏或新的交互编辑器。

水平版本已通过后台导入保存为 `/Game/ColdSteelData/Icons/ue_rsh12`，见 `horizontal-import-commandlet.log` 和更新后的 `import_receipt.json`。图像仍为 480×320 透明画幅，SHA-256 为 `d2b8517fc109640cf1c2314b67c8f358d995460cebcd60fd46210e367adcccae`。已查看本次正式成图的枪管与导轨水平效果，未进入游戏实测。

## 弹巢机构层追加修订

随后用户指出弹巢错位，进一步查到轻量展示初始化提前返回，导致原设计用于出图的 RSH 私有姿态层实际未加载。上文早期版本关于“采用私有姿态层”的描述是制作意图，并未在当时生效；`horizontal_v2` 图像因此仍有约 3.58° 的弹巢倾斜。

现已在展示初始化中加载该层，并将配方键追加 `mechanism=1`。更新后的目录 PNG 和 UE Texture 均已保存，见 `mechanism-v3-commandlet.log` 和 `SourceAssets/RSH12Mechanics20261006/icon_import_receipt.json`。当前正式成图为后者目录的 `ue_rsh12_fixed.png`；枪管和弹巢均回到本枪实际装配坐标。拆分、换弹接触和根因详情见 [RSH 弹巢错位与换弹机构排查](rsh12-mechanical-presentation-20261006.md)。
