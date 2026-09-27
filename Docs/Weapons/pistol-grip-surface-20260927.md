# 半自动手枪通用握把防滑纹

2026-09-27：按用户确定的方案制作，首个宿主为 M1911。共用改造名称、数值与材质，每把枪使用自己的贴合薄片。左轮继续使用专用替换握把。

| 改造 | 效果 | 数据 |
| --- | --- | --- |
| 原厂纹理 | 保留原厂表面 | `false`，无倍率 |
| 细颗粒防滑纹 | 枪械稳定性 +15% | `pistol_grip_granular`，`stability_mult=1.15` |
| 橡胶菱形防滑纹 | 后坐力 −5%，枪械稳定性 +5% | `pistol_grip_diamond`，`recoil_mult=0.95`，`stability_mult=1.05` |
| 细点快握防滑纹 | 开镜耗时 −10%，枪械稳定性 −5%，后坐力 +5% | `pistol_grip_quickdot`，`ads_percent=-0.10`，`stability_mult=0.95`，`recoil_mult=1.05` |

稳定性沿用统一枪械稳定性属性，未新增独立镜头震动加成。三种选项互斥，使用现有 `reargrip` 槽；注册此系统的枪械将该槽显示为「握把防滑纹」。倍率和开镜增量继续由枪匠属性结算，存档仍保存已有部件 ID。

## 贴合制作

母版为 `SourceAssets/M1911RearRain20260913/M1911_RearFinish_Editable.blend`。由原枪左右木握把和枪架前握持面采样表面，生成三块连接到一个静态网格的薄片。侧片位于两颗原厂螺丝之间，前片位于扳机护圈以下。

薄片中心约 0.32 mm，外缘约 0.09 mm，封闭背面贴近原表面。使用原枪骨架网格坐标导出，挂到 `WPN_root` 后抵消其参考骨链变换。原木握把、螺丝、握把保险与既有手部动作保留，不隐藏原厂握把材质分区。

三套原创程序纹理分别使用细颗粒、浅菱形和低凸细点。共享 10 cm 物理平铺尺度，每套 1024 BaseColor / ORM / Normal；凹凸由法线表达。一个材质槽，LOD0 / LOD1 / LOD2 为 4218 / 2108 / 1054 三角形。图标为真实部件的 1024 RGBA 灰阶正交图，灰阶仅作用于图标场景。

几何是项目既有 M1911 游戏资产的贴合派生；原枪许可边界沿用项目来源记录。新增橡胶纹理为原创程序素材，未下载外部模型、标志或纹理。

## 通用接入

`gunsmith.json` 顶层 `pistol_grip_surface_options` 是唯一选项表，不放入会广播给所有枪械的 `common_options`。宿主在自己的定义中声明：

```json
"pistol_grip_surface": {
  "mesh": "/Game/Weapons/PistolGripSurface20260927/M1911/SM_M1911_GripSurface",
  "bone": "WPN_root"
}
```

`Weapons/PistolGripSurface.*` 在目录初始化时合并选项，在部件变化时装配薄片或切换材质；恢复原厂会销毁薄片组件。没有新增 Tick 或逐帧 JSON 解析。枪匠预览、物品图标、掉落模型和双持副手通过明确的宿主配置装配，避免独立预览世界缺少 GameInstance 时丢失外观。天气映射使用独立 DataAsset，Cook 目录已登记。

后续非左轮手枪复用三个 ID、材质和数值，只需按其原握把表面制作新的薄片，保持原骨架网格坐标、实际骨名和 10 cm UV 比例，注册宿主配置，并提供该枪自己的原厂及改造图标。不同枪型不直接复用 1911 的薄片几何。

## 制作文件与交付状态

- 作者目录：`SourceAssets/PistolGripSurface20260927`，包含可编辑 Blender、三档 LOD、FBX、九张纹理、五张 UI 图标、制作及导入脚本。
- 引擎资产目录：`/Game/Weapons/PistolGripSurface20260927`。
- 实际 UI PNG：`Content/ColdSteelData/AttachmentIcons20260913/ue_m1911_reargrip_*.png` 与 `ue_m1911_category_reargrip.png`。
- `import_receipt.json` 由实际导入逐包保存时生成；脚本成功保存全部资产后才发布目录配置。
- 源码与作者资产已制作，19 个引擎资产已实际导入保存（三档 LOD 网格、三材质、九纹理、五 UI 纹理、一天气映射资产），目录配置已发布。正式构建待编辑器释放模块后进行。

按用户规则未运行游戏、未自测、未做接触或视觉验收；制作图标的渲染属于 UI 资产生产，不是验收截图。
