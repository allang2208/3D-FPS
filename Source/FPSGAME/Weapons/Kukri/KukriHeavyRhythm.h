#pragma once

#include "CoreMinimal.h"

/**
 * 尼泊尔弯刀重击（技能 heavyStrike，2026-10-24，KukriHeavy.cpp）：参考 BV1CeYUeSE7b 115.60-117.00 s「近战动作（跳跃）#12 ↙」。
 * 作者源：SourceAssets/Kukri20261020/fit_heavy.py → heavy_keys.json → author_kukri_heavy.py（clip HeavyCharge / HeavyRelease）。
 * 与双手剑同一规则：左键按住蓄力（技能等级 ≥1），≤0.2 s 松开 = 普通连击，蓄满（物品／技能的 HeavyChargeSeconds）后松开 = 重击，
 * 未蓄满松开 = 普通连击；快捷栏 heavyStrike 蓄满自动出手。蓄力期间按技能 heavyChargeStaminaPerSecond 持续耗体力，出手再付一次攻击体力。
 *  V2（2026-10-24 用户：蓄力时刀身朝玩家后方、刀把朝前，然后右上→左下回砍；出手更快、更有冲击力）：
 *  蓄力 HeavyCharge（2.0 s 作者）：0-0.17 抬刀——拳向右外侧抬到右上角、刀身指向左上（参考原速）；0.20 刀身竖起，0.20-0.40 手腕
 *   像抡锤一样后扳，刀身从头顶翻到右肩后方、刀把朝前（= 参考 0.367 那一帧：前臂竖在右缘、刀在画外）；左手张开从左下伸到画面中心
 *   再向左下甩出（参考 0.07-0.33 s）；0.40-2.00 蓄力——拳再往肩头收、刀身沉到背后，这一段拉伸到实际蓄力秒数，蓄满后细颤。
 *  出手 HeavyRelease（35/30 s 作者，第 4 段表）：从肩后直接回砍——0.033 刀从头后翻过顶（刃口朝前）→ 0.075 刀尖劈过准星（打击时刻，
 *   刃口领先）→ 0.10 拳到画面下方正中 → 0.133 从左下出画 → 画外 → 0.83-1.07 由右下抬回、翻刀入架势，期间左拳露在左下角。
 *  V1 蓄力时刀身指向左上留在画面里，出手先向右上提刀出画再劈。
 */
namespace KukriHeavyRhythm
{
    inline const FName ChargeClip(TEXT("HeavyCharge")), ReleaseClip(TEXT("HeavyRelease"));
    inline constexpr float ChargeLength=2.f;       // author s of HeavyCharge
    inline constexpr float RaiseEnd=.40f;          // the raise plays on the martial clock; the load fills the rest of the charge
    inline constexpr float TapSeconds=.20f;        // a release this soon is an ordinary click (the sword's rule)
    inline constexpr float CancelBlendSeconds=.22f;// a cancelled charge blends back to locomotion
    inline constexpr float ReleaseEntryBlend=.05f; // HeavyRelease starts on the loaded pose: only a guard blend
    // Full charge: a fine tension tremble on the viewmodel parent (deg, Hz) until the release.
    inline constexpr float TrembleDegrees=.22f, TrembleHz=13.f;
    // Server receipt (UKukriWeaponComponent::ServerSetKukriHeavyCharge): reports of this release are accepted this long.
    inline constexpr double ReleaseWindowSeconds=.9;

    /** Charge clip pose time: the raise at the martial clock, then the load stretched over the rest of the charge. */
    inline float ChargePoseTime(float Held,float Required,float Rate)
    {
        const float Raise=Held*Rate;
        if(Raise<RaiseEnd)return Raise;
        const float RaiseSeconds=RaiseEnd/FMath::Max(.05f,Rate);
        return RaiseEnd+(ChargeLength-RaiseEnd)*FMath::Clamp((Held-RaiseSeconds)/FMath::Max(.2f,Required-RaiseSeconds),0.f,1.f);
    }

    /**
     * 蓄力镜头：参考 #12 远景配准（Reference/camera_heavy.py → curve_heavy.py）。抬刀时逆时针滚约 4.8°、略右转，到右上角后
     * 抬头约 1.4°、视场收窄；蓄力段继续慢慢抬头、滚转、收窄视场（专注），蓄满时到 Loaded*，出手曲线 KukriRhythm::Heavy* 从这里接上。
     * 参考抬刀瞬间滚到 -6.3°，这里按住最长可达数秒，幅度收小。
     */
    inline constexpr int32 ChargeSamples=13;       // 0-0.40 s at 30 Hz
    inline constexpr float ChargeYaw[ChargeSamples]={0.00f,0.16f,0.28f,0.35f,0.37f,0.34f,0.26f,0.22f,0.22f,0.22f,0.22f,0.22f,0.22f};
    inline constexpr float ChargePitch[ChargeSamples]={0.00f,-0.03f,-0.09f,-0.18f,-0.39f,-0.55f,-0.07f,0.55f,0.82f,1.04f,1.22f,1.34f,1.38f};
    inline constexpr float ChargeRoll[ChargeSamples]={0.00f,-0.22f,-0.79f,-2.60f,-4.21f,-4.80f,-4.44f,-4.00f,-3.83f,-3.70f,-3.59f,-3.52f,-3.50f};
    inline constexpr float ChargeFov[ChargeSamples]={0.00f,-0.07f,-0.13f,-0.19f,-0.25f,-0.30f,-0.35f,-0.40f,-0.44f,-0.49f,-0.53f,-0.57f,-0.60f};
    inline constexpr float LoadedYaw=0.22f, LoadedPitch=2.30f, LoadedRoll=-4.50f, LoadedFov=-1.50f;

