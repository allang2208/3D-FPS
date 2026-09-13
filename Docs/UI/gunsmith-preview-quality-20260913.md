# 改造栏枪械预览清晰度

用户要求修复改造栏枪械和材质显示粗糙。本次交付为预览渲染、资源准备与必要构建；不启动游戏、不截图、不运行验收。

## 范围与接入

UMG 的 `UM4GunsmithWidget` 管理预览世界、资源与生命周期，Slate 继续显示现有中央预览区域。改造草稿和角色实际材质仍由现有 `UGunsmithSystem`／`AFPSGAMECharacter` 提供；强化／附魔独立预览复用同一实现。原背景、布局、字体、配件选择、旋转、焦点与保存入口不变。

## 实现

- 当前可见组件的贴图每秒续期一次 3 秒高清驻留请求。装配或材质槽变化立即更新；关闭和卸下配件后自然过期，不全局扩大流送池、不永久锁住资源。
- 展示副本选择 LOD0；替换网格时清除旧覆盖材质，再同步新枪或配件的实际材质。无变化的材质不反复赋值，失效组件从预览世界释放。
- 彩色捕获使用 UE 的 `FinalToneCurveHDR`，开启空间抗锯齿；原始 HDR 覆盖率单独低成本捕获，保留枪托镂空和镜片透明，不修改全项目 alpha 设置。新增 `M_WeaponPreviewResolved` 合成两张纹理，旧 UI 材质不改写。
- 按实际 DPI 后的显示尺寸做至多 2 倍超采样，最长边限制 2048。颜色与覆盖率保持相同尺寸和投影。
- 操作、初次预载和贴图实际流送期间以 30 Hz 更新，静止后 5 Hz；不等待 GPU／贴图加载而阻塞界面。
- 关闭时释放两张渲染目标、捕获组件和临时资源引用。

## 资源与交付

新增素材生成入口：`Tools/AssetPipeline/build_gunsmith_preview_resolved.py`，只生成项目自有 UI 合成材质 `/Game/UI/GunsmithWorkbench/M_WeaponPreviewResolved`。二进制保存在本机 Content，源码脚本可恢复；没有新增第三方资产。

修改前共享源码副本：`Saved/GunsmithPreviewQuality20260913/Before`。该副本包含当时已有的并行改动，只用于定位本次修改边界，不用于整体覆盖回退。

完成后重新启动编辑器加载新模块。实际材质亮度、透明边缘与交互效果由用户测试，本次不宣称实机验收通过。

必要构建记录：UI 合成材质生成进程正常退出，保存标记为 `GUNSMITH_PREVIEW_RESOLVED_MATERIAL_SAVED`；`FPSGAMEEditor Win64 Development` 构建成功，模块 `UnrealEditor-FPSGAME-9131541.dll`。日志位于 `Saved/GunsmithPreviewQuality20260913`。

`FPSGAME Win64 Development` 同样构建成功，生成 `Binaries/Win64/FPSGAME.exe`。两种目标仅完成构建，没有启动运行。

## 共享源码发布边界

两份既有预览源码包含本轮开始前尚未发布的独立预览、正交取景和其他 UI 修改。运行文件直接在 D 盘工程接入；为避免夹带这些既有修改，Git 发布本轮材质生成器、本文及 `SourceAssets/GunsmithPreviewQuality20260913/runtime-integration.patch`。补丁包括本次两个共享文件的增量和新增资源辅助实现，基线／交付散列见同目录 `integration-boundary.json`；它不是对远端较旧 UI 的无条件整文件覆盖。

后续整理见 [归档与技能沉淀](gunsmith-session-cleanup-20260913.md)；可复用方法已收录到 [UE UI 预览渲染参考](../../skills/ue5-ui-umg-slate/references/preview-rendering.md)。
