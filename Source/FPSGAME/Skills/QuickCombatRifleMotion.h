#pragma once
#include "CoreMinimal.h"

// 快速进战 · 步枪枪托砸击（M4，作者源 clip 路线）
//
// 与手枪版（QuickCombatPistolMotion.h）同一技能家族：整段动作在作者源 clip 里
// （SourceAssets/RifleStockMelee20260918，0.62s、接触 0.30s），本文件只放
// 时钟比例、命中探针与镜头常数——改节奏只改作者源，代码按 clip 长度换算。
//
// 动作语言（参考 BV13K421e7Rw 1:05-1:07 AK47 枪托近战，30 fps 原生帧复核）：
//   整枪前推并抬**枪托**（枪口下沉往左下出画）→ 顶点保持 → 枪托自右上向左侧扫过画面中心
//   （接触 0.348s，含 3 帧顿帧）→ 跟随 → 回位。双手全程持枪（右手握把、左手护木）。
// 早期 A 版（抬枪口再往下扫）与参考相反，已作废，只在作者源里保留为对照候选。
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
