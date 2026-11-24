# 锻钢双手剑、铁匠学徒与村庄吊灯

锻钢的力量、敏捷每级强化成长分别为 1.176 和 0.5695。锻造消耗一份合金胚及同一种金属锭三块。暮鸦折羽累计奔跑 3 秒满充，5 秒内命中的下一次攻击获得暴击率+25%。鹰爪之握每次格挡积 1 点，弹反积 2 点；达到 6 点后，下一次普通攻击或战技获得暴击率+30%，体力消耗为零。[武器装配与材质表](../../../Content/ColdSteelData/forged-steel-greatsword-modules.json) · [护手制作源](../../../SourceAssets/ForgedSteelGreatsword20261120)

丘陵铁匠的教学依次为采矿交付、冶炼、锻造。任务栏以父卡选任务，详情列步骤和奖励；选择追踪会更新左侧当前目标。F6 可重置房主自己的铁匠、木匠任务，地牢单独显示。炉棚随铁匠铺修复，六家商店使用 18 个吊灯挂点。机械工坊另有一盏工作灯。[任务与场景实现](Implementation/Source/FPSGAME) · [炉棚制作源](../../../SourceAssets/HillsVillageBlacksmith20261117/SmeltingYard)

## 源码与恢复

武器表、配方、制作脚本及测试入口按工程路径发布。村庄和战斗共享宿主沿用[前次商店交接](../VillageShops20261122/README.md)的发布方式。独立实现位于 [Implementation](Implementation)，共享宿主有制作前后记录的改动按批次保存在 [Integration](Integration)。[差异清单](Integration/recorded-deltas.json)使用 LF 归一化的前后 SHA-256。仅有当时成品快照的旧宿主按[函数与调用位置](Integration/host-hooks.json)对照合入；目标版本不同的宿主需要按其当前结构合并。正式地图、模型、贴图、可编辑源和恢复包按[版本清单](recovery.json)从项目资产库取回。

## 已有验证

11 月 24 日的监听主机、客机及同档重连覆盖了任务归属、赠镐、拾取、交付、炉棚修复和鹰爪状态同步。测试使用新矿掉落及注入的格挡结果。挥镐到出炉的全程客机输入、每种战技对真实敌人的命中仍属未覆盖范围。[22 项双端记录](Evidence/network-result.json) · [任务与护手回归、照明采样](Evidence/checks.json)

两处本机 trash 分别保存原盘的一次性宿主、检测图和弃用造型；逐文件清单及已解除的联接目标保存在本机恢复批次。[整理数量、字节数与清单散列](cleanup-summary.json)
