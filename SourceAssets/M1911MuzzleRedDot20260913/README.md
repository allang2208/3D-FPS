# M1911 枪口卸载、制退器及全景红点修订

用户于 2026-09-13 反馈原厂枪口无法卸下消音器、红点过小和底座横向突出，并要求接入制退器。

## 修改

- `SetM1911Muzzle` 在原厂/空选择时隐藏并销毁旧枪口组件，清空指针及出口状态。此前只隐藏组件，`ApplyColdSteelProfile` 随后递归恢复整枪子组件可见性，导致卸下的消音器重新出现。
- 支持 `true`（消音器）/`brake`（制退器）之间替换网格、材质、安装变换及枪口出口；取消、应用、存档刷新和展示继续走已有公共装配入口。每次替换清除旧材质覆盖；制退器仍使用正常枪声和枪口效果。
- 全景红点只将 `Panoramic_Reticle` 几何沿圆面放大 **2.5 倍直径**，从约 0.558 mm 到 1.395 mm。光学中心 `(1.3175, 0, 2.015)` cm 及镜框尺寸保持不变。
- 红点底板由 **35 mm 收窄为 25 mm**，小于当前套筒约 25.58 mm 的宽度；保留 23.6 mm 外宽的原曲面双脚和照门避让，未横向挤压镜片/框体。
- 复用 `M4Muzzles20260910/brake-editable.blend` 的三组侧孔制退器，按 M1911 制作紧凑变体，保留侧孔和贯通内壁。主体长约 40 mm、外径约 24 mm，独立后接头衔接当前枪管；随 `WPN_Barrel`，导入前向为 UE -Y，出口 `(0, -3.4, 0)` cm。

## 游戏数据与材质

`Content/ColdSteelData/gunsmith.json` 的 M1911 枪口类别加入 `brake`，沿用现有制退器规则：后坐力 ×0.85、射击晃动 ×0.85、开镜耗时 +10%。图标直接使用现有 `AttachmentIcons20260913/muzzle_brake.png`，不新增不同形状的占位图。

新资源放在 `/Game/Weapons/M1911/MuzzleRedDot20260913/Meshes`，通过 `M1911WeaponAssets::AttachmentPath` 接入。消音器、全息、激光、手电继续使用上一版资源。打包目录已加入 AlwaysCook。

红点沿用当前 M1911 镜体/底座材质及原光学材质，UV3 重新按 10 cm 物理尺度投射。制退器使用当前 M1911 消音器的外部枪钢、暗内壁和接头材质，UV2 与现有材质一致，沿用已有雨滴映射。没有修改共享步枪模型、光学材质或天气库。

## 文件及交付边界

- `author_parts.py`：局部红点/底板修改与制退器适配；不生成预览。
- `assemble_editable.py`、`M1911_RedDot_Brake_Assembly_Editable.blend`：装在当前 M1911 源上的可编辑总装。
- 两个 `M1911_*_Editable.blend`、对应 `SM_M1911_*.fbx`：各配件可编辑源与导出。
- `import_parts.py`、`authoring.json`、`installed.json`：制作参数、导入入口及资源/材质记录。
- `build-editor.log`、`import-editor.log`：必要构建和资源导入日志。

沿用 `M4Muzzles20260910`、`PanoramicRedDot20260911` 与前两版 M1911 配件的来源和许可记录，没有新增外部素材或扩大公开再分发授权。

遵守用户规则：只完成制作、导入及必要编译，未启动游戏、未执行自动测试或验收渲染，交由用户测试。编译后需由用户重启已打开的 UE 编辑器加载原生变更。

本次导入脚本已保存两个网格并正常完成。命令行进程仍因工程已有 GameFeatureData/MCP 端口错误返回非零码，不将其写成游戏验收。必要 Editor 构建完成，模块为 `UnrealEditor-FPSGAME-913213511.dll`。
