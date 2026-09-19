#pragma once
#include "CoreMinimal.h"

// 快速进战 · 步枪枪托砸击（M4，作者源 clip 路线）
//
// 与手枪版（QuickCombatPistolMotion.h）同一技能家族：整段动作在作者源 clip 里
// （SourceAssets/RifleStockMelee20260918，D 版 0.90s、接触 0.435s），本文件只放
// 时钟比例、命中探针与镜头常数——改节奏只改作者源，代码按 clip 长度换算。
//
// 动作语言（参考 BV13K421e7Rw 1:05-1:07 AK47 枪托近战；H 版 2026-09-19 五次重做，
// **实机审计闭环标定**——QuickCombatAudit 夹具逐帧量枪托/枪口屏幕轨迹+世界变换后落参）：
//   蓄势：整枪滚转压平 + **大偏航把枪口甩出画面左侧**（表 yaw+60 → 游戏内 −169°）+ 拉近；
//   打击：整枪**压平大回旋横扫过画面**——枪口自画左横穿到右侧（u −0.3→0.76）、
//   枪托自右下入画**扫过画面中心偏左**（u 0.83→0.41→0.38，v≈0.72-0.78）、整枪前伸
//   （枪口距离 47→96cm）；接触 0.435s。双手全程持枪（握把不变量逐帧恒定）。
//   教训链：Blender 预览相机 ≠ 游戏相机（视模偏移+运行时镜头层）——离线 tune_motion 的
//   屏幕预测全部失真，必须以实机审计为准；A~G 七版里 D/E/F/G 都败在"离线模型自洽、
//   实机读感相反"。实机审计跑法见 SourceAssets/RifleStockMelee20260918/README.md。
//   A(枪口下劈)/B(抬枪托)/C(小滚转横扫)/D(右腕小回旋)/E(左手小偏航前顶)/F(俯仰正向前捅)
//   /G(枪尾抬但回旋不足) 七版作废，保留为作者源对照候选（--variant A..H）。

namespace QuickCombatRifleMotion
{
    // 分段时钟：按 clip 总长的比例给出，与作者源时间轴同比例
    // （B 版 0.72s：0.058 / 0.244 / 0.348 接触 / 0.511 / 0.72；下面的比值与它一致）。
    constexpr float ReleaseFraction = 0.05f / 0.62f;
    constexpr float CockFraction    = 0.21f / 0.62f;
    constexpr float ContactFraction = 0.30f / 0.62f;
    constexpr float FollowFraction  = 0.44f / 0.62f;
    /** 无 clip 信息时的兜底总长（秒）。 */
    constexpr float DefaultLength = 0.62f;

    /** 命中球半径（距离仍用技能 rangeCM）。 */
    constexpr float QueryRadiusCM = 34.f;

    /** 命中点相对枪口沿枪轴回撤的距离（cm）：打在枪身前段而不是枪口尖端。 */
    constexpr float MuzzleBackOffCM = 12.f;

    /** 动作镜头整体强度：步枪动作幅度大于手枪，取同族略强值。 */
    constexpr float RifleStockCameraStrength = 1.6f;
    /** 镜头动作语言相对手枪表的放大系数。 */
    constexpr float RifleCameraShapeScale = 1.15f;

    /** 命中冲量：与手枪同一 exp·sin 家族，幅度取同级略强（步枪是更重的配重打击）。 */
    inline FVector ImpactLocation() { return FVector(-36.f, 0.f, -5.4f); }
    inline FRotator ImpactRotation() { return FRotator(-18.f, 0.f, 3.4f); }
}
