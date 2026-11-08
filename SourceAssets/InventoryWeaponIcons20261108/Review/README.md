# 伐木斧与 M249 图标复查

范围：2026-11-08 两件武器背包图标这一轮的制作、落盘、缓存和相关库存/掉落联机路径；不代表此前魔法、近战动画或全部武器功能的全面验收。

## 发现与修复

`ColdSteelWeaponIcons.cpp` 的手部隐藏条件按 `hand` 子串匹配，只排除了 `handguard`、`charginghandle`、`carryhandle`。实际 M249 的 `M249_Factory_Handle` 是拉机柄，会命中错误隐藏条件。相同条件也存在于 `ColdSteelPickupWeapon.cpp`，共享掉落的服务端构建与客机 `OnRep_SharedItem` 均会使用它。

两处均把以 `_handle` 结尾的武器柄材质排除出手部子串匹配，保留原有真实手臂/衣袖材料识别及 `HandLeft` 一类名称；M249 图标配方版本从 `icon_studio=3` 更新为 `4`。第一处错误发生在材质可见性过滤，早于图标边界计算和捕获，并非网络传输丢失了拉机柄。

复现前提：以当前 `SK_M249_V7` 生成背包图标或共享掉落。预期是显示枪械的拉机柄且不显示第一人称手臂；旧条件会把拉机柄材质段也隐藏。修复前源码、PNG、纹理资产和保存回执保存在 `Before/`。

## 联机代码覆盖

| 路径 | 核对内容与结果 |
| --- | --- |
| 背包请求回执 | `UColdSteelInventoryReply.Changed` 携带完整 `FColdSteelItem`，`Data` 是反射字段。`QueueInventoryReply` 经 `ColdSteelProfileTransfer` 序列化、分块发送；客机应用实例数据后广播 `OnChanged`。 |
| 共享容器 | 服务端 `ContainerItems` 保留物品数据；客机仅设置 `NetView` 容器归属，随后刷新界面，图标仍按该物品自身的配件生成。 |
| 档案镜像/重新载入 | 物品数据随完整档案存储和传输；本次没有改实例结构、占格、装备槽或存档版本。客机库存/配件回执的刷新链路仍存在。 |
| 共享地面掉落 | `SharedItem` 为初始复制字段，`OnRep_SharedItem` 调用 `InitializeItem` / `BuildWeapon`；主客机共用本次修复后的材质过滤。 |
| 图标缓存 | `UColdSteelWeaponIcons` 是 GameInstance 子系统，缓存及任务队列是实例成员；配方读取传入物品的 `gunsmith_parts` 并排序，不依赖当前本地装备或枪匠草稿。 |
| 异步回读 | 任务保存物品副本与配方，曝光在提交时写入独立 Packet；完成时对照配方，界面仅按当前实例的配方取图。M249 的照明参数会在下一件非 M249 物品准备时恢复。 |

上述是源码与数据链路检查，未运行真实主客机 UDP、晚加入/断线重连或丢包测试；不能据此宣称完整联机实测通过。

## 图像、资产与构建证据

复查开始时两张正式 PNG 均与此前保存回执的 SHA-256 相同。伐木斧为 512×1536 RGBA，非透明边界 `(48,68)-(464,1468)`；M249 为 800×320 RGBA，修复前非透明边界 `(38,43)-(764,277)`。两图 alpha 范围均为 0–255，主体无裁边。已直接查看这两张实际图像。

`FPSGAME.Build.cs` 已将 `Content/ColdSteelData/...` 作为 UFS RuntimeDependency；两张 PNG 沿用原目录路径，现有打包入口包含它们。

- 本次构建结果：本目录 `build-FPSGAMEEditor.json`、`build-FPSGAME.json` 及 `Logs/`。
- 修复后的 M249 生产与保存：上级目录 `m249-authoring.json`、`saved-icons.json` 和带时间戳日志。
- 独立进程读回资产：`read_saved_assets.py` / `read_saved_assets.ps1`，结果 `saved-assets-readback.json`。该检查只读取纹理与实际 M249 材料绑定，不运行地图或修改玩家存档。
- 目录/PNG 最终检查：`catalog-artifact-check.json`。

本次执行结果：Editor 与 Game 均已编译、链接成功；修复后的 M249 出图 commandlet 返回 0，正式 PNG 与两张 UI 纹理重新保存成功。独立后台进程读回两张纹理的尺寸、UI 组、压缩、无 mip、sRGB 与不流送设置，`errors=[]`；同时确认当前 M249 的拉机柄材料绑定存在。最终 PNG/目录检查通过。修复后 M249 PNG SHA-256 为 `85732e1689ff747fb109e893b20432c01b4d8887a7f8229a161b21fbe2e85d2f`，伐木斧图像内容不变。

未进行背包实战、主客机截图或多人游戏验收；联机结论限于上述源码链路检查。
