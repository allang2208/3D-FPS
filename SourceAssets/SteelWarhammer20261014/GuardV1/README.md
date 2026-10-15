# 双手战锤斜横撑挡 V1

本次新增双手战锤的进入、保持、受击、破防与收回动作。双手沿用原生待机的握柄接触矩阵和握距；手指保持包握，武器与双手共同运动。斜横锤柄左低右高约 25°，两手中心置于画面下方，锤头偏右。

## 动作

| 动作 | 时长 | 设计 |
| --- | --- | --- |
| GuardEnter | 0.22 秒 | 快速抬起、随后减速撑稳 |
| GuardHold | 1.60 秒循环 | 小幅呼吸，端点连续 |
| GuardHit | 0.30 秒 | 0.055 秒内回压，随后逐渐撑回；弹反沿用 1.25 倍反应播放率 |
| GuardBreak | 1.50 秒 | 锤柄向右下卸力、短暂失衡，然后恢复待机 |
| GuardExit | 0.25 秒 | 平滑卸力收回原生待机 |

源动作以 300 Hz 烘焙。每一只手固定在锤柄局部空间，肩、肘和前臂共同解算，保持原生骨段长度；腕部方向由完整前臂承接，辅助骨使用该原生模型的蒙皮位置分布。没有更改骨架绑定、手指骨长或网格权重。

## 接入

- `URuneSwordComponent` 保持原有双手剑身份，同时为当前双手钝器保存独立的格挡装备标识与修正属性。
- 右键进入/维持，松开右键收回。进入、受击、回收与破防均由战锤自己的动画播放；格挡的服务器判定、弹反窗口、体力结算、减伤、移动限制和破防输入锁定使用双手剑原有入口。
- 抬挡途中松键时从当前抬挡位置反向收回；完整撑挡后使用独立的收回动画。
- 保留双手剑当前实际判定规则：普通格挡与弹反的方向条件各自沿用共享逻辑，没有新增另一套判定角度。
- 声音复用双手剑普通格挡与弹反音效，镜头反馈也复用共享格挡反馈。
- 防御时阻止普通攻击与重击蓄力；施法、切换装备等原有动作优先级仍能取消格挡。
- 动画时钟在摄像机更新前推进一次；破防输入锁定期间保留破防动画，避免被不可操作条件立即清除。
- 第一人称播放新制作的五条动画，角色身体状态发布已有的 Guard / GuardHit / GuardBreak 动作类型。

## 文件

- 作者入口：`author_guard.py`
- 可编辑源：`Warhammer_GuardV1_Editable.blend`
- FBX：`Export/A_Warhammer_Guard*.fbx`
- 引擎资产：`/Game/Weapons/SteelWarhammer20261014/GuardV1/A_Warhammer_Guard*`
- 导入入口：`import_assets.py`；优先无界面 commandlet，已有编辑器通过项目批次互斥桥接入。
- 运行时入口：`Production/ProductionBluntGuard.cpp`、`Production/WarhammerGuardMotion.h`、`Weapons/RuneSwordToolGuard.cpp` 与原有 `RuneSwordGuard*.cpp`。

## 交付状态

五段动作已制作、导出，并通过无界面 commandlet 完成 UE 动画编译与资产保存。FPSGAME 和 FPSGAMEEditor 正式构建均成功。结果由同目录 `import_receipt.json`、`build_receipt.json` 和 `delivery.json` 记录。

遵照用户工作规则，本次不启动编辑器或游戏，不追加动画渲染、运行测试或联机验收。源码制作与构建成功不等于第一人称视觉或实机玩法验收。
