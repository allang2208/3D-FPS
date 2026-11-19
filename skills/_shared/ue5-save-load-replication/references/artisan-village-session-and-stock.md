# 丘陵房主存档、共享货架与个人学徒任务

## 谁决定村庄

`ATemperateHillsWorld::ResolveSession` 在房主进程读取 `TemperateHills_World`。首次建世界为种子与 `WorldId` 分别取值，同时记录生成器版本。入口 URL 带 `HillsContinue` 时优先续读已有存档，即使进程原先带过 `HillsSeed` 或 `HillsNewWorld`。这些命令行开关用于明确选种或开新世界。固定测试种子写在本轮测试启动参数中即可。

客机在 `BeginPlay` 等候房主复制的种子、世界 ID 和生成器版本，再生成本地场景。晚加入或原角色重连也走这个入口。村庄建筑读同一世界的修复位；在场角色修复建筑后，新到的玩家也看到修复结果。人物的修炼阶段另存个人档案。

## 多人购买同一件商品

- `AVillageArtisanMerchant` 在权威端为货架每件商品分配批号 `Lot` 和品质，复制 `Offers`。顾客看到的属性、价格和购买请求都引用这一批商品。售后换新批号，识别两个顾客同时点中旧货的情况。
- `UColdSteelShopModel::ExecuteNetworkTrade` 重新核对当前角色、商人、交互范围、商品定义、批号和数量，用服务端货品计算价格。在待提交的个人档案中增加商品并扣灵魂，存档成功后才调用 `RestockSoldLot`。背包放不下、存档失败或旧批号均不动该批库存。共享货架随商人实例创建；买入的物品归买家档案。

## 学徒任务与实际工件

- `UChapelDialogueComponent` 校验本次会话编号、老师及当前 Pawn。远端玩家的物品事务使用该 PlayerState 的影子模型与档案槽。`ApprenticeMaterials::Grant` 按生产配方在一份档案快照里放入整套材料，连同领取回执和阶段提交。缺少一格导致任一物品放置失败时，仍可清出空间后重领；已经保存的领取回执防止重复发放。
- 铁匠任务认 `forge_tang_dao` 的唐刀工件及实际锤击，木匠任务认 `woodwork_staff` 的学徒长杖及锯切达标。领取合格成品时，由工作台在同一笔档案事务里完成任务；买到、拿着同款成品均保留原阶段。废弃工件按各项实付材料分别返还一半并向下取整，任务回到备料，不重发教学包。
- 导入旧档时用领取回执和现存目标工件归一化。左上任务栏读取当前本地玩家的跟踪源。实现见 `BlacksmithApprenticeship`、`CarpenterApprenticeship` 和 `ChapelDialogueSmithTraining.cpp`。
