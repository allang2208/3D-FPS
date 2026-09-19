#pragma once
#include "CoreMinimal.h"

// 快速进战 · 单持手枪握把砸击（V5：关键帧表）
//
// 相机空间：X 前 / Y 右 / Z 上。旋转按「相机空间前乘」叠在入场旋转上：
//   Pitch>0 = 枪口上仰；Yaw>0 = 枪身向右摆；Roll>0 = 左侧抬起。
// 表内偏移全部相对「动作开始瞬间的入场姿态」；动作中相机转动、移动都不会累积误差。
// 力度来源改为 肘极向量 + 肩线偏航 + 高低差；腕只是 IK 目标，不再用腕部自转制造挥击。
namespace QuickCombatPistolMotion
{
    // 分段时钟：**按 clip 总长的比例**给出，运行时用实际动画长度换算（作者源改节奏不会与结算脱节）。
    // 段序：松握起手 → 上提蓄势（末段保持）→ 斜下砸接触 → 顿帧 → 跟随 → 回握。
    // 两把作者源 clip 节拍逐值相同（SourceAssets/DanWesson715QuickCombat20260918 与
    // SourceAssets/M1911QuickCombat20260919），当前都是 0.55s：
    //   0.06 / 0.18 / 0.21 / 0.26（接触）/ 0.29（顿帧结束）/ 0.40 / 0.55
    // 改任何一边的节拍必须同步另一边，并复核下面的比例常量。
    constexpr float ReleaseFraction = 0.06f / 0.55f;
    constexpr float HoldFraction    = 0.18f / 0.55f;
    constexpr float CockFraction    = 0.21f / 0.55f;
    constexpr float ContactFraction = 0.26f / 0.55f;
    constexpr float FollowFraction  = 0.40f / 0.55f;
    /** 无 clip 信息时的兜底总长（秒）。 */
    constexpr float DefaultLength = 0.55f;
    constexpr float QueryRadiusCM = 32.f;     // 命中球半径（距离仍用技能 rangeCM）

    /** 握把底相对手骨的相机空间偏移（约在拳心下方 5cm、后方 1cm）。 */
    inline FVector GripPointOffset() { return FVector(-1.f, 0.f, -5.f); }

    /** 动作镜头整体强度：对齐已获接受的符文剑配重锤（那边用 SwordCameraStrength=1.5）。 */
    constexpr float PistolBashCameraStrength = 1.4f;
    /** 阶段进入用的减速曲线。 */
    inline float EaseOut(float T) { T = FMath::Clamp(T, 0.f, 1.f); return 1.f - (1.f - T) * (1.f - T); }

    // ---- 命中冲量（配重锤 exp·sin 家族，方向改为下压）----
    // 量级对齐配重锤的**有效**幅度（配重锤基础值 ×1.5：位置 18/2.8 → 有效 27/4.2，
    // 旋转 10.5/1.6 → 有效 15.75/2.4）；手枪砸击是同类配重打击，取同级下压版本。
    // 用户 2026-09-18：镜头冲击抖动加强（幅度 ↑，衰减略慢、频率略高 ⇒ 更硬更长的抖动）。
    constexpr float ImpactSpan  = .30f;
    constexpr float ImpactDecay = 12.f;
    constexpr float ImpactFreq  = 52.f;
    inline float ImpactKick(float Age) { return FMath::Exp(-ImpactDecay * Age) * FMath::Sin(ImpactFreq * Age) * (1.f - FMath::SmoothStep(0.f, ImpactSpan, Age)); }
    inline FVector ImpactLocation() { return FVector(-32.f, 0.f, -4.8f); }   // 命中：镜头后坐 + 下沉
    inline FRotator ImpactRotation() { return FRotator(-16.f, 0.f, 3.0f); }  // 命中：下压 + 轻微侧倾
}
