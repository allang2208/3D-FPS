# Super90 贴图坐标与改造预览修复

用户反馈：整枪表面出现错误的图集形状，改造预览底部出现独立子弹，枪体偏离中心。

## 贴图制作

原来的 `(1-u, 1-v)` 方案已由 `../Super90SurfaceAlignment20261007/` 修正。原始 FBX 的枪体 UV 与源 PNG 的左上原点图集直接对应，Blender 应使用 `(u, 1-v)`；不能把另一份转换后的 GLB 中 `KHR_texture_transform.rotation = pi` 直接套到源 PNG。

机匣两侧原始 UV 分别为 U=.3591–.4174 / V=.2255–.5544、U=.7315–.7894 / V=.6712–.9980，与 PNG 的两块刻字面板一致。旧方案额外翻转 U，错误采样到了握把与枪托区域。当前 `mapping.py` 将旧版本仅反转 U 迁移到正确坐标；未处理过的源只转换 V。随后按正确金属图重建 WS1 分区。顶点、骨架、蒙皮、动画、裸臂和装备 UV 不变。

`mapping.py` 由现有 WS1 和 Super90 主制作入口调用；网格版本 `SourcePNG-VFlip-20261007` 防止重复转换。枪体源法线为 DirectX，UE 的 `flip_green_channel=False`；其余原始手套、衣袖、弹壳和备弹夹法线转换保持各自原配置。保留公共 WS1 母材质、预设与原结构法线，不改动其他武器。

## 预览修复

`Source/FPSGAME/UI/M4GunsmithPreview.cpp` 对 Super90 的预览副本排除 `12gauge` 材质段，继承已有可见段包围盒计算，独立装填子弹不再参与显示或居中。真实持枪组件和换弹动画中的子弹保持原逻辑。

## 制作入口与交付范围

- Blender：`../Super90WS1Surface20261007/author_surface.py`。
- UE 资产导入保存：`apply_mapping.py`；编辑器关闭时通过 `../WeaponSurface20260930/run_ue.ps1` 无界面执行。
- 制作源同步：`../Super90WS1Surface20261007/publish_source.py`。
- C++ 必要编译：`Tools/Build/Build-Editor.ps1`，需先关闭已加载模块的编辑器。

保存进度见 `import_receipt.json`，先前源与资产在 `Before/`。未启动游戏、截图、渲染或测试，视觉结果由用户体验。
