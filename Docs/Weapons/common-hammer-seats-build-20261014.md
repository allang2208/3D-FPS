# 通用中央锤座：三款建模与外观接入

按 `SourceAssets/CommonHammerSeats20261014/DesignV1/common-hammer-seats-design-v1.png` 制作三款独立中央锤座，目标槽位 `head_mount`，当前宿主为锻钢战锤 `ue_steel_warhammer`。

| 改造 ID | 名称 | 已制作结构 | 作者三角面数 |
| --- | --- | --- | --- |
| `reinforced_block` | 厚壁重铸座 | 整体方芯、前后阶梯厚盖板、嵌入铆钉和中央固定头 | 32,988 |
| `ribbed_light` | 镂肋轻型座 | 连续内芯、支撑侧轨、前后实体开窗盖板、交叉肋和顶部桥板 | 24,776 |
| `laminated_damper` | 叠片缓冲座 | 前后三层钢板、薄层缓冲垫、四角贯穿拉杆和分层端面 | 49,396 |

## 接口与表面

原装安装端取自 `SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend` 的 `SM_Warhammer_head_mount_factory`。保留左右接触面外侧 2.5 mm 的原表面（|X|≥0.0375 m）、Z≤0.887 m 的底部连接段和 Z≥0.972 m 的顶部帽。原装 UV 与面角法线随新切割点插值保留，新切口封闭；中央承力体和前后盖板重建。

实际对接截面仍为 X=±0.040 m、下接面 Z=0.865 m，锤头轴线 Z=0.925 m。三款枢轴均保持武器基准 (0,0,0)，装配偏移也为零；不改变其他五槽、锤头间距或手臂骨架。新增盖板向前后展开，不外移锤头接口。

新钢材复用已保存的通用锤头基色、金属度／粗糙度和法线，物理 UV 平铺长度为 0.12 m。原接口继续使用原战锤材质。深钢盖板和哑光垫片使用独立 Substrate 材质：深钢保留金属度和粗糙纹理，垫片为非金属，法线强度降低。没有重复导入共享钢材贴图，没有改动现有武器材质。

## 资产与运行数据

作者目录：`SourceAssets/CommonHammerSeats20261014/BuildV1/`。

- `CommonHammerSeats_Editable.blend`：三个完成模型、原生枢轴、UV 和材质。
- `Export/`：三个独立 FBX；`exports.json` 保存来源、面数、槽名、偏移。
- `CommonHammerSeats_IconSources.blend`、`IconSources/`：实际新模型的独立灰阶图标素材。
- `Icons/`：依据认可框体母版逐项生成的正式图标；提示词、素材来源和生成路径同时保留。
- `import_seats.py`：导入模型、材质与图标并保存后，调用 `register_seats.py` 合并当前运行数据；`import_receipt.json` 记录实际保存结果。

UE 模型及新增材质位于 `/Game/Weapons/CommonHammerSeats20261014/BuildV1/`。共享图标键为 `head_mount_reinforced_block`、`head_mount_ribbed_light`、`head_mount_laminated_damper`，保存在既有改造图标根目录；使用 UI 组、Editor Icon 压缩、sRGB、Never Stream 和无 mip。

通用目录为 `Content/ColdSteelData/common-hammer-seats.json`，由 `warhammer-gunsmith.json` 的 `head_mount.options_library` 引用；三条实体配方合并到 `warhammer-modules.json` 的同名槽。复用现有模块加载、工作台草稿和装备改造 ID 保存流程，不新增 C++。原厂选项保留，其他槽和轻量鼓锤物理伤害 -10% 保持原值。

## 数值与交付边界

三款在初次建模时仅接入外观，随后按用户确定的下表写入制作源 `BuildV1/catalog.py` 和正式共享目录 `common-hammer-seats.json`，`effects` 从同一倍率生成。以下数值均相对原装锤座，各槽之间沿现有结算相乘。

| 中央锤座 | 物理伤害 | 攻击速度 | 体力消耗 | 韧性伤害 |
| --- | --- | --- | --- | --- |
| 厚壁重铸座 | +10% | -5% | +10% | +15% |
| 镂肋轻型座 | -5% | +10% | -10% | -10% |
| 叠片缓冲座 | +5% | +5% | -15% | -15% |

复用既有钝器改造评估、工作台草稿和详情显示；没有新增特殊机制，`special_effects` 保持空数组，缓冲层不新增物理模拟或动画。本次数值修改仅涉及数据与作者源，不需要原生构建或资产重导入，未运行游戏测试。

后台制作、FBX 导出、材质编译和 UE 资产保存属于本轮工作；没有打开编辑器界面、运行游戏、测试装配／联机或追加验收渲染。完成状态以本轮导入回执为准，游戏内效果交由用户测试。

本轮导入回执 complete=true：三个静态网格、两个新增材质和三个共享 Texture2D 共八个 UE 资产保存完成，三个正式 PNG 已同步，三个改造选项和实体配方已注册。后台 commandlet 返回 0；没有 C++ 改动，不需要原生构建。
