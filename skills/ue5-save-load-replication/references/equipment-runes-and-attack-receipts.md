# 装备符文与攻击提交回执

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 远端材质按语义重建

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 消耗确认独立于动作确认

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 持续刻印与双段攻击（2026-10-23）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 证据与边界

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 持续旋风与 CMC 的双通道顺序（2026-10-19）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 共用蓄能符文与观察者（2026-10-28）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 共用表现组件与真实传输夹具的边界（2026-10-28）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 弯刀命中回调与拥塞后的动作时间（2026-10-30）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 剑身材质复制与断线恢复（2026-11-01）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 单手近战蓄力：起手到包时间不能代替输入时间（2026-11-04）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 双手剑连段与突刺接触的统一时钟（2026-11-06）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 斧头观察端首次刀光与附魔夹具迁移（2026-11-06）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 击杀返还与跨通道付款（2026-11-07）

详见[维护源](../../_shared/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)中的同名章节。

## 客机连续改造与迟到的库存回写

客机点“应用”时，按物品实例记录本次实际改动的免费槽位和提交序号。上次提交仍待确认时合并新改动的槽位。旧库存快照到达后，只保留待确认槽位的本地值，其他槽位采用服务器值；相应序号收到服务器回复后，接受服务器最终值并清理待确认记录。两端的部件都要兼容当前武器，材料消耗继续由库存事务确认。

需要验证这条路径时，可让客机只换弦，同时让服务器改变弓体并确认拾取，再分别送达旧快照和匹配序号的拒绝回复。检查弦、弓体和库存各自的最终值。真实传输另用主机、客机和新进程重连覆盖，并记录延迟、丢包及测试所用正式模块的散列。
