# 唐刀：破锋燕翎刀身

本次按用户提供的“方案二：破锋燕翎式刀身”制作唐刀专属的 `blade_1/yanling_edge`，在改造台「剑身Ⅰ」显示“破锋燕翎刀身”。初版先完成外观；随后按用户“调整为”的要求，将原参考方案的第二段横斩伤害 +15% 替换为第三段伤害 +40% 的过顶竖劈与前方矩形判定，同时接入攻击耐力消耗 +10%、格挡减伤倍率 ×0.90。详细运行合同与构建状态见 [战斗效果开发记录](CombatEffects20261002/README.md)。

原装刀根从安装面 z=1.4 cm 到 z=34 cm 的几何、UV、龙纹、原始结构法线和 SurfaceV2 材质保留。后段以共用边界接入新钢刃，燕翎刀尖采用折线轮廓及折面收锋，两侧各两条导槽具有 0.55 mm 的实体凹陷。新刀身尖端维持 88 cm 纵向长度，不改护手、握柄、柄尾、骨骼挂载或动画。

新钢刃使用独立 4096×4096 BaseColor／ORM／Normal 图集：层叠锻钢纹、微细磨削纹与抛光刃口，ORM 顺序为 AO／粗糙度／金属度，OpenGL 法线在 UE 导入时翻转绿色通道。原装刀根继续引用自己的原图集。

两个材质槽分别为 `M_TangDaoSurface`、`M_TangDaoYanlingSteel`。新钢刃材质复制已经保存的 `M_TangDaoBladeRuneSurface`，仅替换三张钢刃 PBR 贴图；沿用共鸣／侵蚀／导魔的遮罩、动态参数、曝光补偿、Substrate 自发光输出和无符文时的采样跳过。前景旋风对应材质与目录也随新钢刃登记。刀身采用普通静态网格路线，完整 LOD0 与两档显式 LOD 一并导入，不依靠低精度 Nanite 回退几何。

制作源：`TangDao_YanlingBlade_Editable.blend`；游戏交换件：`Export/SM_TangDao_Blade_yanling_edge.fbx`（3 LOD）及 `.glb`（完整 LOD0）。`author_blade.py` 与 `author_maps.py` 可继续编辑制作。`render_menu_icon.py` 只用于生产改造栏图标，不是验收场景。正式图标由内置 imagegen 按实际模型图及已有金属方框母版制作，提示词与输入记录在 `imagegen_prompt.json`。

后台执行 `import_assets.py` 实际导入并保存网格、三张贴图、原生符文材质及旋风变体、改造栏 Texture2D，然后以 `catalog_extension.py` 增量登记专属选项。父级目录安装及 SurfaceV2 刷新脚本保留这个已保存的独立扩展，不覆盖钢刃图集。导入完成状态与保存资源路径见 `import_receipt.json`。

初版后台导入已完成并保存 7 项 UE 资源：1 个带三档 LOD 的刀身网格、3 张 PBR Texture2D、2 个原生符文材质（含旋风变体）和 1 张正式改造图标。刀身模块目录、唐刀专属改造选项、表面绑定及旋风材质映射已合并落盘。初版命令行导入返回 0，当时没有修改 C++；后续战斗改造的 C++ 与构建单独记录在 `CombatEffects20261002`。保存记录为 `import_receipt.json`，目录合并记录为 `catalog_receipt.json`，制作 LOD 三角数为 121480／66814／31584。

正式图标：`Icons/ue_tang_dao_blade_1_yanling_edge.png`；内置 imagegen 的完整提示词与输入见 [imagegen_prompt.json](imagegen_prompt.json)。游戏读取的正式 PNG 及同名 Texture2D 均位于 `Content/ColdSteelData/AttachmentIcons20260913`。

没有启动 UE 编辑器或游戏，没有运行测试、验收渲染或截图。图标生产属于接入所需素材。显示效果、持握与改造预览交由用户测试。
