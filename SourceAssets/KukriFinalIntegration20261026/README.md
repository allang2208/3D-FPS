# Kukri 全面接入与正式改造图标 · 2026-10-26

> 三款刀身的当前表面及图标修订见 [KukriBladeSurfaceV220261026](../KukriBladeSurfaceV220261026/README.md)。其余图标保持本批版本；`manifest.json` 中三款刀身母图由 V2 部署脚本更新。重新执行本批图标导入前应先运行 `deploy_icons.py`，以使用最新母图生成部署回执。

本批承接 `KukriModules20261026`、`KukriBladeVariants20261026` 与 `KukriComponentVariants20261026`，保留五栏各三款、合计 15 款外观改造，不增加数值或机制。

## 图标生产与部署

- 运行菜单合并本武器目录与两个共享选项库，共 21 个选项入口（含五个原厂／空槽选项及无挂绳）和五个分类入口，使用 20 张独立母图。
- 17 张新图以实际模型／纹样素材和认可的 `FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 为参考，通过内置 imagegen 一项一图生成。保留已有原厂刀身、原厂挂绳及通用移除母图。
- 灰阶主体、厚倒角方框、四角铆钉、银色内圆环、深灰底板及极窄透明外缘；保留具体模型轮廓与穿孔。符文仅表达主印，分类使用折翼纹代表；无符文、无挂绳才使用减号。
- 通用改造使用共享键 `<slot>_<id>`；原厂件保留 `ue_kukri_<slot>_false`，分类使用本武器键。当前近战界面优先读取根目录共享改造图，无需改动缓存或逐帧加载逻辑。
- `manifest.json` 保存 26 个实际读取键、20 张母图、真实模型及输入来源；`Before/` 保留本轮替换前 PNG 与 Texture2D 包，作者源和中间渲染继续保留。
- `deploy_icons.py` 发布 PNG；`import_icons.py` 实际导入并保存相同键的 UE Texture2D，UI 纹理组、Editor Icon 压缩、sRGB、Never Stream，运行最大尺寸 1024。

后续重制模型时，旧批次的 `render_icons.py` 输出仅作为实际模型素材；完成旧批次模型／目录发布后，再执行本批 `deploy_icons.py` 和 `import_icons.py` 以保留正式图标。最终图标的 import source 指向本批持久母图。

## 接入范围

- 改造台的五栏选项、选中预览、应用／撤销和 `gunsmith_parts` 存档沿用已有系统。
- 主手、副手、双持和世界装备使用同一模块配方；刀身符文使用持久材质实例，移除时恢复对应刀身原材质。
- 背包动态图标和地面掉落沿用 `ColdSteelModularSword::Apply`；旧存档通过 `ue_kukri` 定义回退到同一模块目录。
- 普攻、动作、伤害、范围和强化数据不在本批修改；挂绳仍为静态配件，符文为无发光表面纹样。

制作、导入及构建状态分别以 `Receipts/` 为准。未启动游戏、运行测试或验收渲染，交由用户检查。

## 本批完成状态

- 17 次 imagegen 均返回成图，原文件已复制到 `Generated/`；另复用三张既有母图。提示词与工具返回路径见 `imagegen-receipt.json`。
- 26 个运行 PNG 已部署，26 个同名 Texture2D 已实际导入并保存，见 `Receipts/deployment.json`、`Receipts/import.json` 和 `Receipts/import-result.txt`。
- 已有编辑器中的 StopPIE 返回成功；随后关闭请求未发现可连接节点，常规构建提交前已无编辑器占用。本批没有强制结束进程，没有另开或重开编辑器。
- `FPSGAMEEditor Win64 Development` 常规增量构建 **Succeeded，退出码 0**，66 个动作，耗时 92.66 秒。基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已重新链接；此前仅 Live Coding 生效的材质描述代码已并入基础 DLL。证据为 `Receipts/build-editor-console.log`。
- Game 目标在上一批已常规构建成功；本轮没有追加 C++ 改动，仅补齐基础 Editor 构建和图标资产，未重复构建 Game。
- 游戏内外观、组合、存档和联机效果未测试；打开工程后从“尼泊尔弯刀 → 改造武器”进行用户检查。
