# 蓝紫金纹魔法书素材

> **2026-10-10 已暂停。** 当前为 V17 恢复原阅读方向、原开掌的已编译现场，视觉未确认、recover 待重做。历史版本不作为当前认可模板。后续任务及归档见[暂停记录](../../Docs/Weapons/spellbook-paused-20261010.md)。

使用 evildeer 的 [Magic book set](https://sketchfab.com/3d-models/magic-book-set-ee1747b4d426446ba5f14bcf2aec8400) 中 `book2`：蓝紫色、金色卷纹的 **Elemental Alchemy**。本目录为 2026-10-09 的独立素材制作目录。

## 文件

- `original-source.zip`：原始下载，保留未修改版本；API 来源、下载时间及 SHA-256 记录在 `source-metadata.json`。
- `Original/`：下载包里的 FBX、原始 PBR 图集，以及 Blender 从 FBX 提取的嵌入贴图。
- `source-import.blend`：原始整套 FBX 的本地 Blender 转换版本。下载包本身没有 `.blend`。
- `Spellbook_Alchemy.blend`：选定书本的可编辑适配源，纹理已打包，默认显示展开姿态。
- `Export/`：闭合静态模型、展开静态模型、骨骼模型、7 段 FBX 动画及未降分辨率的原始纹理副本。`manifest.json` 保存材质映射、尺寸和坐标约定。
- `author_spellbook.py`：本地 Blender 制作与导出入口。
- `InventoryIcon/render_icon.py`：从闭合模型与原生产 PBR 生成共用装备图标；读取物品目录的取景角度及占格。可编辑场景、作者 PNG 和制作记录一起保存在 `InventoryIcon/`。
- `import_spellbook_ue.py`：UE 后台导入、材质编译与资产保存入口。
- `ue-import-receipt.json`：实际保存资产的逐项回执；只有 `complete: true` 表示整批导入完成。
- `ATTRIBUTION.md`：作者、CC BY 4.0、来源及改动说明，后续发行时应保留相应署名。

## 制作内容

保留原闭合书的封皮几何、外部 UV、皮革颜色、金纹与磨损。将书体沿中间书页平面分成前后两半，加入使用原包插图的内页表面；增加三张具有正反面与厚度的可翻页，每张使用 8 节骨骼弯曲。全部以厘米制作，根位于书脊与中间书页平面的交点。

源模型坐标：+X 从书脊指向书页外缘，+Y 从书底指向书顶，+Z 指向闭合时的正面。FBX 按项目标准使用 -Y forward / Z up 导出，UE 导入单位倍率为 1。

材质使用原包的 Base Color、Roughness、Metallic 和 Normal；封皮为 4K 图集，内页为 2K 图集。封皮法线沿 Blender/OpenGL 约定，内页文件明确为 DirectX，UE 分别设置绿通道翻转。

## 动画合同

| 动作 | 时长 | 用途 |
| --- | --- | --- |
| IdleClosed | 1 秒 | 闭合保持 |
| Open | 1.2 秒 | 展开到 165 度 |
| IdleOpen | 1 秒 | 展开，三张活动页位于右侧 |
| FlipPages | 4 秒 | 三页依次从右向左翻动 |
| IdleOpenTurned | 1 秒 | 翻完后三页位于左侧 |
| FlipBack | 4 秒 | 三页依次翻回右侧 |
| Close | 1.2 秒 | 从 IdleOpen 收拢 |

顺序：`IdleClosed → Open → IdleOpen → FlipPages → IdleOpenTurned → FlipBack → IdleOpen → Close`。`Close` 的起点是未翻页状态；玩法控制器接入时应先翻回或补充相应过渡，不应将任意帧强切到 Close。当前活动页为三张有限插画页，不是任意页数的书籍系统。

## UE 交付边界

已后台导入并保存到 `/Game/Weapons/SpellbookEvildeer20261009/`，分为 Meshes、Materials、Textures、Animations。共 21 项资产：2 个静态模型、1 个骨骼模型、1 个骨架、7 段动画、2 个材质、8 张纹理。导入回执为 `ue-import-receipt.json`。

最终后台导入日志 `ue-import-final.log` 返回 0 错误；本次书页 UV 层合并与切线警告已在源文件修正。日志仍包含工程 ModelingService 的 5 条既有 Python 同名暴露警告。这里记录的是导入与保存结果，不是视觉或游戏验收。

2026-10-09 已补充游戏内副手接入，最初按用户选择接入闭合握持和移动，随后新增 F 键持书前击。物品名为“元素炼金魔法书”，定义 `ue_alchemy_spellbook`，沿现有一次性军械发放机制加入仓库，可装备到副手槽 8 / 11，随主副手组切换，沿现有物品实例与装备存档流程保存。

`Source/FPSGAME/Weapons/Spellbook/SpellbookComponent.*` 使用 V7 原生左臂。当前作者版本为 Photo V3：按用户后续修正，书脊朝向视线，封面向侧后方转开，书顶向右上倾斜。保持 V2 的拇指压封皮、四指绕书脊夹持关系，将手与书联动转侧并适配整条肩肘腕支撑。`GripPhotoV3/author_grip.py` 读取 `GripPhotoV2/grip.json` 的固定挂点和局部指骨旋转，输出 65 组姿态到 `grip.json` 和 `SpellbookAuthoredGrip.h` Revision 3，保留原生绑定、蒙皮和骨长。`GripPhotoV3/Spellbook_PhotoGripV3.blend` 包含同源可编辑左臂、书本和 Idle / Walk / Run 动作。初版源保留在 `Grip/`，V2 仍是有效的接触制作输入。

移动基础表使用空手同源的 `LeftGaitV16` 腕部轨迹，整条左臂围绕照片掌向适配支撑。按后续“低位、小幅晃动”要求，`SpellbookCarryTuning.h` 将走路／奔跑姿态混合权重分别缩至 0.35／0.25，并将完整左臂下移 5 cm；保持 `FStaffLocomotion` 的脚步相位及停启、走跑过渡。书每帧直接跟随同一次姿态更新后的 `hand_l`，不会单独叠加相位不同的摆动。基础姿态编入 C++，无需新增 UE 动画资产。

已连接手套衣袖跟随、主手左臂显示归属、主手换弹／检视让手、消耗品放下／使用／抬回、世界握持模型、拾取模型、现有模型图标与打包资源目录。持书时左手施法按占手处理，F 使用持书前击；主手法杖施法仍沿原通道。持书前击沿用快速近战伤害与体力，没有新增魔法效果或翻页按键，独立翻页资产保留供后续使用。CC BY 署名另存于 `Content/ColdSteelData/Licenses/SpellbookEvildeer20261009.txt`。

握持制作没有启动编辑器、运行游戏、截图、预览渲染或进行自动测试／验收；实际握持观感、动作与装备流程由用户测试。后台构建记录见 `Docs/Weapons/spellbook-offhand-20261009.md`。

## 装备图标

按用户后续要求，已另行生成正式透明 PNG：`Content/ColdSteelData/Icons/ue_alchemy_spellbook.png`。图像使用实际闭合书本与蓝紫金纹材质，竖直正交展示、稍露书脊；当前占格更新为 2 × 2，图标重新渲染为 320 × 320 RGBA，实际轮廓等比例居中、主轴约占 91%。不附加边框、背景或手部。

`InventoryIcon/ue_alchemy_spellbook.png` 与正式 PNG 同源同步；`Spellbook_InventoryIcon.blend` 是独立的图标编辑场景。出图入口从 `items.json` 读取 `ue_icon_pitch/yaw/roll = 0/75/90`，实时装备模型图标也读取相同角度，沿既有异步捕获及 PNG 回退通道供背包、装备栏、仓库共用。旧存档加载时仅同步此书的图标路径、图标模型和取景角度，不改实例位置、数量或属性。

图标任务仅进行用户要求的成图、接入与必要后台构建，没有启动 UE 或执行游戏测试。

Photo V3 侧握修改时，用户明确要求图标保持现状；本次没有修改图标 PNG、取景参数或出图入口。V3 姿态源码和编辑 Blend 已保存，常规编译状态见 `Docs/Weapons/spellbook-offhand-20261009.md`；没有执行动作渲染或游戏测试。

后续按用户“改为 2 × 2 格并调整贴图”的要求，图标保持原取景角度，仅按新占格重新构图出图；正式 PNG、作者 PNG 与独立编辑 Blend 已同步。`InventoryIcon/production.json` 记录新占格与分辨率，`render-2x2.log` 为生成记录。旧物品沿正常存档加载流程更新占格及旧旋转标记，游戏握姿和模型材质不受影响。

后续低位持书调整已同步至 `GripPhotoV3/save_editable.py` 和编辑 Blend。保存入口直接读取 `SpellbookCarryTuning.h`，按运行权重混合基础姿态并下移完整左臂；`grip.json` 与 `SpellbookAuthoredGrip.h` 保留未减幅的基础轨迹。基础动作重制后执行保存入口仍会沿用当前低位参数。当前编辑器热编译成功，基础 DLL 的常规构建待编辑器关闭后进行；没有运行游戏或制作验收渲染。

## F 持书前击作者源

`QuickMelee/author_strike.py` 以当前 Photo V3 夹持为固定输入，制作保持指姿和书本挂点的肩肘前伸，输出 `strike.json` 与运行姿态表 `SpellbookAuthoredStrike.h`。57 个密集姿态使用同一 0.43 秒动作时钟，0.14 秒接触；游戏从实时低位步态接入并收回该层。

`QuickMelee/save_editable.py` 已保存 `Spellbook_QuickMelee.blend`，含可编辑 V7 左臂、原书和前击动作，保存日志为 `save-editable.log`。F 接入共享快速近战数值与命中结算，书页外沿作为实际接触点，指姿与书本侧角保留。2 × 2 占格和图标沿用前次版本；未运行游戏或渲染，构建状态见制作文档。

持书前击制作后，常规基础 DLL 构建已于 `Saved/BuildEditor/build-20261009-224717.log` 返回 `Result: Succeeded`，同时包含此前低位摆动改动。无需为本动作新增导入 UE 动画资产；没有打开编辑器或进行游戏测试。

## 法杖专注与空主手右拳

当前新增：空主手＋本书的左键固定右拳；法杖＋本书的右键切换专注，再按一次合书。其他主手的右键继续使用原功能。

`Focus/author_focus.py` 将共享施法积蓄手型适配为当前 V7 的 40 帧原生姿态，保留未离手阶段的书脊抓握。`Focus/Spellbook_Focus.blend` 已实际保存完整积蓄、浮起、快速打开、慢速往返翻页及合书回握作者场景；`Focus/save-editable.log` 和 `editable-source.json` 记录保存边界。运行复用原 `Open`、`FlipPages` 资产，16 秒一轮前后翻页，关闭先回到未翻页端点再合书。

翻页是三张八段骨骼页的预制弯曲，没有页碰撞、布料模拟或额外动画 Tick。只在专注显示时求值；闭合时继续静态书模型，本地世界浮书使用同一骨骼缓存。未新增专注增益或魔法消耗，也未新增跨客户端专注状态复制。尚未运行游戏或渲染；编译状态见项目制作文档。

用户关闭 UE 后，空主手右拳与法杖专注的常规基础 DLL 已完成编译和链接，日志 `Saved/BuildEditor/build-20261009-231118.log` 返回 `Result: Succeeded`。没有重新启动编辑器或游戏，实际输入、翻页及收书效果由用户测试。

后续阅读方向修正：专注悬浮的两个书面轴同时转动 180 度，保留原页面 PBR 和闭合侧握。`Focus/author_return.py` 新增独立的连续抬手、接书脊、依次扣指及下落收势，输出 `return.json` 与 `SpellbookAuthoredReturn.h`。`Focus/save_editable.py` 已同步方向、弧线回书和新手臂轨道，实际保存 `Spellbook_Focus.blend`；生产日志 `Focus/save-natural-return.log`。

翻页金光作者源为 `Focus/GoldOrbit/gold_orbit.hlsl`／`install_material.py`，运行几何由 `SpellbookFocusGold.cpp` 创建一次。两道流光、16 个光点共 416 个三角面，材质 UV 流动，开合淡入淡出，不使用粒子物理或动态灯。专用材质路径 `/Game/Weapons/SpellbookEvildeer20261009/Effects/M_Spellbook_GoldOrbit`，实际安装回执保存在 `Focus/GoldOrbit/install_receipt.json`。构建与实际资产落盘状态见项目制作文档；未运行游戏或验收渲染。

方向／接书／金光本轮制作已完成后台材质保存及着色器编译，最终 commandlet 日志 0 错误；常规基础 DLL 构建 `Saved/BuildEditor/build-20261009-233626.log` 返回 `Target is up to date`、`Result: Succeeded`。可编辑 Blend、作者姿态与 UE 材质均已落盘，没有运行游戏测试。

用户再次否定上一版回收观感后，当前 `Focus/author_return.py` 改为 **先原位合书 → 下落到左手 → 接触缓冲和扣指 → 回到待机**。合书／下落／握紧／归位分别为 0.28／0.22／0.16／0.42 秒，从统一 `SpellbookFocusMotion.h` 读取；`return.json` Revision 3 为 73 个归一化姿态，运行命名空间 `SpellbookAuthoredDropReturn`。合书不再先退页，直接从当前页姿态混合到闭合参考姿态；下落加速，书脊接触后固定随手，手指仅在接触后闭合。

`Focus/Spellbook_Focus.blend` 同步新的分段动作，制作日志 `Focus/save-close-drop.log`；未渲染或运行游戏。此前“弧线返书”及 61 帧作者表已由这一版原位合书、下落方案替代，未作为认可基线。热编译／基础构建状态见项目制作文档末节。

先合书再下落这一版已完成基础 Editor DLL 的常规后台构建：`Saved/BuildEditor/build-20261010-000548.log` 为 `Target is up to date`、`Result: Succeeded`；不依赖未成功接入的热编译请求。可编辑源已实际保存，未启动编辑器或运行游戏测试。
