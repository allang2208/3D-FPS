# SVCH 换弹抓握 R9（2026-10-18）

后续：用户要求的实际换弹复查及 R10 修复已完成，当前结果见 [R10 复查记录](svch-reload-review-r10-20261018.md)。以下保留 R9 制作时的状态。

本轮针对普通、空仓换弹时左手与弹匣未贴合的问题，沿用认可的 SVD 换弹、原生 V9 裸手和 R8 枪体。制作及落盘结果见 `SourceAssets/SVCHRefinement20261018/R9ReloadGrip/delivery_receipt.json`；本轮未运行游戏、截图或视觉验收。

## 原因与制作方式

原 R7 配置对持枪支撑手做了配准，但左手离开护木后的弹匣抓握仍主要使用 SVD 原关系。源弹匣的测量长轴约 12.31 cm，SVCH 当前弹匣约 19.49 cm；抓握处宽度也不同，直接复用腕的位置不能保持前半段接触。

参考手臂 SKILL 的 [弹匣抓握配准](../../skills/ue5-fps-arms-animation/references/magazine-grip-registration.md)、[不规则弹匣](../../skills/ue5-fps-arms-animation/references/irregular-magazine-grip.md) 和 [共享动画](../../skills/ue5-fps-arms-animation/references/weapon-animation-sharing.md) 经验，使用当前 V9 蒙皮及实际弹匣几何，在弹匣局部坐标中转移认可的前半段抓握和向上拇指关系。

制作时比较距底盖、距供弹口和相对高度三种基准，普通/空仓共用同一组接触约束和机匣避让约束，采用距底盖约 9.56 cm 的基准。整只左手进行刚体配准，肩肘随动，新增前臂轴向转角由 V9 辅助骨分担。手指局部动作、骨段长度、蒙皮权重和原生模型不改。

以 120 fps 源时钟表示：18–49 帧渐入，49–244 帧保持弹匣关系，244–302 帧返回原支撑轨迹。普通与空仓换弹使用同一抓握，保留原本张手/收指、拔匣、插匣、落座和拉栓动作时序。优化器的接触距离只用于生产拟合，不构成实际画面通过的证明。

## 接入范围

| 项目 | 本轮处理 |
| --- | --- |
| 普通、空仓换弹 | 更新 8 条左肩臂/腕及辅助骨轨道 |
| 右臂、手指、机械轨道 | 保留原配置及源动画 |
| 其余 10 个动作 | 保留当前 R7 配置 |
| V9 裸手和 R8 枪体 | 不改 UE 模型、骨架、蒙皮和材质 |
| 前握把分支 | 换弹通道单独选择 SVCH 基础配置；不受缺失的配件配置影响 |
| 待机、ADS、冲刺 | 继续使用原有配件配置选择 |
| 弹药、声音、换弹速度、弹道 | 不修改 |

运行时增加可选 `ActionGripProfile`，只对 SVCH 的两条原生换弹 clip 赋值。该动作通道不再叠加另一套通用握把修正，待机/ADS 等通道仍保留原配置。接触求解全部离线完成，运行时读取已有配置轨道，不增加 IK、文件读取或同步资产加载。

UE 保存目标仍为 `/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip`，历史目录名不代表内容回退。源动画仍为 `/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_reload` 和 `A_SVD_reload_empty`，时长分别为 3.333333 s、4.291667 s。

## 制作文件与状态

所有本轮文件位于 `SourceAssets/SVCHRefinement20261018/R9ReloadGrip/`：

- `Inputs/`：当前几何、蒙皮、压缩动作及修改前配置的生产输入。
- `author_reload_grip.py`、`profile_reload_grip.json`：可重建的接触配准及配置数据。
- `SVCH_R9_ReloadGrip_Editable.blend`：普通/空仓动作及当前 V9 源皮肤；武器和 V9 分别有对应 action，切换两者同名后缀即可编辑。源文件皮肤使用中性显示材质，游戏材质保持原资产。
- `Before/DA_SVCH_BaseGrip.uasset`：接入前的单资产备份。
- `install_receipt.json`、`build-editor.log`、`delivery_receipt.json`：实际保存及后台构建记录。

本轮完成标准是源文件、配置资产和必要构建落盘；普通/空仓及各配件下的实机接触、前臂外观和过渡仍由用户体验确认，未标记为已验收。
