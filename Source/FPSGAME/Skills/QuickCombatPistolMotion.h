#pragma once
#include "CoreMinimal.h"

// 手枪「快速进战」握把猛砸的分段时钟与相机空间目标。
// V2：参考 COD4 UZI 枪托近战（B 站 BV13K421e7Rw 45-47s）的动作语言——
// 右肩方向快速上提枪口朝上 → 斜下前方的短促前捅（握把端领先）→ 左手同步开掌前推 →
// 立即回握。全程收紧到约 0.85s（V1 的水平缓推被否）。相机空间：X 前 / Y 右 / Z 上。
namespace QuickCombatPistolMotion
{
    constexpr float ReleaseEnd=.12f;   // 左手张开、同步开始上提
    constexpr float CockEnd=.32f;      // 提到右肩高度，枪口上仰
    constexpr float ContactTime=.42f;  // 握把接触（技能结算点）
    constexpr float SmashEnd=.48f;     // 前捅到位
    constexpr float AttackEnd=.85f;    // 收势完成，左手回握闭指

    constexpr float QueryRadiusCM=32.f; // 命中球半径（判定距离用技能 rangeCM）
    constexpr float CockTiltDeg=55.f;   // 上提到肩：枪口上仰，握把底朝下前
    constexpr float ContactTiltDeg=20.f;// 接触时回正一部分，握把底部领先
    constexpr float GuardTiltDeg=25.f;  // 左手推掌的翻掌量

    inline float Ease(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
    /** 前捅的加速曲线：起手慢、接触前最快（COD4 式短促斜捅）。 */
    inline float Strike(float T){T=FMath::Clamp(T,0.f,1.f);return T*T;}

    /** 右腕相对其入场点的偏移：上提段终点（向后、向右、抬高到肩）。 */
    inline FVector CockWristOffset(){return FVector(-12,4,9);}
    /** 右腕前捅段终点：从高处斜向下前方猛送（高低差是这一记的力度来源）。 */
    inline FVector SmashWristOffset(){return FVector(18,2,-14);}
    /** 左手相对其入场点的推掌位：与砸击同步向左前方开掌推挡（非下垂守位）。 */
    inline FVector LeftGuardOffset(){return FVector(6,-22,-2);}
}
