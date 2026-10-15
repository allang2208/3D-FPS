# M66 V23 — 焚化区楼梯恢复与尸体定姿排查

本轮用户明确要求实际检查主客机倒地、起身、死亡及尸体定姿超时，并直接修复。

## 收尾状态

用户随后明确要求停止排查，由用户自行检查；已停止本任务后续检查。修正源码已编入项目 DLL：`Records/compiled_sources.json` 对 7 个修改的 C++ 文件与 MSVC 对象内嵌 SHA256 校验全部匹配。`trash/m66-incineration-retired-20261015/SourceAssets/IncineratorBossM66/StairRecoveryV23/RuntimeHost-20261015-230940/snapshot.json`（工程根相对路径） 记录了当时项目 DLL 与插件的相同副本及 SHA256。

修正后的渲染联机复查 `Records/Hall-20261015-231055` 未完成：Windows 于 23:13:36 重启，系统日志有 Kernel-Power 41、EventLog 6008，BugcheckCode 为 0；UE 日志此前存在内存余量不足警告。不能据此确定重启原因，不能将中断轮次算作通过。尚未完成新修正的主客机画面对照、狭窄楼梯复查及原平地超时复现。原先的超时尚未被精确复现；已有修正针对确认的几何接触检测缺陷、阻尼覆盖及恢复动画缺少地形适配。

## 场景来源

`Records/production_rooms.json` 从当前保存的 `/Game/GameMaps/L_Dungeon_Randomized` 的 AuthoredDungeonGenerator.ModuleCatalogJson 只读提取。包含焚化大厅 74 个部件和烟气处理站 59 个部件的真实网格、材质、变换和碰撞开关。测试场景重建这些部件，不以简单斜坡代替实际楼梯。诊断照明不写回关卡。

- 焚化大厅上层双向楼梯：宽 260 cm、踏步高 15 cm。
- 焚化大厅 B1 楼梯：宽 180 cm，B1 净高约 335 cm。
- 烟气处理站楼梯：宽 180 cm、踏步高 16 cm。
- 当前 M66 胶囊直径 200 cm、高 380 cm。狭窄楼梯的实际阻挡必须与动画缺陷分开记录。

## 已取得的修正前证据

`Records/Hall-20261015-215839`：使用实际焚化大厅，监听主机 + 在线客机 + 晚加入客机，80±20 ms 延迟、2% 丢包。通信/控制状态检查通过。最终尸体位置误差分别约 0.0242/0.0328 cm。

但恢复姿态不合格：采样的局部表面与台阶/栏杆出现穿插（该指标包含栏杆，不等同于纯地板穿透）；起身中段最低可见表面距碰撞面约 14.32 cm。网络一致并不代表地形姿态正确。

这次两具尸体均成功定姿，其中一具在台阶附近存在较长的滑动、足部及腿部残余运动，约 20 秒后停止；尚不能用这一轮复现此前平地的超时。

## 当前修正源码（仍须以新构建及后续记录为准）

- `M66RecoveryGroundNode`：缓存蒙皮表面样本，游戏线程有界查询台阶，在侧倒/早期起身期间调整整体倾斜和高度；不修改角色胶囊或客户端网络平滑偏移。
- `MonsterSurfaceGroundingNode`：M66 起身 0.9–1.8 秒逐步恢复脚部 IK，与整体恢复接地交接。死亡不启用站立 IK。
- `M66CorpseSurface::FindPhysicalSupport`：原包围盒底部中心漏检时，验证真实凸体边界是否接触实际碰撞面；保持 2 cm 接触容差，排除体积内部点和无碰撞辅助骨。
- `MonsterCorpseRagdollComponent`：M66 保留物理资产原有阻尼，不再被普通怪物默认值降低；仅在真正低速且有接触时累计稳定时间，不引入超时强制定姿。
- opt-in `M66RecoveryAuditGameMode` / `M66RecoveryAuditScene`：实际房间、逐刚体诊断、蒙皮表面采样、主客机截图及最终姿态对照。

## 运行入口

`build_native.ps1 -Target FPSGAMEEditor -ForceHeaders` 使用共享批次互斥，并等待现有构建/编辑器释放。`run_network.ps1 -Room Hall` 默认为 NullRHI；显式加 `-Render -RenderPeer host` 或 `early` 时每轮仅渲染指定端，其余端保持 NullRHI。`-Room Flue` 检查烟气站；`-Room Flat` 进行原平地定姿复查。仅结束各次脚本自己创建的进程。

`summarize.py <Records/运行目录>` 汇总原始 JSONL。检查结果、是否截图、实际构建和未完成项以最终交付记录为准，本文不代替运行通过证明。

## 发布整理（2026-10-15）

旧 DLL 快照宿主、快照创建脚本与旧运行器已归档到上述 trash，保留散列和失败证据。当前运行器统一使用工程批次互斥，不再通过复制 DLL 绕开已运行的编辑器/构建。新运行器仅完成源码整理，未执行；用户已停止排查，须再次明确要求测试才能运行。个人与仓库调试技能已同步记录此约束。
