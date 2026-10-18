# M870 原厂改造图标重制（2026-10-16）

用户反馈原厂枪托及原厂部件图标不合格。实际解析链为 `M4GunsmithLayout.cpp::OptionWidget`：原厂 `false` 优先查找本枪专属的 `FramedFirearms/<weapon>_<slot>_false.png`，不存在才退回通用图。M870 此前缺少这些专属图，因此显示了其他枪型的枪托、后握把、盒式弹匣或无配件符号。

本轮按 M870 当前实际枪体的原始 FBX 连通组件提取部件，用原贴图恢复表面并在独立 Blender 图标场景中转为灰阶。先渲染部件，再用内置 imagegen 以认可母版 `FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 约束厚金属方框、四角铆钉、银色内环和暗底，保持本枪轮廓。源模型、运行材质和动画不改。

| 实际原厂选项 | 专用图标键 | 来源 |
|---|---|---|
| 枪托 | `ue_m870_stock_false` | 一体式传统枪托，安装端向左 |
| 后握持部 | `ue_m870_reargrip_false` | 与枪托一体的握持颈部，复用同一完整实体图 |
| 泵动护木 | `ue_m870_underbarrel_false` | 原厂带肋护木及其动作杆 |
| 枪口 | `ue_m870_muzzle_false` | 原厂带齿圆孔枪口，出弹端向左 |
| 管式弹仓 | `ue_m870_magazine_false` | 真实细长管式弹仓，不再使用盒式弹匣图 |
| 机械瞄具 | `ue_m870_optic_false` | 单个原厂后照门及完整底座 |
| 手装填 | `ue_m870_reload_device_false` | 复用现有中性无装置符号，替换旧红色禁止弹药图 |

共新制 5 张独立母图，另复用 1 张中性无装置图，对应 7 个正式 PNG/Texture2D 键。无战术装置及通用改造仍沿用既有共享图；分类入口继续按既有逻辑使用共享分类图。没有为了图标更改部件名称、选项 ID、属性或存档。

正式路径为 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/`。纹理按 UI 组、Editor Icon 压缩、sRGB、Never Stream、无 mip 保存。本枪新键原先不存在，没有覆盖其他枪型或共享图片。当前面板有缓存时重新打开改造栏即可重新解析；本轮未运行游戏确认。

制作源：`SourceAssets/M870FactoryIcons20261016/`。`M870_FactoryIconSources.blend`、`render_sources.py` 和 `source_manifest.json` 保留实际模型、连通组件、相机方向和材质来源；`generation_manifest.json` 保存全部最终提示词、原始生成路径和键映射，`Generated/` 保留最终母图。PNG 部署回执见 `deployment.json`，UE 实际保存范围见 `import_receipt.json`。

本轮只进行用户要求的图标查看、制作、渲染及必要导入保存；没有启动游戏、PIE 或追加验收。没有改 C++，无需原生构建。图像来源为内置 imagegen，实际部件参考来自本机 M870 模型。

实际落盘：`icon-import-02` 后台 commandlet 退出码 0，`import_receipt.json` 为 `completed: true`，7 个专用 Texture2D 已保存。正式 PNG、UE 包路径及散列汇总于 `delivery.json`。首轮接入只因共享批次排队超时退出，没有发送导入请求；随后等待既有批次结束完成保存。
