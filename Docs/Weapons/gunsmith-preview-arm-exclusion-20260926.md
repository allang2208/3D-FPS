# 改造页手臂进入预览修复（2026-09-26）

## 排查结果

`UpdateGunsmithCapture` 递归收集 `AKMViewmodel` 的所有子组件。装备外观组件把裸臂、手套和衣袖作为带 `ModularOutfit` 标签的跟随网格挂在枪模下面，因此这些人体网格也被加入预览。旧版 `SetGunsmithInspection` 只隐藏源枪模中的 Manny 材质，无法隐藏独立装备网格。`SyncStudioPreview` 随后复制这些组件，并把它们的包围盒计入自动取景。

## 修复方案与实现

1. 非瞄准预览收集时排除 `ModularOutfit` 分支，包含其后代组件；瞄准预览保持持枪外观。
2. 在摄影棚副本统一隐藏人体材质，覆盖原生 Manny、手套、衣袖、手部及独立 V7 裸臂命名；保留护木等枪械材质。已装备和独立预览共用此逻辑。
3. 包围盒缓存和自动缩放读取副本的实际可见材质，使手臂不再撑大取景范围。颜色与覆盖通道沿用同一副本列表。
4. 移除页面切换对源模型手臂材质的显隐改写，保留源模型已有的装备遮挡规则。退出预览不再重新显示被服装系统遮盖的原生皮肤。

修改限于 `M4DrumVisual.cpp`、`M4GunsmithPreview.cpp`、`M4StandalonePreview.cpp`。无需修改模型、动画、装备配置或存档；没有新增 Tick、资源加载或全局缓存。

## 交付状态

- 源码已保存。
- 用户结束占用模块的游戏后，沿用工程已启动的后台 `FPSGAMEEditor Win64 Development` 构建。三个修改文件均已编译，`UnrealEditor-FPSGAME.dll` 已链接；结果 `Succeeded`，耗时 144.79 秒。日志：`Saved/BuildEditor/build-20260926-190331.log`。
- 本轮未启动编辑器、游戏或截图验收，实际页面表现由用户测试。
