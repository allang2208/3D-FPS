# 玄脊图标重制与骨架狙击枪托分类

用户要求：玄脊碳纤维枪托图标按正式标准重做；骨架狙击枪托改为特殊改造。

## 已完成

- `Source/FPSGAME/Weapons/GunsmithModificationTier.h` 将 `stock / sniper_skeleton_stock` 在 M24、SVD、SVCH 三种已适用枪型上统一归为 `Special`。沿用原 ID、属性数值与存档引用。
- `build.ps1` 已完成普通 `FPSGAMEEditor` DLL 构建，输出见 `build.log`。未启动编辑器或运行游戏测试。
- 从当前正式资产对应的 `M24JointClean20261106/M24_HorizontalJointClean.blend` 取出最新枪托，移除无关枪身；左侧安装端、右侧肩垫、水平正交侧视。保留碳纹、叶形凹槽、UV、法线和材质分区。
- `stock_actual_source.png` 是重新制作的 1024×1024 透明模型素材，不是最终带框图标。`StockIcon_Editable.blend` 与 `render_source.py` 保留可编辑制作源。
- 灰阶助手的基色映射仅在独立图标场景改为 `0.025 + 0.48 × Y^0.60`，避免把碳纹与橡胶全部提亮成白模；未改游戏材质。

## 图标未完成的部分

按 `attachment-icons.md`，以已认可的 `FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 为框体参考、实际模型素材为主体，调用内置 imagegen 生成新标准图标。服务返回 HTTP 400 `moderation_blocked`，类别 `violence`，request ID `1dd235bb-c25d-4763-a89b-adbe3c8d45c5`。没有生成最终图片，未重试该请求。

正式 PNG 与 Texture2D 均未替换，未执行导入。现有两处稳定引用仍是 `Content/ColdSteelData/AttachmentIcons20260913/ue_m24_stock_m24_carbon_spine_stock` 及 `FramedFirearms/ue_m24_stock_m24_carbon_spine_stock`。`Before/` 保存本轮开始时的原文件，`baseline.json` 记录其哈希。

不要将本轮透明模型素材或之前的旧图标描述为已完成标准图标重制。图标成图与接入仍待完成；分类代码构建完成不表示游戏验收通过。
