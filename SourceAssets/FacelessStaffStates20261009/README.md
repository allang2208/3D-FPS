# M-03／M-04 动作遗漏修订（2026-10-09）

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

依据 `Docs/Monsters/FacelessStaffMotionReview20261009.md` 的五项发现，制作安保员 V12 和接待员 V05。源文件、导出和 Editor／Game 原生构建已经完成；16 项 UE 资产已实际保存到原蓝图入口，`ue_delivery.json` 为 `stage: saved`，`import_process.json` 记录后台 commandlet 退出码 0。

- 安保员制作：`../FacelessSecurity20261008/V12/README.md`。新增受击、倒地、两种起身、眩晕，保留 V11 模型／服装／帽子、V06 待机与移动、V10 攻击收势。
- 接待员制作：`../FacelessReceptionist20261007/V05/README.md`。保留 V04 基础外观和三段动画，新增五种状态的 121 个衣物形态，合计 181 个；专属受击与特殊状态动作绑定原独立骨架。
- `NurseZombie.cpp` 只将既有 M05 过渡分支扩展到 M03／M04。`FatZombieAnimInstance.cpp` 将快照衣物支持扩展到接待员 FR4／FR5；具体代理类型保护保留，其他派生播放器不读取该节点。
- 没有改变攻击权威时钟、命中窗口、伤害、控制时长、移动速度、尸体／帽子物理预算，也没有新建 Tick 或布料求解器。

制作脚本位于 `Tools/FacelessStaffStates20261009`：

1. `export_sources.py` 从现有 UE 导出共用源动作、记录当前两只蓝图核心引用；不写游戏资产。
2. `author_security.py` 制作安保 V12，`author_receptionist.py` 制作接待 V05。
3. `build.ps1` 完成 Editor／Game 常规构建；`save.ps1` 通过现有命名互斥窗口执行 `import_states.py` 并落盘。

`Motion/` 保存本轮共用源 FBX，`source.json` 是输入合同。`SourceBackup/` 保存本轮修改前的两个 C++ 工作区文件，仅供追溯，不能覆盖后续并行修改。模型完整身体及原版本不删除。

第一次安保制作因 Quaternion.slerp 不接受大于 1 的加强系数停止，后改为旋转轴角乘系数并重新完成导出；没有把失败输出导入 UE。首次构建调用的 PowerShell 语法错误发生在执行前，修正后 Editor／Game 均正常完成。

本轮为制作修复，未追加自动检查、游戏／PIE、截图或渲染。没有主动打开编辑器；用户保存并退出当前编辑器后进行正式构建和后台导入，完成后不自动重新打开。动作观感、穿模与真实击倒效果由用户测试。