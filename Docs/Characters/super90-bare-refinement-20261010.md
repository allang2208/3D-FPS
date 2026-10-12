> 2026-10-13 整理：本方案已被用户否定并回退。整个制作目录已移至 `trash/super90-retired-20261013/SourceAssets/Super90BareRefine20261010/`；当前使用 Super90JointSurface20261012，不得重装旧权重方案。逐文件恢复清单见 `Docs/Weapons/super90-retired-20261013.json`。

# Super90 裸手修正（用户已否定，2026-10-11 回退）

用户反馈“手臂完全扭曲，退回”。本版权重分摊和专用材质修改已被否定，停止继续优化及发布。下文为历史制作记录，其中的分析和保存成功不能作为该方法有效的证据。`REJECTED.json` 及入口脚本的拒绝执行标记用于防止再次安装该版。

范围由用户限定为 Super90：其他枪械手臂外观保持当前版本。前一轮 MPFB 整臂改形已被用户否定并回退，本轮不采用该几何变形。

## 制作依据

Super90 原生骨架和 M4 的辅助骨语义不同。原生 `twist_arm_1/2/3` 对应 `lowerarm_aux / lowerarm_twist_02 / lowerarm_twist_01`，其旋转分别承担末端辅助骨旋转量的约 41.33%、72.7%、100%。原生 `lowerarm` 是未附加这些扭转的肘铰链。

旧裸臂制作把 M4 的主要前臂权重直接映射给 `lowerarm_aux`，肘部附近因此立即承受较大的扭转。读取原始动作制作数据时，左臂待机中三个辅助骨相对铰链的旋转约为 55.87°、98.26°、135.16°。这些是制作输入数据，不是本轮运行验收结果。

另一个独立问题是 Blender FBX 会翻转各 UV 层的 V。Super90 的 UV1–3 同时承载标准皮肤坐标和法线，公共皮肤材质却按未翻转数据读取，影响纹路投射和腕部过渡区域。

## 本轮调整

- 使用原生肘铰链和三个前臂辅助骨，按肘到腕的纵向位置及平滑曲线重新分摊旋转。每份模型修改 5,710 个顶点的前臂权重。
- 保留每个顶点的前臂总权重，以及手掌、手指、上臂等其他骨骼权重。没有改参考顶点位置、骨长、绑定矩阵或动画。
- 为 Super90 单独复制 Arms / Hands 父材质和实例，修正 `RestPosition.y = 1-y`、`RestNormal.xz = 1-xz`。UV0 的手部贴图及现有网格 UV 均保持原数据。
- 独立材质继承当前公共材质的无视差、弱微法线、较轻颜色及粗糙度噪声；公共材质本身保持原样。
- 两份活动网格共用这次修正：整枪视模及换装系统引用的独立裸臂。其他枪械、衣袖、手套和枪体材质不在修改范围。

活动资产：

- `/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7`
- `/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7`
- 专用材质目录：`/Game/Weapons/Super90/BareRefine20261010/Materials`

## 制作源与回退点

工作目录：`SourceAssets/Super90BareRefine20261010/`。

- `forearm_weights.py`：原生辅助骨权重规则；UE 补丁和 Blender 作者源共用。
- `author_patches.py` / `Authored/`：从回退后的原始 Super90 包对应快照制作权重修改。
- `super90_bare_materials.py` / `install.py`：独立皮肤材质及两份 UE 网格的实际保存。
- `update_editable.py` / `source_saved.json`：可编辑 Blend 及两份参考 FBX 已导出记录，未导出或修改动画。
- `Before/`：被修改文件的原始备份。UE 写入前也备份对应原始包。
- `Saved/*.json`、`materials_saved.json`：只有实际 UE 保存完成才生成的回执；脚本本身不代表已接入。

Super90 自身的 `author_super90.py` 与 `import_super90.py` 已加入这次规则和专用材质，后续完整重制会保留修正。没有运行完整枪械重制或重新导入音频、衣物和动画。

## 历史写入状态（非当前采用版本）

可编辑 Blend、两份 FBX 和源流程更新已落盘。用户停止游戏并关闭编辑器后，通过后台 commandlet 完成两份活动网格及四份专用材质资产的编译、绑定和保存。

权重使用 `copy_skin_weight_profile_to_skeletal_mesh` 直接写入默认蒙皮配置，没有把整枪几何通过转换器重建。两份网格均保留 1 个 LOD。实际保存记录位于工作目录的 `Saved/3ca77250fe28.json`、`Saved/41ae04f60896.json` 及 `materials_saved.json`。

最终执行记录为 `install-commandlet-01.log`：两份网格保存完成，命令执行报告 0 个错误。5 条启动警告来自既有 ModelingService 的 Python 同名函数暴露；本轮日志没有皮肤材质编译失败或默认材质替代信息。早先 `install-01.txt` 的 PIE 阻挡、`install-02.txt` 的编辑器已退出连接失败，不作为完成记录。

遵照用户规则，没有启动游戏、制作验收渲染或追加测试。关节形变和表面最终效果由用户体验确认。

## 2026-10-11 回退

已在编辑器关闭、UE 资产互斥锁持有期间，恢复本轮开始前的两个原始 `.uasset` 包、可编辑 Blend、两份 FBX 和两个作者／导入脚本，共 7 个文件。恢复原始资产包同时恢复其中原来的蒙皮与公共材质引用。新建的专用材质保留为未使用的失败版本资料，制作入口停用。

实际回退完成记录：`SourceAssets/Super90BareRefine20261010/rollback_saved.json`。被撤回文件保留于 `RejectedFiles/`；原始备份保留于 `Before/`。没有运行游戏或追加验收。
