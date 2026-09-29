# 病区绿色候诊长椅

已将用户导入的 `Hospital Waiting Bench - AshenCut` 放入 `/Game/GameMaps/Design/L_AbandonedIsolationWard_Subject`，共 13 张。源网格 `/Game/Props/HospitalWaitingBench20260929/SM_Hospital_Waiting_Bench` 及材质直接复用，没有改动源资产。

- 北侧三组病房门各两张，共 6 张；南侧两组病房门、消毒间门各两张，中段实墙补一张，共 7 张。
- 长椅长 227.34 cm、深 59.81 cm。椅背朝墙，两侧座面相对；中心线在走廊两侧距中线 3.8 m 处，中央实际净宽约 7 m，配置声明 6.7 m 连续通行带。
- 门中心左右各 2.45 m 作为长椅禁入范围，窗洞两侧另留 20 cm。长椅脚底放在地面完成面上方 2 mm，背侧与墙面护栏有间隔；西侧开放通道不放长椅。
- 作者在写入前按模型实际包围盒处理门口、观察窗、主路留白和已有碰撞占位，符合布局的位置才保存。不是运行时随机堆放，不执行 Tick 或物理模拟。
- 沿用源网格已有简单凸碰撞，关卡组件为 Static、BlockAll、QueryAndPhysics、可作为角色踏面。未添加坐下交互。

配置由 `BenchLayout20260929/Scripts/bench_design.py` 生成，写入 `Config/room.json` 与 `module-draft.json`；`configure_benches.py` 同时供增量保存和完整作者入口调用，重跑按专属标签和稳定名称更新，不叠加副本。

落盘回执：`SourceAssets/DungeonIsolationWard20260929/BenchLayout20260929/Receipts/install.json`，桥输出 `install-bridge-01.log`。当前已有编辑器通过批次互斥完成保存，结束后返回原先主场景；本轮未启动编辑器、PIE、截图、渲染或运行测试，无需原生编译。游戏观感与通行由用户自行测试。

来源：[Hospital Waiting Bench - AshenCut](https://www.fab.com/listings/05f7dccc-ecee-4bd4-9cc1-189ab2f42cc5)，CC-BY-4.0；沿用原导入回执中的作者与许可记录。