    inline float SampleCharge(const float (&Curve)[ChargeSamples],float T)
    {
        const float X=FMath::Clamp(T*30.f,0.f,float(ChargeSamples-1));
        const int32 I=FMath::Min(int32(X),ChargeSamples-2);
        return FMath::Lerp(Curve[I],Curve[I+1],X-I);
    }

    /** Camera of the charge clip at author time T (degrees: pitch/yaw/roll + vertical FOV delta). */
    inline void ChargeCamera(float T,FRotator& Rotation,float& Fov)
    {
        const float Load=FMath::SmoothStep(RaiseEnd,ChargeLength,T);
        Rotation=FRotator(FMath::Lerp(SampleCharge(ChargePitch,T),LoadedPitch,Load),FMath::Lerp(SampleCharge(ChargeYaw,T),LoadedYaw,Load),
            FMath::Lerp(SampleCharge(ChargeRoll,T),LoadedRoll,Load));
        Fov=FMath::Lerp(SampleCharge(ChargeFov,T),LoadedFov,Load);
    }

    /**
     * 双持弯刀重击（2026-10-27，用户：参考视频 1:19-1:20 的 X 姿势同时挥砍，做双持重击出手，力求 100% 还原；蓄力阶段的手和
     * 手臂也要自然衔接）。参考 BV19dUqBJECT 近战动作 #3「X」，文件 78.20-79.30 s。作者源 SourceAssets/DualKukriIdle20261025/
     * fit_dual_heavy.py → heavy_keys.json → author_dual_heavy.py（clip DualHeavyCharge 2.0 s / DualHeavyRelease 1.0 s）。
     * 蓄力与单持同一套时长（RaiseEnd、ChargeLength、ChargePoseTime）：0-0.10 X 握姿向两侧打开、两刀各自朝外竖起；0.10-0.20
     *  两拳沿两侧抬起；0.20-0.40 两只手腕像抡锤一样后扳，刀身放到两肩后、刀把朝前，两拳在画面上缘两侧、前臂沿两边竖着；
     *  0.40-2.00 两拳再往后上收一点（蓄力，拉伸到实际蓄力秒数）。左手是右手的镜像，手腕都在认可握姿附近。
     * 蓄力镜头：参考 0-0.30 s 远景配准（Reference/camera_heavy_x.py → curve_heavy_x.py）：X 打开时略抬头、视场放宽，
     *  双臂上举时低头约 3°、视场收窄约 3°、略左转右滚；蓄满时到 DualLoaded*，出手曲线 KukriRhythm::DualHeavy* 从这里接上。
     */
    inline const FName DualChargeClip(TEXT("DualHeavyCharge")), DualReleaseClip(TEXT("DualHeavyRelease"));
    inline constexpr float DualChargeYaw[ChargeSamples]={-0.00f,-0.15f,-0.07f,0.01f,-0.13f,-0.29f,-0.51f,-0.75f,-1.00f,-1.06f,-1.17f,-1.13f,-0.78f};
    inline constexpr float DualChargePitch[ChargeSamples]={0.00f,0.30f,0.72f,1.05f,1.08f,0.47f,-0.37f,-1.27f,-2.10f,-2.49f,-2.73f,-2.93f,-3.16f};
    inline constexpr float DualChargeRoll[ChargeSamples]={0.00f,0.01f,-0.22f,-0.37f,-0.07f,0.15f,0.34f,0.55f,0.85f,0.71f,0.82f,0.92f,0.76f};
    inline constexpr float DualChargeFov[ChargeSamples]={0.00f,0.06f,0.92f,1.88f,2.27f,1.76f,0.75f,-0.49f,-1.73f,-2.52f,-3.27f,-3.52f,-2.86f};
    inline constexpr float DualLoadedYaw=-0.97f, DualLoadedPitch=-3.47f, DualLoadedRoll=0.91f, DualLoadedFov=-3.57f;
    inline void DualChargeCamera(float T,FRotator& Rotation,float& Fov)
    {
        const float Load=FMath::SmoothStep(RaiseEnd,ChargeLength,T);
        Rotation=FRotator(FMath::Lerp(SampleCharge(DualChargePitch,T),DualLoadedPitch,Load),
            FMath::Lerp(SampleCharge(DualChargeYaw,T),DualLoadedYaw,Load),FMath::Lerp(SampleCharge(DualChargeRoll,T),DualLoadedRoll,Load));
        Fov=FMath::Lerp(SampleCharge(DualChargeFov,T),DualLoadedFov,Load);
    }
}
