# 掉落物稀有度光效 — 2026-09-11

已为 `AColdSteelPickup` 的地面物品添加中心柔光和向上渐隐光柱，参考无主之地通过颜色辨识掉落物的表现。实际截图：[LootGlowInGame](../../Saved/LootGlowInGame.png)。截图为正立排列的材质展示；物理下落、旋转和拾取另由真实掉落审计验证。

## 资产检查与选择

实际加载检查结果保存在 `Saved/LootFXAssetReview.json`：

- 项目 `/Game/NiagaraExamples/Materials/MasterMaterials/M_Glow_Capsule`、`M_FresnelGlow`、`M_Flare` 均可加载，包含辉光、耀斑、衰减等可参考材质。已读取材质类型及参数，并非仅凭文件名判断。
- UE `/Niagara/DefaultAssets/Templates/Emitters/StaticBeam`、`DynamicBeam` 均可加载，类型为 NiagaraEmitter；它们是发射器模板，不是直接绑定稀有度的掉落成品系统。
- 本次使用原创柔边材质、UE BasicShapes Plane 和 MaterialBillboard 构成专用掉落标识。无需复制武器/爆炸粒子系统，也不引用外部游戏资源。原示例资产保持原样。
- 视觉参考：[Borderlands 3 掉落截图](https://www.millenium.org/guide/345228.html)，中心亮点、细长光柱及稀有度颜色关系；不复制其美术文件或照搬本项目已有高阶稀有度配色。

## 实现

- `ColdSteelPickupGlow.cpp`：初始化按 `rarity`，缺失时按 `grade`，再缺失时按普通显示。颜色取冷钢 UI 色相，提高世界光效饱和度。
- 普通白、优秀绿、稀有蓝、史诗紫、神话金、传说粉红，后两档保持本项目原 UI 含义。
- `LootFXRoot` 跟随刚体中心，使用绝对旋转/缩放；光柱局部 X 为世界竖直，仅绕世界 Z 朝向镜头。物品滚动不会将光柱带倒。
- 每件物品一张光柱面片和一张中心 billboard；不生成逐物品动态点光源，不改变模型原有材质。呼吸效果由材质 Time 驱动。
- Additive / Unlit、渐隐边缘、DepthFade、EyeAdaptationInverse 曝光补偿。保留深度测试；光效没有碰撞、没有阴影，80 米组件剔除。未进行大量掉落物性能基准，不给出 FPS 保证。
- 组件随掉落 Actor 销毁，读档重建时依据物品数据重新生成，不单独保存光效 Actor。
- 材质位于 `/Game/Items/LootFX`，生成脚本 `Tools/AssetPipeline/build_loot_glow.py`，对应 AlwaysCook 目录已加入。

## 数据与旧存档

| 物品 | 稀有度 | 光效 |
|---|---|---|
| 强化石 | 史诗 | 紫 |
| 魔法粉尘 | 史诗 | 紫 |
| 沉重、锋利的卷轴 | 普通 | 白 |
| 狼蛛卷轴 | 优秀 | 绿 |
| 骷髅射手卷轴 | 稀有 | 蓝 |

`items.json` 更新以上定义；卷轴补充与原 grade 一致的 rarity，统一 UI 与世界表现。`ReloadProfile` 经原 A/B 校验事务刷新这六种物品的授权字段。材料数量、最大堆叠 99999、卷轴最大堆叠 99、附魔效果保持原样。正式玩家存档没有被测试夹具替换。

## 验证

- 原生编译通过，`Saved/LootFXBuild.txt`，最终本次模块后缀 `9111221`。
- 材质脚本 `LOOT_FX_MATERIAL_PASS`，无最终 Python 异常。命令行退出码 1 包含现有 GameFeatureData 设置与端口占用错误，不作为全工程 commandlet 通过。
- 首轮 A：88/0，发现白天亮度不足后加入曝光补偿。最终 B：**88 项通过，0 失败**，`Saved/LootGlowAuditB.log`。
- 验收六种实际物品：旧数据稀有度刷新、数量/效果保持、模型和刚体加载、落地、坐标/旋转重载、中心与光柱存在、光柱竖直居中、无碰撞、白蓝绿紫颜色、瞄准拾取及拾取后保存。已实际查看最终游戏截图，无掉落材质编译失败。
- 未执行完整打包、夜间场景及大批量性能测试。当前为 UE 编辑器宿主的独立游戏运行。

复现参数：`-game -LootGlowAudit -ColdSteelProfile=<独立测试名>`。正常玩家重新进入游戏时应用旧物品稀有度更新。
