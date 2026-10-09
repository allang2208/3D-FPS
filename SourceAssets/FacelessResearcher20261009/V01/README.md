# 无面女性研究员 V01

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

2026-10-09。用户提供减面后的 `C:/Users/allan/Downloads/Meshy_AI_Gray_Full_Body_Manneq_1009014620_texture.glb`，要求继续三视图方案并套用现有女僵尸动作。本目录负责身体绑定、独立研究员服装、动作适配和 UE 接入；不运行游戏、预览或自动验收。

## 身体与绑定

输入包含 110905 个导入顶点、199621 个三角面与三张原始贴图，没有现成骨架。原文件复制到 `Source/`；SHA-256 为 `6a9c56a05e39cae186e68d8975252401fcf19a5463dfd645ed3bc534b3f93746`。保留用户减面后的完整身体、UV 和材质，不再对身体减面。

按此模型的肩、肘、腕、髋、膝、踝和指尖建立解剖映射，双手仅从同侧手部表面传递细分手指权重，肩部权重沿实际身体邻接连续化，再绑定到未改参考变换的 Nurse 骨架。161 骨导出层级包含 FBX 容器根。没有修改原护士、接待员或男性安保。

作者体型设为 1.88 m；原生绑定坐标的完整身体高度约 1.8021 m，运行组件使用统一 1.043208 倍缩放恢复设计高度。没有在骨骼轨道写入非均匀缩放。胶囊半高 94 cm，网格相对 Z 约 -96.6716 cm，依据作者鞋底与胶囊地面间距制作。此值为制作参数，不是游戏站姿实测结果。

## 独立服装

灰白研究员白大褂、深灰窄身长裤、黑色包脚平底鞋、胸袋、两侧贴袋、深色口袋包边、金属胸牌及 RESEARCH 字样。

- 上衣在原生绑定坐标构造连续肩袖外表面，开口与外轮廓确定后再制作同权重内壁；领口使用共享边界延伸，避免独立领座错开。
- 白大褂为大腿长度、A 形下摆，前后留活动开衩。每侧下摆主要跟随骨盆和同侧大腿，并制作随动作变化的表面修正。
- 裤装从新身体独立生成；切割前按蒙皮家族排除手臂，避免把低于裤腰的手部残片带进裤子。仅新衣物按其用途分配网格密度。
- 包脚鞋从闭合脚体积制作完整鞋头和鞋底，再打开鞋口、加入内壁。完整身体保留双脚；运行显示副本不显示封闭鞋内的脚趾和脚背。
- 19 个可编辑衣物与细节对象；穿衣组合导出 219505 三角面。身体、衣物、运行组合分别保留。
- 原 Meshy 身体贴图保留；新衣料、饰边、皮革和金属使用独立 PBR。织物微纹依据 20 cm 物理平铺尺度的程序表面场制作，不称作扫描或高模烘焙素材。

## 女僵尸动作

从项目当前 `BP_NurseZombie` 实际引用导出并复用：

| 用途 | 源资产 | 时长 |
| --- | --- | --- |
| 待机 | `/Game/Monsters/NurseZombie/A_Nurse_idle` | 约 10.2667 s |
| 移动 | `/Game/Monsters/NurseZombie/A_Nurse_walk` | 约 3.2667 s |
| 攻击 | `/Game/Monsters/NurseZombie/A_Nurse_attack` | 约 3.3333 s |

保留源骨骼轨道、1.4–1.7 s 命中窗口、0.8 s 恢复等待与 52 cm/s 移速。移动片段额外按身体统一缩放的倒数修正 rate scale，配合现有 Nurse 播速逻辑。其他玩法数值继承原护士配置。

离线制作 53 个衣物修正形态：待机 17、移动 18、攻击 18。上衣按实际身体三角面及变形法线保持表面间距，下摆依据动作中的身体包络作平滑避让；内外壁同步，口袋／门襟／胸牌随主衣修正。UE 动画副本只增加相应 morph 曲线，不新增运行时布料求解、Tick 或独立物理衣片。

完整源动作保存在作者文件的静音 NLA 中；动作源导出、`nurse_source.json`、`corrective_manifest.json`、`corrective_curves.json` 都是制作输入与记录，不代表已通过动作验收。

## 接入与恢复

目标命名空间 `/Game/Monsters/FacelessResearcher`，蓝图 `BP_FacelessResearcher`，F6 名称“无面研究员”。独立 `SKEL_FacelessResearcher` / `PA_FacelessResearcher` 从现有 Nurse 同源资源复制；不覆盖其他角色资产。

2026-10-09 已完成后台导入和保存：`ue_delivery.json` 为 `stage: saved`，记录 33 个已保存资产，包括三份骨骼网格、骨架、物理资产、贴图、材质、三段动画副本和角色蓝图。导入 commandlet 正常退出，退出码 0。`build_receipt.json` 记录 `FPSGAMEEditor` 与 `FPSGAME` 两个原生目标均构建成功，退出码 0；F6“无面研究员”入口已编入。

未启动编辑器界面、UE 游戏或 PIE，未截图、渲染或追加自测，由用户测试外观、衣物变形和动作效果。构建与保存完成不代表已通过运行时或视觉验收。

恢复入口：`Tools/FacelessResearcher/prepare_inputs.py` → `build_recipe.py` → `author_character.py` → `tailor_motion.py` → `prepare_delivery.py` → `import_assets.py`（已有编辑器时可拆为 materials / 单网格 / blueprint 批次）。作者源为 `Authoring/Inputs.blend` 和 `Authoring/FacelessResearcher_V01.blend`，交付网格位于 `Delivery/`。三视图与提示词保存在上级 `Reference/`。

模型来自用户提供的 Meshy 文件，动作来自项目现有女僵尸资源；两者来源独立，不把其他工具的许可用于这些原始资产。没有发布二进制或执行 Git 推送。
