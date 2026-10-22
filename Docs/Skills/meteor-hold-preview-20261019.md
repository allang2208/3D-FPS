# 陨星长按范围预览（2026-10-19）

用户要求参照暴风雪，长按触发按键显示陨星作用范围。

## 输入与显示

- 复用快捷槽 `BeginSpellAimPreviewForSkill` / `EndSpellAimPreview`，以及法杖左键 `PressStaffMagic` / `ReleaseStaffMagic`，没有新增按键或改变绑定。
- 按住期间随准星选取可落地表面；松开冻结最后显示的落点，再走既有施法手势与接触释放。短按也在松开时提交。
- 新的红色双圈地面贴花采用共用魔法预览颜色：亮外圈为爆炸半径，淡内圈为持续火场半径。半径来自 `FireMagicStats(meteor)`，包含 2026-10-19 的三倍调整与等级成长。
- 材质在世界水平坐标中计算圆形，取消旧暴风雪 UV 半径 `.91` 的补偿；高度限定在落点上下 100 cm，与现有地面伤害的高度窗口一致。圈表示半径上限，实体遮挡仍由实际伤害路径判断。
- 保留淡填充，加入低强度自发光，避免仅靠场景照明看清红圈；关闭这张预览贴花的屏幕尺寸淡出。
- 仅本地一个可复用 Decal/MID，每 0.1 秒刷新；没有新增 Niagara、网络消息或持续计时器。

## 施法边界

- 预览阶段不扣蓝、不启动冷却，不提前播放释放手势。
- 预览请求不再要求全部陨石和音效资源已经就绪。按住期间后台资源到达后可继续显示；真正释放仍执行现有资源、法杖、蓝量、冷却和距离条件。
- 菜单、选弹/魔法轮盘、建造模式、死亡、捕获、切走法杖或其他已准备法术会取消预览；松开不会重新触发已取消的预览。
- 陨石固定生成高度、穿越天花板的下落方式、伤害和联机权威路径不变。非法地面/超距继续显示原有原因并拒绝释放。

## 文件与交付

- 运行路径：`FPSFireMagicComponent.*`、`PlayerSkillAssets.cpp`，原输入路径保持。
- 作者脚本：`Tools/Skills/build_meteor_aim_preview.py`。
- 独立材质：`/Game/Skills/FireMagic20260921/Preview20261019/M_MeteorAimPreview`；不修改暴风雪共享资产。
- 打包目录显式加入 `DefaultGame.ini`。
- 材质已由无界面 commandlet 保存，退出码 0，`asset-receipt.json` 的 `complete=true`。构建回执位于 `Saved/MeteorAimPreview20261019`。
- 构建遇到 `ColdSteelCrosshair.cpp` 既有瞄准镜倍率提示的格式字符串编译错误；仅把运行时格式选择移到两次常量格式 `FString::Printf` 调用外，保留两种提示和倍率精度。
- 共享构建新增 `ZhufengNetworkAudit.cpp` 后，角色类缺少它所属 `USkillNetworkAuditCommandlet` 的访问声明；按现有辅助工具约定补充一条 `friend`，仅解决编译，没有执行该工具。

## 本轮完成状态

- 材质：后台保存成功，`import-01.log`，commandlet 退出码 0。
- Game：`FPSGAME-build-03.log`，`Result: Succeeded`，6.10 秒；在共享完整 Game 构建成功后确认目标已更新。此构建包含陨星运行改动，发生在最后补充辅助工具 friend 声明之前。
- Editor：`FPSGAMEEditor-build-02.log`，`Result: Succeeded`，386.80 秒；正式 `UnrealEditor-FPSGAME.dll` 链接完成，包含最后的访问声明修复。先前 Live Coding 未成功的回执不作为交付构建依据。
- 没有执行编译过程中提及的 Audit 工具；它们只是共享工程的编译单元。

未由本任务启动游戏、画面预览或玩法测试，长按显示与释放手感交由用户测试。

整理说明（2026-10-22）：本页保留阶段记录；Before 备份和已替代作者的归档位置、当前资源及公开恢复边界见 [陨星发布记录](../Publication/Meteor20261022/README.md)。
