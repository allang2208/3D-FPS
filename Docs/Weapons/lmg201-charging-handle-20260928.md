# 201 拉机柄修正

制作分支：`SourceAssets/LMG20120260927/Charging04`。继承 Hands03 原生 V7 双手和 Refinement02 枪体，依据铁烽实拍修正右侧外部拉机柄位置、固定/活动分件以及装备、空仓换弹接触。

原错绑枪机的左侧表面恢复固定，右侧外部滑块与折叠柄独立驱动；开火不再带动整个外部块往复。右手保持成熟抓握形态，前送到位后再松手。其他手部片段、普通换弹、机瞄与 FireAudio01 开火声保留。

运行路径仍为 `/Game/Weapons/LMG201/Production20260927`，修改前备份为 `/Game/Weapons/LMG201/Charging04/Before`。UE 安装保留原生手臂表面并替换武器表面；12 个动作更新拉柄轨道，其中仅装备、空仓换弹重做右臂接触。使用既有骨架，无 C++ 变更。

最新源：`Charging04/LMG201_Charging_Editable.blend`；完整动作源在 `Charging04/Motions`，FBX 在 `Charging04/Exports`。详见该目录 `README.md`、`RESEARCH.md` 和保存回执 `import_receipt.json`、`DELIVERY.json`。

本轮先使用已有编辑器桥接导入落盘；该会话退出后，最后一处模型修正通过无界面 commandlet 补存。不打开新编辑器、不启动游戏；没有运行或视觉测试，由用户测试，不将源文件/保存成功视为验收通过。
