# 唯一巫婆：巫婆·重建候选

用户指定只保留「巫婆·重建候选」，删除普通巫婆和「巫婆·动作基础候选」。显示名及稳定 ID `WitchRebuilt` 保留，当前外观为 Fabric09，双手为 Hands08，网格/布料为 Seams07 / Drape07。

## 运行入口

- `DevelopmentSpawnComponent` 移除 `Witch`、`WitchFoundation`，仅保留 `/Script/FPSGAME.WitchRebuiltMonster`。
- `AWitchMonster` 保留当前重建版依赖的施法、投瓶、AI 与死亡逻辑，改为 Abstract；它是公共战斗基类，不能作为另一款巫婆生成。移除旧模型、旧动作、旧瓶子、旧挂点和旧布料编辑器制作代码。
- 动作基础候选的角色类和专用动画实例四份 C++ 文件移出 Source，归档至 `trash/witch-variants-20260922`；旧类路径重定向到保留版本。
- 重新生成预加载表，移除旧版本的预加载路径。生成器跳过自己的输出，避免已删除路径从旧表重新进入新表。

## 资源边界

按 UE 包引用移除旧 OriginalRobeV05 / SpellSupportV07 以及 Foundation 动画中不再被保留内容引用的包，先保留原文件和 SHA-256，再通过编辑器删除活跃 Content 中的副本。仍被现有资产引用的包不删除。

Foundation 的网格、骨架、物理与材质仍是 `Tools/WitchRebuilt/import_assets.py` 的重建输入；原 Meshy 外观、法杖、贴图及外部 Foundation 动作 Blend 也是保留版本的源依赖。这些素材不是额外的可生成巫婆。保留 `SourceAssets/WitchRebuilt20260921` 和实际依赖，不能直接删除整个 WitchFoundation/WitchMeshy 目录。

归档清单：`Docs/AssetArchives/witch-variants-native-20260922.json`、`witch-variants-assets-20260922.json`。当前交付记录位于 `SourceAssets/WitchRebuilt20260921/Revision10`。

## 状态

源码修改、四份原生废案归档与常规 Editor 构建已完成；构建日志为 `Saved/BuildEditor/build-20260922-175034.log`。先前一次构建遇到 Abstract/NotPlaceable 继承标记冲突，基类采用 Abstract 后构建成功。

12 个旧 UE 包已从 Content 移除并完成带 SHA-256 的归档：Foundation 两段动作、OriginalRobeV05 的五段动作/网格/骨架/物理包、SpellSupportV07 两段动作。保存记录为 `Revision10/archive_assets02.txt` 与 `asset_retirement_result.json`，上述归档包无保留内容的外部包引用。当前打开关卡没有旧版角色，未发现旧版派生 Blueprint；没有保存或改动其他关卡。

接入前一次删除调用因新启动的 PIE 而停止，未删除资产；按已有授权正常结束试玩后，下一次调用完成归档。编辑器保持打开，F6 仅保留「巫婆·重建候选」。

未启动 PIE、未做运行或画面测试，完成后由用户通过 F6 唯一巫婆入口试玩。
