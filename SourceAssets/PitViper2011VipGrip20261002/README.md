# 2011 VIP 专属改造：蝮蛇防滑纹

**当前源（整理于 2026-10-03）：** 纵向覆片与专属图标位于 `../PitViper2011ViperLongitudinalGrip20261003`，原作者入口转发当前源。此目录保留初始材质/绑定建立脚本和生产记录供恢复；旧 Exports、Icons、Textures 已移入 trash，下文首批经过中的产物路径属于历史说明。

**2026-10-03 重制：** 用户否决原规则菱格表现，当前制作源、定向排查与修复记录见 [防滑纹重制](../PitViper2011GripRebuild20261003/README.md)。`author_grip.py` 已转到重制入口，`authoring.json` 指向重制模型和纹理；下文保留首批制作经过，不能据此选择旧导出。UE 资产身份及改造 ID 沿用首批路径。

本批为用户概念图续作，选项 `pit_viper_vip_scales`，仅属于 `ue_pit_viper2011` 的 `reargrip`（握把防滑纹）。用户于 2026-10-03 指定腰射随机散布减少 15%，使用 `hip_spread_mult=0.85`；实际选项、专属选项合并来源、提示文字与生成脚本同步维护。

模型按当前 Pit Viper 原厂聚合物握柄采样，左右掌侧各一片独立表面层。鳞片连续菱形交错，带方向性细刻纹和轻微流向；香槟金细边、几何蝮蛇标记为贴合表面的独立金属槽。VIP 覆盖区避开下方原厂卡口，原始枪体、握柄、骨架、手臂和动作保持现有版本。鳞纹制作了 2048² BaseColor、Normal、ORM 及母版 Height；Height 留作作者源，运行法线和轻微几何起伏承担细节。原厂下部卡口与底板不按概念图重造。

金属实例以 `/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolishedSteel` 为父，属于共享 WS 母版；鳞纹复合表面为独立 PBR 材质，保持非金属。两者接入既有 `WeaponWetness` 和手枪湿材质汇总表，原有项保留。全套资源在 `/Game/Weapons/PitViper2011/VipGrip20261002`，由现有 PitViper cook 根目录包含。

`PistolGripSurface` 增加按武器／选项解析的 `variants`，公共防滑选项与宿主的 `exclusive_options` 合并。Configure、改造预览和库存图标预加载使用同一选项绑定，装配与保存沿用现有实例事务，不创建第二份持枪状态。2011 卡片沿用既有专属金色样式，并显示“VIP 专属”。重制整枪及通用配件目录时读取本批已保存回执并恢复专属绑定，防止通用三款纹理覆盖 VIP 条目。

制作入口：

- `author_grip.py`：本地 Blender 源表面拟合、原创图案、贴图和 FBX，可编辑源在 `Exports`。
- `author_icon.py`：从实际模型制作单片灰阶图标素材，仅修改图标场景，运行模型保留左右两片。
- `Icons`：灰阶素材与 image_gen 合成的正式金属框图标；图标不以整枪概念图替代。`Reference/framed_icon_prompt.txt` 保留生成指令。
- `run_import.ps1`：通过既有桥互斥，在当前编辑器或无界面 commandlet 实际保存网格、材质、纹理、图标与目录。不会启动 GUI 编辑器。
- `build_editor.ps1`：等待编译与编辑器资源释放后构建正式原生模块，不关闭占用者。
- `import_receipt.json` 和 `build_receipt.json`：实际资产保存及构建结果；不是游戏验收证据。

概念图为 image_gen 输出；握柄拟合源为 D_U 的 [Sketchfab Pit Viper 2011](https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153)，原项目记录为 CC BY 4.0，保留来源及修改归属。鳞纹、几何徽记和金属边线在本地程序制作。未启动游戏或进行验收，最终外观、装配及存档由用户测试。

2026-10-03 当前 VIP 几何源为 `../PitViper2011ViperLongitudinalGrip20261003`：两侧纵向防滑纹按原握把外形延伸，下沿沿斜向握把分界裁切，预留间距，不覆盖弹匣、底板或底部扩口。此目录的作者入口与 `authoring.json` 已指向新源；旧 Exports 为历史源。沿用 ViperQuiet 私有细腻表面材质，腰射随机散布 −15% 保持不变。实际保存状态见新目录 `import_receipt.json`。


2026-10-03 整理发布：旧短覆片 Exports/Icons/Textures 及图标记录已归档，当前 VIP 源位于 ViperLongitudinalGrip20261003。归档清单与恢复范围见 `Docs/Weapons/pit-viper2011-publication-20261003.md`，所有移动文件均可从 trash 恢复。
