# 通用锤类柄尾选项：无配重

稳定 ID：`no_pommel`；槽位：`pommel`；通用库：`common-hammer-pommels.json`。

| 属性 | 改变量 | 数据字段 |
| --- | --- | --- |
| 攻击速度 | +5% | `attack_speed_mult: 1.05` |
| 体力消耗 | -5% | `stamina_mult: 0.95` |
| 重击蓄力速度 | +10% | `heavy_charge_speed_bonus: 0.10` |
| 重击出手体力消耗 | +10% | `heavy_release_stamina_mult: 1.10` |

独立的重击出手倍率仅在蓄满重击释放时扣体力；单机与服务器提交攻击时采用同一计算结果。冲刺攻击和武技不使用该重击专属倍率。蓄力起始保留普通攻击的体力门槛，避免阻挡随后转为普通挥击的短蓄力。

按照现有属性乘算规则，单独安装此改造时，普通攻击消耗为基础值的 95%，蓄满重击出手为 95% × 110% = 104.5%。蓄力速度使用既有加算增益，再以基础时长除以总速度；仅此选项时，2 秒基础蓄力为 2 ÷ 1.1 秒。

## 外观与资产

- 移除原配重坠体；保留沿原装安装端适配的 3.2 mm 轻薄金属收口，封住握柄底端。
- 可编辑源：`NoPommel_EndClosure_Editable.blend`；FBX：`Export/SM_CommonHammerPommel_NoWeightCap_V1.fbx`。
- 1318 三角面；安装坐标沿用原装接口，局部 Z 约 -8.5 cm。
- UE 网格：`/Game/Weapons/CommonHammerPommels20261014/NoPommelV1/SM_CommonHammerPommel_NoWeightCap_V1`。
- 沿用原装战锤表面与通用锤头钢材，不创建新的材质体系。
- 图标复用已采用的银色减号移除图标：`Content/ColdSteelData/AttachmentIcons20260913/rune_false.png`，新键为 `pommel_no_pommel`。不使用表示原厂配置的 `false` ID。
- 已有金属战锤通过 `warhammer-modules.json` 的 `pommel.no_pommel` 替换部件；通用库供其他具备对应接口适配的锤类复用。

## 接入范围

通用配件读取和属性累积、角色工具属性、单机与服务器重击扣费、工坊选件详情与总览、物品提示及比较摘要。该选项以稳定 ID 走已有装备配置和存档流程。

同时补全此前双棱尖头锤物理防御穿透在锤类专用详情、总览、提示及摘要中的展示；其已批准的数值保持不变。

## 制作记录

`author_end_cap.py` 制作收口；`import_no_pommel.py` 保存网格和 UI 纹理后调用 `register_no_pommel.py` 登记数据。数据写入前备份至 `Before`。重新制作外观保留已有同 ID 后续调整过的数值。

本轮未运行游戏、自测或验收；实际资产保存与编译结果记录在 `import_receipt.json`、`commandlet_receipt.json`、`editor-build-receipt.json`、`game-build-receipt.json` 和 `delivery.json`。
