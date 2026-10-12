# 魔法书 V26：接入已认可的开书与 recover

2026-10-12 后续调整见 [V27 书本方向、托掌起伏和开合节奏](spellbook-focus-v27-20261012.md)。本页保留 V26 接入记录。

用户已认可 V23 整体翻转、V24 松指开书和 V25 倒放 recover，并于 2026-10-11 要求接入游戏。该版本替代此前 V18 开书及 V9/V11 收书路径。

## 动作与接入

- 保留原待机抓握，手腕、五指及书本固定关系不变，前臂带动手和书整体逆时针转动 180°；0.90 秒到位。
- 0.95 秒以后才松指，1.28–1.94 秒两侧封面沿书脊展开，使用预览中的书脊倾角、页面弯曲及手臂下移。书本落点仍为 `(44,-19,-14)` cm。
- 1.95 秒进入悬浮阅读，沿用原 16 秒慢速往返翻页与轻微悬浮起伏。金光的位置基底跟随新阅读平面。
- recover 直接倒序采样同一条开书时间轴，完整回收长 1.95 秒。合指结束后恢复固定握点，再将手和书整体转回待机。
- 开书中途取消，从当前动作时间开始倒放。阅读中收书，捕获当前页面姿态并在合书阶段收拢，避免直接跳回第一页。
- 主副手组合、右键切换专注、F 前击队列、施法占手、物品模型/材质、图标和存档未改。

手臂直接使用 V24 原采样生成的 `SpellbookAuthoredFocus.h`，开书与 recover 共用 118 个 60 Hz 关键帧。握持期间使用原 `BookInHand`；释放后书本对象根变换固定，局部骨骼完成开合。旧 `SpellbookAuthoredReturn.h`、`SpellbookReturnContact.h` 已不被当前运行代码使用。

## 已保存内容

动画资产位于 `/Game/Weapons/SpellbookEvildeer20261009/Animations/FocusV26/`：

- `A_Spellbook_FocusOpen_V24`：1.95 秒开书；recover 反向采样该资产。
- `A_Spellbook_FocusFlip_V24`：与新阅读姿态一致的翻页动画。

使用后台 Python commandlet 导入并保存，复用既有书本网格、Skeleton 和材质。导入记录为 `SourceAssets/SpellbookEvildeer20261009/Focus/IntegratedV26/import-receipt.json`；成功日志 `import-book-2.log`。

活动制作入口 `Focus/author_focus.py`、`author_return.py` 均转入 `IntegratedV26/promote_accepted.py`，不再调用已撤回的动作生成路线。活动可编辑源为 `Focus/Spellbook_Focus.blend` 与 `Spellbook_Recover.blend`；书本 FBX 作者源、导出和导入脚本保存在 `IntegratedV26/`。V23/V24/V25 原预览文件保留，修改前现场见 `IntegratedV26/backup.json`。

## 构建与运行边界

正式后台构建日志：`Saved/BuildEditor/build-spellbook-v26-20261011.log`。构建结果另见 `Focus/IntegratedV26/delivery.json`。

未启动交互 UE 编辑器或游戏，未做游戏运行测试、截图或新验收渲染。游戏内效果由用户测试。
