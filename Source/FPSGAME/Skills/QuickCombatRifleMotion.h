#pragma once
#include "CoreMinimal.h"

// 快速进战 · 步枪近战：动作烘焙在作者源 clip，本文件提供事件时钟与命中参数。
// M4 N 与 RifleQuickMelee20260919（AKM/QBZ191/ASH12）：0.90 s，接触 0.1667 s。
// BV13K421e7Rw 1:05–1:07：枪托从右向画面中部送出，枪口保持左下，随后收枪。
// 各枪按自己的待机抓握适配腕臂与枪托点，旧 H 的反向挥击不再作为来源。

namespace QuickCombatRifleMotion
{
    // BV13K421e7Rw native frames 1988..2015: rapid entry/contact, then
    // loaded follow-through and recovery. All current rifles use this clock.
    constexpr float M4ReferenceReleaseFraction = 1.f / 27.f;
    constexpr float M4ReferenceCockFraction = 3.f / 27.f;
    constexpr float M4ReferenceContactFraction = 5.f / 27.f;
    constexpr float M4ReferenceFollowFraction = 8.f / 27.f;
    // Author stock point (0,+0.235,+0.025)m. FBX bone-space Y reverses in UE;
    // use no-scale centimetres so the imported bone scale is not applied twice.
    inline FVector M4ReferenceStockPointCM() { return FVector(0.f,-23.5f,2.5f); }

    // Authoring surface anchors from RifleQuickMelee20260919/authoring.json.
    // Bone-space Y reverses on FBX import; these are no-scale centimetres.
    inline FVector ReferenceStockPointCM(const FString& MeshPath)
    {
        if (MeshPath.Contains(TEXT("/ASH12/"))) return FVector(0.343015f, -45.591554f, -4.261902f);
        if (MeshPath.Contains(TEXT("/QBZ191/"))) return FVector(0.072809f, -20.850360f, 5.925570f);
        if (MeshPath.Contains(TEXT("AKM"))) return FVector(0.107212f, -28.872550f, 1.638935f);
        return M4ReferenceStockPointCM();
    }

    // 保留旧 clip 的分段时钟供旧调用使用；当前四把步枪均走上方参考时钟。
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
