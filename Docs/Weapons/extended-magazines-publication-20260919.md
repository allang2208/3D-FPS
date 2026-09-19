# 扩容弹匣发布与本地恢复（2026-09-19）

本轮包含 M4、AKM、QBZ-191 原厂弹匣延长与接触修正，以及 ASH-12 扩容和中段材质遮罩修复。M4 最终预览已获用户确认；其余实机效果继续由用户测试。本次整理仅做发布范围、依赖、散列、暂存差异与脚本语法检查，未启动游戏或新增渲染。

## 当前制作与运行入口

| 枪型 | 作者入口（SourceAssets 下） | 当前 UE 静态网格 |
|---|---|---|
| M4 | M4GridUnified20260919/author_surface.py → finish.py | /Game/Weapons/M4GridUnified20260919/SM_M4_ExtMag40_Grid |
| AKM | MagazineMouthFinish20260919/author_mouth.py；ExtMagContinuity20260919/author.py | /Game/Weapons/ExtMagContinuity20260919/SM_ExtMag_AKM40_Continuous |
| QBZ-191 | ExtMagRemodel20260919/finish.py | /Game/Weapons/ExtMagRemodel20260919/SM_ExtMag_QBZ40_Remodel |
| ASH-12 | ASH12ExtendedMagazine20260919/author.py → ASH12MagFinish20260919/author.py | /Game/Weapons/ASH12/MagazineFinish20260919/SM_ASH12_ExtMag30_Finish |

各目录的 install.py 和 install_icon.py（或 README 指定入口）完成本地导入。旧多枪安装脚本属于制作历史，不能按目录顺序批量重跑覆盖最终资产；恢复时按上表逐枪选择最终导入入口。M4 普通/扩容弹匣使用 ExtMagContact 的同枪包握动作，弹鼓独立；QBZ 不套 M4 动作。

## 必须保留的本地输入

- ExtMagRebuild 中的 Factory 原厂对象仍被后续作者读取，目录不是整包废案。ExtMagPattern 的参数、export_tangents.py 与 QBZ 源也仍是后续输入。
- ExtMagContinuity 的 AKM 最终源、QBZ 中间源和 M4/AKM 干湿连续材质仍在使用；ExtMagRemodel 保留 QBZ 最终源及历史制作链。最终 M4GridUnified 中名称含 Remodel 的原始采样场景也是 finish.py 输入。
- ASH12ExtendedMagazine 的可编辑源仍由 MagFinish 读取，其连续干湿材质仍是最终网格依赖。ASH 当前 Surface20260919 基础材质来自另一项表面制作工作，需本机已有对应资源；不能将本次源代码发布理解为 ASH 全部素材的公开分发。
- ExtMagContact 的 M4/AKM 动作与 MagazineMouthFinish 的口部材质保留。图标位于 Content/ColdSteelData/AttachmentIcons20260913，武器专属图优先，M4 同步共享回退图。
- Blend、FBX、UE 包、图像、纹理、完整采样/姿态数组及备份留在本机；本次仅发布作者代码、少量制作参数、回执、运行接入与文档。拥有使用许可不等于具有公开再分发许可。完整恢复仍需合法的原厂源包及本地依赖。

## 归档

171 个确认废案/中间记录，共 555,744,869 字节，移至 `trash/extended-magazines-20260919`。包括未接入的 M4ExtMagNormals 整套试验、M4 未采用的 author_grid、诊断渲染及各本轮目录的过程日志、构建记录和已有正式源的 .blend1。没有移动运行 Content 包或后续作者依赖的旧源。

逐文件原路径、归档路径、大小、SHA256、原因及替代入口见 [归档清单](extended-magazines-20260919/archive-manifest.json)。移动前核对范围与源散列，移动后核对目标散列。仍作为输入的历史文件不算废案，不按日期删除。

## 经验与验收边界

M4 的关键是延续原厂真实外表面槽纹，单纯重算法线不能统一造型；ASH 的深色块来自新增角点默认白色误触发枪口内壁遮罩。经验分别沉淀到武器技能的 extmag-lengthening、weapon-finish、attachment-icons，个人源与工程镜像同步。

此前必要构建已完成。本轮发布检查不代替实机换弹、穿模、雨天材质和图标显示测试；这些由用户自行测试。共享仓库的其他 ASH、天气、斧头、建造和 UI 修改不随本次发布。
