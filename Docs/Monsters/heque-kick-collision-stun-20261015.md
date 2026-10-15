# 合阙踢击：击退撞障碍眩晕

2026-10-15，按用户要求增加碰撞后的 2 秒眩晕。

- 沿用踢击 10 米击退的原生移动路径。击退期间首次撞上阻挡位移的不可行走表面，立即消耗剩余推力，并对存活目标调用 `UCombatStatusFormula::AddStun(2.f)`。
- 走满击退距离而未撞障碍不会施加本次眩晕；正常可行走地面不触发。重复碰撞调用不会刷新同一次踢击的眩晕。
- 眩晕只由服务器施加。玩家动作/输入锁和状态显示沿用已有 `PlayerGuardBreak` 与 `FPSStatusReplicationComponent` 的复制通路，保留既有控制免疫规则。
- 修改：`Source/FPSGAME/Movement/FPSImpactPushMovement.cpp`。无需重新导入模型、动画或地图。
- 本次仅制作及必要构建，没有追加测试；上一轮联机检查结果不代表本次新增眩晕已经实测。

构建记录：`SourceAssets/HeQueBoss20261014/KickCollisionStunV01/Records/`。

后续按用户明确要求进行了真实主客机测试，发现并修复“首次眩晕尚无输入锁组件”的遗漏；三例复测通过。实际时长及恢复操作记录见 [联机测试结果](heque-kick-collision-stun-test-20261015.md)。
