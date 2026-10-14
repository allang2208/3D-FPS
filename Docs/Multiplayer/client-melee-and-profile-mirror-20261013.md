# 客机唐刀无法切出与档案下行修复（2026-10-13）

用户反馈：双人联机中客机无法切出近战武器，测试武器为唐刀。

## 直接原因与修改

`URuneSwordComponent::BeginPlay` 原先在 `NM_Client` 下直接禁用 Tick 并返回，没有创建 `Viewmodel`；之后 `RefreshEquipment` 又因 `Viewmodel == nullptr` 返回。该路径覆盖全部由近战组件管理的双手剑／唐刀。

现在允许权威角色和本机控制角色初始化近战表现。若客机控制器晚于 BeginPlay 到达，现有 `OnRep_Controller → TryAttachLocalProfile → ApplyColdSteelProfile → RefreshEquipment` 链会补建视模。客户端的远端代理不初始化第一人称近战表现；服务端远端角色使用自己的影子档案，不再从主机的 GameInstance 档案初始化装备。

保留唐刀原有模型、配件、动作时钟、装备槽、存档和战斗结算路径。

## 同次发现的下行问题

既有日志（UTC）显示 2026-10-12 16:22:32 的压缩档案上行已完整接收，57311 字节；但 16:22:35 开始，`ColdSteelPlayerState_1` 下行报 `BunchSize=212743, MaximumSize=65536`，后续仍反复出现约 130 KB 的超限包。

上一轮仅压缩整块 `MirrorBlob` 仍不足：普通复制数组还会产生逐元素变更头。现将它从复制属性改为拥有者本地的临时组装缓冲区，由可靠 Client RPC 按 1 KB 分片传输，并沿用连接带宽 20%、最高 16 KB/s、拥塞等待和不补发突发流量的节流方式。分片携带传输编号、位置和总数，收齐后调用原档案合并与篝火回执流程。

本修改需要主机与客机使用同一版正式构建、重新建立联机会话。

## 交付边界

构建日志：`Saved/ClientMeleeFix20261013/`。本轮不启动编辑器或双人测试，由用户重新进入双人 PIE 后切换唐刀，观察第一人称拔刀与收刀，以及主机侧装备显示。

本轮必要构建另外修正了两处阻塞：`FatZombieAnimInstance.cpp` 为派生节点添加设置接口，保留原有条件、避免外部直接访问引擎 protected 字段；`FPSPerformanceMetricsResources.cpp` 的两个怪物头文件 include 改为正确相对路径。未调整这两处功能的行为参数。

Editor 构建已成功：`editor-build-final.log` 报告目标最新、`Result: Succeeded`；初轮日志记录了本次近战及 PlayerState 源码编译，后续日志保留构建阻塞与修正过程。

Game 正式构建也已成功：`game-build.log`，`Result: Succeeded`，104 个构建动作，已链接 `Binaries/Win64/FPSGAME.exe`。源码及正式构建完成；未进行双人运行复测。
