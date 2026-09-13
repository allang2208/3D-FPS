# 感染矿工单手挥镐

当前使用 `NaturalWrist/` 的三段修正动画，模型沿用 `DragGround` 放大后的矿镐。手腕回到中性附近，肘部和前臂配合镐头方向，原蓝图已替换引用。见 [当前说明](../../Docs/InfectedMinerNaturalWrist20260913.md)。预览位于 `NaturalWrist/Previews/`，未进行游戏测试。下文为各阶段历史记录。

当前版本为 `DragGround/`：矿镐整体放大 25%，待机与移动在身后拖镐，攻击延续已认可方向并前倾砸地，状态切换增加 0.16 秒姿态混合。见 [当前说明](../../Docs/InfectedMinerDragGround20260913.md)。以下 `PickaxeSingleHand/` 保留为已认可的前一版本。

当前交付已转为 `PickaxeSingleHand/`，使用实际 `A_Mannequin_PickAxe_Act` 的身体/腿/持镐左臂，配合已有放松右臂和已认可手指姿态，合成为 1.8 秒单手挥镐。参见 [当前说明](../../Docs/InfectedMinerPickaxe20260913.md)。当前 GIF 为 `PickaxeSingleHand/Previews/InfectedMiner_SingleHand_Pickaxe_Attack.gif`。未做游戏测试。

以下为上一版被拒绝的斧击记录，根目录旧 `Delivery`、`Previews` 与旧 GIF 不再是当前输出。

当前源为工程已导入的 Easy Building System V10 工具动画。UE 原生 IK Retargeter 输出同套待机、移动和挥击，替换被用户拒绝的 CMU 动作；不在旧攻击上继续编排姿态。

本轮输出在 `Delivery`：三个 `A_Miner_*.fbx`、可编辑 `InfectedMiner_Editable.blend`、资源及时序记录 `rebuild.json`。身体、手部、绑定、权重、材质和当前矿镐保留已认可版本。

免费替代候选为 [Basic Pickaxe](https://www.fab.com/listings/46ea08b2-1947-40f8-b1e7-f1254d49a912)，尚未下载和接入。用户先前提供的 Orphans 道具包是斧头，不作为十字矿镐替换。

村庄仍使用原矿工蓝图。原生构建及资产接入完成；未运行测试或渲染，交由用户试玩。旧交付目录和旧验收日志保留为历史，不能当成本轮结果。

详见 [本轮说明](../../Docs/InfectedMiner20260913.md) 和 [制作入口](../../Tools/InfectedMiner/README.md)。原始商店素材及派生二进制只保存在本机，不随公开 Git 再分发。

后续用户已明确请求 GIF：`Previews/InfectedMiner_Default_Axe_Attack.gif` 为当前完整挥击的原速双视角离线模型预览；同名 MP4 为清晰视频版。此次只输出预览，未修改游戏模型、动画、材质或玩法，也未执行游戏测试。
