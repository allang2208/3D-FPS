# 魔法书内页方向与受击回收 V2

用户反馈：新增插画方向反转；上一版受击动作在接书时手指穿模，要求改成快速翻页、合书、下落到左手，再播放正常恢复动画。

## 只旋转内页图片方向

16 个插画面在各自 2×2 图集单元内旋转 UV 180°。保留同一原图、页面分配、纸张边缘、封面、几何、骨骼及原开合／阅读动画。原图没有重新生成或编辑。

制作入口：`SourceAssets/SpellbookEvildeer20261009/PagesV1/OrientationV2/rotate_uvs.py`；从本次 `Before/Spellbook_16Pages.blend` 读取，保存主制作源与网格 FBX，重复运行不会再旋转一次。主作者脚本 `PagesV1/author_pages.py` 同步了同样的逐页 UV 方向。

仅重导入并保存 `/Game/Weapons/SpellbookEvildeer20261009/PagesV1/Meshes/SK_Spellbook_Alchemy_16Pages`。原材质引用和骨架沿用，未修改纹理／材质／动画资产。原编辑器处于 PIE，首次保存被 UE 拒绝；结束已有 PIE 后保存成功，没有关闭或重启编辑器。

## 受击动作

V1 在书还在靠近时就混合到闭合握姿，手与书同时靠近接触点；V2 改为明确分开的等待、落掌和合指阶段。

| 阶段 | 实际时序 |
|---|---|
| 快速翻页 | 0–0.30 秒，从当前页进度连续采样已制作的翻页动画，快速翻向较远的一端。 |
| 合书与对齐 | 0.30–0.49 秒合拢封面和纸页，0.51 秒前移动到等待手掌上方；书脊、掌向按现有握点对齐。 |
| 垂直下落 | 0.51–0.75 秒，从握点上方 14 cm 加速落向同帧手部挂点。此段书已闭合，手指保持张开。 |
| 正常回握与恢复 | 0.75 秒落掌即随手，接入现有 V30 的 `SourceTime=1.28` 回程；用原返回时钟继续约 0.70 秒，原合指曲线负责在接触后握紧并回到待机。 |

整段约 1.45 秒。删除 V1 的额外手臂旋转冲击、提前合指及独立快速恢复混合。落掌前后共享同一手部姿态、书本挂点和源时间；接住之后不再对书另作位移插值。正常主动收书的动画数据与时序没有改变。

开书早期还未松手时受击，沿当前进度播放正常回程，不制造书本脱手或下落。减速、施法加成、快速近战限制、受击扣除最大魔法值 25% 和一次性扣除规则均沿用上一版。

代码入口：`SpellbookFocusInterruptMotion.h`、`SpellbookFocusInterrupt.cpp`、`SpellbookFocus.cpp`、`SpellbookFocusPose.cpp`。运行组件布局、数据属性及装备公式未改变。

## 交付范围

已后台制作并保存内页 UV 修正，动画由现有运行姿态层制作与接入，无新动画 uasset。构建结果见 `SourceAssets/SpellbookEvildeer20261009/Focus/InterruptV2/delivery.json`。未启动游戏、截图、渲染或执行自动测试；穿模和节奏的实际效果由用户体验。

现有编辑器 Live Coding 编译并应用成功，日志明确返回 `Live coding succeeded`；Win64 Development 游戏构建成功，已生成 `Binaries/Win64/FPSGAME.exe`。本次没有关闭或重启编辑器，也没有执行基础 Editor DLL 的完整重构建。
