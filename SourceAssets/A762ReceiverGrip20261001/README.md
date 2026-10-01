# A762 ReceiverGrip08 — 2026-10-01

后续修正：原厂及幻影握把的前缘让位已更新至 [GripClearance09](../A762GripClearance20261001/README.md)。继续制作这两款时使用 R09 当前源和编辑配方；本目录保留 R08 历史记录。

本轮对应用户截图中的机匣破碎金属边、扳机前卡笋、护圈后部缺口以及后握把接口。

状态：2026-10-01 14:45 四个正式网格和独立版本均已保存；保存后已通过全新后台进程只读加载，网格/UV/材质绑定与保存记录一致。详见 `install_receipt.json`、`saved_reload.json` 和 `../../Docs/Weapons/a762-receiver-grip-junction-20261001.md`。未运行游戏。

## 输入与坐标

- 从当前 UE 正式资产读取：`Input/current.json` 记录路径、槽位、材质和资产 SHA256；所有原始网格及骨骼权重在 `Input/`。
- 原参考图：`../A762Meshy20260920/References/a762_side.png`、`a762_rear_threequarter.png`。
- Blender 使用原枪 `WPN_root` 的装配坐标，导出枪体部件时转换回对应骨骼的 bind pose；枪栓仍使用 `WPN_bolt`。
- `author.py` 修改局部机匣、卡笋、护圈、握把，枪口、护木、瞄具、枪托、原装弹匣及手臂沿用输入资产。Continuous07 扩容弹匣不在本轮范围。

## 制作与落盘

1. `capture_inputs.py`、`capture_uvs.py` 只读采集当前资产；不要在升级后覆盖原始 Input。
2. 顺序运行 `author.py`、`finish_export.py`，生成可编辑 `A762_ReceiverGrip08.blend`、`Exports/*.bin` 和三个独立握把 FBX。幽灵握把保留原有镂空主体和法线，只重建其接颈；原装、均衡、稳固防滑握把使用连续外壳。已合入 author.py 的一次性 `restore_phantom_lattice.py`，以及废弃的 finish_phantom/reduce_phantom 实验脚本，已移入 `trash/weapon-surface-animation-20261001/SourceAssets/A762ReceiverGrip20261001/`，不再作为制作入口。
3. `install.py` 经 `../WeaponSurface20260930/run_ue.ps1` 的批次锁写入；已开编辑器时使用现有桥，否则后台 commandlet。PIE、未保存目标或 SHA 变化会停止写入。
4. 先保存独立 R08 版本，再写回当前正式网格路径。正式路径、骨骼、握把安装变换不改变。
5. `Before/` 保存当前四个正式资产的备份；`install_receipt.json` 是实际落盘记录，只有 `complete: true` 才代表四个正式资产全部保存。

新表面使用原有 WeaponSurface 母材质体系及当前 Refine06 微法线；不修改共享母材质、既有材质实例或天气参数。重新制作的握把保留各自的聚合物/橡胶材质类别。

## 本轮模型检查

按用户“全面检查并调整”的要求，通过离线装配查看两侧机匣、扳机区域、均衡/稳固防滑后握把的斜下方接合面，并记录新部件的边界边、非流形边和退化面。`Inspection/result.json` 与 `Inspection/after_*.png` 是模型结构检查，不是 UE 材质或游戏测试。

未启动 PIE，未运行射击、换弹、天气或玩法回归，游戏内观感由用户测试。

## 后续维护

- 枪体新固定结构的材质槽不包含 `FactoryRearGrip`；原装握把槽保留该标识，匹配现有换握把隐藏逻辑。
- 三款改装握把使用贴合的接颈，不再追加 `A762_GripUpperTang` 大方块；均衡和稳固防滑的接颈已与主体合为连续网格。
- Accessories05 的旧批量制作脚本在本轮安装完成后直接引用新的握把 FBX。旧整枪 Accessories05 FBX 早于近期几何/材质升级，不能直接拿它覆盖正式枪体；当前完整状态以 UE 资产和各轮局部编辑配方为准。
