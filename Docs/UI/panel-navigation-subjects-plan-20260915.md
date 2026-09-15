# 栏目图标去底与放大

用户要求取消三张入口图标背景、只保留主体，放大一倍，并参考 game-dev 悬停放大优化布局。直接制作和接入；不启动游戏或追加测试。

- 素材：内置 image_gen 去除原图框体后仍输出烘焙棋盘格的 RGB 图。用户随后明确授权改用本地抠图并完成接入，使用 rembg isnet-general-use 从这三张生成主体图提取 alpha。正式图为 512×512 RGBA，主体等比居中并占最长边约 84%。源、生成提示词、本地制作记录放 `SourceAssets/PanelNavigation20260915/SubjectOnly`，运行图为 `Navigation/*_subject.png`。原始生成源保留作来源。
- 常规图标由 44px 改为 88px。按钮所有状态不画底板、圆框或方框；选中用短侧线表示。纵排间距改为 25px，右边预留悬停扩张空间。
- 悬停／焦点以 game-dev 的 200ms CSS ease 和 1.25 倍缩放为基准，只放大主体，退出平滑复原；键位和命中区域不跟随缩放，避免位置跳动。快捷键保持右下角 1.2 秒闪动；放大后用 16px 字号，名称在左侧提示。
- 右抽屉预留图标、悬停外伸与 12px 间隔；仓库仍与背包等宽。矮窗先压缩纵向间距，可用高度不足时按剩余区域缩小入口，保持顶部资源和右下武器信息可见。
- UI 保留原点击、Caps／Tab／P、LeftAlt 鼠标模式、独立弹层转发和焦点合同。主体变换仅参与绘制，不写游戏数据、存档或物品状态。
- 必要构建继续使用 `Tools/Build/Build-Editor.ps1`；本轮未要求测试、截图或游戏预览。

## 完成记录

- 三张主体 RGBA 已写入 `Content/ColdSteelUI/Icons/Navigation`，HUD 当前加载 `status_subject.png`、`backpack_subject.png`、`skills_subject.png`；原始 RGB 仅作生成来源，未当作透明素材接入。
- 本地制作脚本为 `Tools/UI/export_navigation_subjects.py`，选用 rembg isnet-general-use CPU，做 alpha 处理、轻量边缘羽化和统一居中，不改主体颜色。源 alpha 图、运行路径与输出规格记录在 `SourceAssets/PanelNavigation20260915/SubjectOnly/local-cutout.json`；生成步骤与提示词记录在同目录 `generation.json`。
- 已完成无底无框按钮、88px 常规尺寸、200ms/1.25 倍悬停与返回、固定 16px 键位及闪动、当前页短侧线、矮窗适配、143px 抽屉留位。
- 必要编辑器构建结果为 Succeeded，日志 `Saved/BuildEditor/build-20260915-084425.log`；脚本等待并行构建结束后确认 Target is up to date，本次调用无新增编译动作。随后正式 PNG 已写入既有资源路径，无 C++ 改动。
- 未启动游戏、未运行自测、lint、回归、截图或视觉验收，由用户自行测试。

用户后续要求快捷键恢复青色：Caps／Tab／P 改用共享 NavigationKey #54D9DC，保留原 1.2 秒闪动、字号与阴影。源码和正式规则已修改；本次必要构建因编辑器仍打开被 Build-Editor.ps1 第 18 行阻止，待保存关闭后继续。未运行游戏测试。

后续双持状态栏改造的完整编辑器构建已成功（Saved/BuildEditor/build-20260915-090729.log），此前青色快捷键修改也随当前模块一并交付。未实机测试。
