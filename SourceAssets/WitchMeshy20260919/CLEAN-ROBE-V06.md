# 巫婆原裙修复 V06

2026-09-20。针对下半身大片黑面、误带手部和破碎问题，沿用原 Meshy 模型及 PBR，在本地修正装配、接缝蒙皮与布料制作数据。未重新调用生成服务，未制作新动作，未运行 PIE、预览渲染或游戏测试。

## 2026-09-20 显示消失修正

首次 V06 接入存在两处错误：网格保存的 FBX `convert_scene_unit` 为 false，动画却为 true，UE 内模型高度实际仅 1.9 cm、骨架缩放 0.01；另外，重导入按源区段编号保留了代理的禁用标记，导致原裙区段 `bDisabled=true`。角色仍使用 94 cm 半高胶囊的脚底偏移，缩小的模型与手部挂点因此位于正常地面下方。这里是导入单位及区段状态错误，不是新的模型制作失败。

已在重导入资产自身的 FBX 数据与导入选项两处明确开启场景单位转换，比例为 1，并指定 FBX factory。原来按错误尺寸生成的布料记录被替换为 `Witch_CleanRobe_ChaosV06Cm`，重新提取厘米单位代理及碰撞体。原裙与身体的导入区段、持久源区段数据都恢复显示；代理仍不进入最终显示 FBX。

修正脚本 `Tools/Witch/repair_v06_visibility.py` 已完成提取、最终模型重导入、绑定及保存。当前回执为 `ue_clean_robe_v06_visibility_fix.json`，UE 导入结果位于 `Saved/WitchV06-visibility-import-result.txt`：高 190 cm，Hips/Head/手/脚骨架缩放均为 1，两个显示区段 `disabled=0`，布料代理范围 Z=2.2～98 cm。故障资产备份在 `trash/witch-v06-before-visibility-fix-20260920/`。

常规构建 `Saved/BuildEditor/build-20260920-215620.log` 已完成此前绑定修正。此次制作函数的单位版布料和显示标记修正已通过 Live Coding 应用并用于资产保存；编译请求的桥回执曾超时，实际导入已成功执行新版 `V06Cm` 制作函数。后续常规构建将这些编辑器制作函数写入基础 DLL；运行角色使用本次已保存资产。没有启动 PIE 或进行游戏验收，需在 F6 清除旧实例后重新生成，由用户测试。

## 源文件与保留范围

- 制作脚本：`clean_robe_v06.py`。
- 组合源：`Authoring/CleanRobeV06/Witch_CleanRobeV06.blend`。
- 分件：`Authoring/CleanRobeV06/Parts/` 内帽、头/头发、原左手、原右手、上袍、原下袍、原脚的独立 Blender 与 FBX。布料代理另外保存，不作为显示网格。
- 五段可编辑动作源及上下身动作层位于 `Authoring/CleanRobeV06/`，已换成修正版显示部件，保留原动作键。`Delivery/CleanRobeV06/A_Witch_*.fbx` 复制既有骨骼动作，不重采样。
- 最终模型：`Delivery/CleanRobeV06/SK_Witch_CleanRobeV06.fbx`，只含七个原模型显示部件。
- 布料提取模型：同目录 `SK_Witch_CleanRobeV06_ClothBuildSource.fbx`，额外包含代理。提取后必须用最终模型重导入，不能将它作为最终显示输入。

原模型的显示顶点位置、UV、分裂法线和 PBR 保留。移除了 V04/V05 错误适配的 `Witch_InnerBody.001` 及沿用的 `Witch_InnerCalves`；没有把另一个新人体或新裙子塞回原裙内部。此前的黑色大面和误带 Quinn 双手不再进入最终导出。

旧制作源继续用于追溯，V05 不再是当前制作入口。替换前游戏模型与物理资产备份在 `trash/witch-v05-before-clean-robe-v06-20260920/`，含原路径和 SHA-256 记录。

## 接缝与布料

腰口 216 个共享源顶点，两侧统一骨盆权重，并向上袍内部平滑过渡。脚部切口 98 个共享源顶点，裙侧使用与原脚完全相同的蒙皮权重，23～38 cm 高度带向骨盆支撑平滑过渡。显示部件仍可分别编辑。

新代理为 64 个角向点、37 圈，共 2368 顶点 / 2304 四边形。点始终位于各自径向半线上，未命中部分插值半径；采用环向和纵向平滑，不再跨洞取任意最近点并强改高度。可见原裙不参与此平滑。

布料固定 82 cm 以上腰带区、26 cm 以下脚踝区；只有中段得到次级摆动，最大允许位移 6 cm。动画驱动强度改为 0.25，增加阻尼，减小碰撞厚度。布料使用单独的骨盆/双大腿/双小腿五个胶囊形体，不继承长裙自动生成的躯干碰撞体。布娃娃继续使用原角色 Physics Asset。

`AWitchMonster::PrepareCombatPhysics` 依据 `OriginalRobeV06` 材质槽进入这条制作分支，删除旧模拟引用，使用新代理提取数据。绑定同时保存源区段 `UserSectionsData`；重导入后通过原布料对象解除旧 LOD 映射再绑定，避免只改临时区段或生成两份模拟记录。

## 接入与边界

导入脚本：`Tools/Witch/import_clean_robe_v06.py`。已完成布料提取、最终显示模型重导入与持久绑定、现有 F6 引用接入和保存；实际保存阶段见 `ue_clean_robe_v06.json`，成功回执为 `Saved/WitchV06-import-02.txt`。

继续写入 `/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy`，保持现有 F6 `Witch` ID、角色类、导航规格、骨架、五段动画引用与道具引用。路径中的 V05 是兼容已有引用的包名，新的制作源为 CleanRobeV06。

必要常规构建：`Saved/BuildEditor/build-20260920-212819.log`。随后布料 LOD 映射与保存顺序修正通过 Live Coding 构建，记录 `Saved/WitchV06-livecoding-02.txt`；该函数仅负责编辑器制作，运行模型使用保存后的布料资产。常规构建完成后才会将最后这处函数修正写入基础 DLL。

导入日志含原密集网格的零长度法线/切线提示；本轮保留原显示拓扑，没有据此宣称着色、步态或碰撞已验收。未新增脚掌斜坡 IK，也未重做持杖动作。用户通过 **F6 → 怪物生成 → 巫婆** 清除旧实例并重新生成测试。
