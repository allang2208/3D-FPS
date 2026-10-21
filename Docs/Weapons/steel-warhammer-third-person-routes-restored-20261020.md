# 双手锤第三人称动作配置恢复（2026-10-20）

本次恢复了 `Content/ColdSteelData/player_body.json` 中缺失的 39 个 `Warhammer.*` 动作入口。修复前该文件有 125 个动作入口，但没有任何战锤入口；修复后共 164 个。原有的其他 125 个入口和全部非动作配置保持不变。

## 原因与恢复依据

`FPSPlayerBodyComponent.cpp` 从上述 JSON 的 `clips` 字段加载第三人称动画。缺失战锤入口时，已有的专用动作资产无法通过这个动作库供运行时选用，导致出现退回通用动作的表现。

当前源码仍包含战锤动作分类、源动画持握、连续双手握持及步态混合处理；本次没有回退这些共享源码。引用的 21 个动画包也仍在本地，因此不需要重新制作或导入动画。

恢复基准：

- `SourceAssets/SteelArmet20261019/ReferenceMatchV5/player_body-before.json`
- 基准文件 SHA256：`4bde9715f7e4f848d047240c6c221a9bbae34277afe7c9540d004101299a1c39`
- 同一套 39 个入口还存在于 `SourceAssets/BlueMageSetAudit20261019/Before/Content/ColdSteelData/player_body.json` 和 `SourceAssets/SteelArmet20261019/player_body-before.json`。

完整备份中的 39 个入口与下列五个制作版本的最终保存回执合并结果一致。回执均位于 `SourceAssets/WarhammerThirdPersonSevarog20261016/<版本>/assets-published.json`；其中的 `published` 是资产制作流程的记录，不能单凭此字段认定已推送 Git。

| 制作版本 | 恢复范围 | 动作入口数 | 独立动画包数 |
| --- | --- | ---: | ---: |
| SourceGripV16 | 待机、持锤、冲刺持锤、八方向走路与慢跑 | 19 | 9 |
| NaturalComboV17 | 第一、第二段普攻及恢复段 | 4 | 2 |
| Slash3AlignmentV18 | 第三段普攻及恢复段 | 2 | 1 |
| RefinementV8 | 蓄力、重击、冲刺抬锤与砸击、上挑、快速近战 | 6 | 3 |
| AnatomicalGripV7 | 旋风起手/循环/收手、格挡进入/保持/受击/退出/破防 | 8 | 6 |
| 合计 | | 39 | 21 |

这是此前实际接入配置的恢复，不是将全部动作换成同一个编号的制作版本。

## Git 与会话追溯边界

排查时，本地 HEAD、main、origin/main 以及 `git ls-remote origin refs/heads/main` 均指向 `b921d59896bc12a8c69daa1bc0c7b1ee61011bbe`。

在可用 Git 历史中，`git log --all -S 'Warhammer.FullBody' -- Content/ColdSteelData/player_body.json` 没有命中。抽查当前提交与相关较早提交中的配置，也均没有这套战锤第三人称入口。因此本次没有找到一个可直接回退的“完整第三人称动作已推送提交”，不能把本次修复描述为回退到了某个已推送 SHA。

相关发布提交不能混同：

- `e75b75ab` 涉及战锤检视、换握与第一人称连击节奏。
- `f9a9024b` 包含战锤施法相关工作，不代表这套完整第三人称战斗动作库已发布。
- `3f7e3dae7975ae35d5651f60175fa9f418cb14e1` 对该 JSON 的提交差异仅增加头部装备配置，未在提交差异中删除战锤入口。

针对相关服装发布记录的只读排查发现，其发布脚本生成的是独立索引内容；已查到的命令不足以证明它覆盖了工作区配置。现有证据无法确定实际导致入口丢失的会话或操作，不据此归责。

## 本次落盘内容

- `Content/ColdSteelData/player_body.json`：只补回 39 个缺失的战锤入口。
- `Tools/PlayerBody/restore_warhammer_routes_20261020.py`：本次定向恢复脚本。
- `Saved/WarhammerThirdPersonRestore20261020/player_body-before.json`：修复前完整配置备份。
- `Saved/WarhammerThirdPersonRestore20261020/receipt.json`：恢复来源、39 个入口映射、21 个本地动画包的路径与 SHA256、修复前后配置摘要。

恢复脚本已完成范围比对：所有原有非战锤入口、其他配置及 `clips` 对象之外的原始文件字节均保留。本次没有修改 C++、动画资产或第一人称手枪/魔法书姿态，也没有执行 Git 提交或推送。

## 生效与验收

本次是配置修复，不需要 C++ 编译或资产导入。重新进入游戏或重新开始 PIE，使玩家身体组件重新初始化并加载配置即可。

未启动编辑器、运行游戏、截图或进行视觉验收；最终动作表现由用户自行测试。
