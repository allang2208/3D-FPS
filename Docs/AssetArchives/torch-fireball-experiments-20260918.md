# Archived: torch / fireball flame experiments (torch-fireball-experiments-20260918)

- Date: 2026-09-18 / Rule: WORKFLOW.md section 4 / Count: 22
- Moved to: `trash/torch-fireball-experiments-20260918/`（gitignored，仅本机保留，供重做取回）
- Machine-readable manifest: `Docs/AssetArchives/torch-fireball-experiments-20260918.json`

## 两条线为什么作废

1. **方向理解反了**（`fireball-core-into-torch/`）：用户原话"看一下青铜火把的火焰特效，你可以加入火球技能火球主体强化燃烧效果吗"
   被理解成"把火球主体加进火把"。实际要求是把**火把的火焰**加进**火球技能的火球**。
   `NS_TorchFlame.uasset` 已还原成改动前版本（1,292,861 B）。
2. **效果不理想**（`torch-flame-into-fireball/`）：按正确方向把火把那两层 Vefects 火苗叠进
   `NS_FireballSlowBurnCore` 后，用户实机判定"效果并不理想，退回吧"。
   火球已**按字节还原**为改动前版本（2,722,693 B，SHA-256 与备份逐字节一致）。

资产候选留在两个已有的 trash 目录里（同样被忽略，不随 Git 发布）：

| 候选 | 位置 | Bytes | SHA-256 | 说明 |
| --- | --- | ---: | --- | --- |
| `NS_TorchFlame.scale042.uasset` | `trash/torch-fireball-core-20260918/` | 2,707,559 | 48A58F71…C0D865D | 火把加火球主体 0.42 版 |
| `NS_TorchFlame.with-fireball-core-070.uasset` | `trash/torch-fireball-core-20260918/` | 2,723,386 | FD3D849E…D0D2CD37 | 火把加火球主体 0.70 版 |
| `NS_FireballSlowBurnCore.with-torch-flame.uasset` | `trash/torch-flame-into-fireball-20260918/` | 3,316,988 | 08D8E0BA…A1DC9802 | 火球叠火把火苗版（重做起点） |

两侧的**改动前**备份同样在那两个 trash 目录里（`NS_TorchFlame.before-fireball-core.uasset`、
`NS_FireballSlowBurnCore.before-torch-flame.uasset`），本次退回就是从它们还原的。

## 沉淀到哪里

可复用的经验已进技能（个人目录与工程镜像同步）：
`skills/ue5-skill-magic-workflow/references/fireball-vfx.md` →

- 往系统里加**外部包的发射器资产**时，生命周期按那个资产原本的写法（Vefects 火苗是 `System`）；
  套用目标系统里其它发射器的 `Self` 会让发射器立刻结束，**整条 Niagara 系统静默失效**（火球连主体一起不渲染）。
- 定位手段：编辑器内临时 `NiagaraActor` 轮询 `UNiagaraComponent::is_active()`，并在 `_Scratch*` 副本上做对照。
- 活编辑器里 remove + re-add 发射器后 `compile_rain()` 可能返回 False
  （`Failed to generate consistent results for System spawn and update scripts`），`collect_garbage()` 后再编译即通过；
  结构性改动优先关编辑器走无头 commandlet。
- `EmitterState` 在 `Life Cycle Mode = System` 下不接受 `Loop Behavior` 写入；PIE 期间
  `EditorAssetLibrary.save_loaded_asset` 会被 "The Editor is currently in a play mode" 挡下，改用
  `EditorLoadingAndSavingUtils.save_packages([package], False)`。

火把那侧的过程记录（含"编辑器视口不点火、PIE 默认白天不点火、开发面板推时间"）留在
`SourceAssets/RomanColumn20260915/README.md` 的"【已回滚】火球主体加进 NS_TorchFlame 的尝试"一节。
