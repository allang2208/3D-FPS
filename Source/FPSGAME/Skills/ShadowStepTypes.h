#pragma once
#include "CoreMinimal.h"

struct FShadowStepTuning
{
    float Stage1DamageBase=1.15f, Stage1DamageMax=2.10f;
    float Stage2DamageBase=.85f, Stage2DamageMax=1.65f;
    float DualPerHandRatio=.60f;
    float FollowupBackstabCritBonus=25.f;
    float FollowupWindowSeconds=.45f;
    float DashDistanceBaseCM=600.f, DashDistanceMaxCM=750.f;
    float CooldownBase=18.f, CooldownMin=12.f;
    float StaminaBase=35.f, StaminaMax=50.f;
    float ToughnessStage1=220.f, ToughnessStage2=260.f;
    int32 MultiKillExperience=20;
};

struct FShadowStepCast
{
    float Stage1DamageMultiplier=1.15f;
    float Stage2DamageMultiplier=.85f;
    float DualPerHandRatio=.60f;
    float FollowupBackstabCritBonus=25.f;
    float FollowupWindowSeconds=.45f;
    float DashDistanceCM=600.f;
    float CooldownSeconds=18.f;
    float StaminaCost=35.f;
    float ToughnessStage1=220.f;
    float ToughnessStage2=260.f;
};

namespace ShadowStep
{
    inline const FName SkillId(TEXT("shadowStepSlash"));
    // Distinct from 0x10 (heavy), 0x14 (uppercut), 0x15 (cloven), 0x16 (dash).
    // Note bit 0x10 is set; heavy-only branches explicitly exclude ShadowStep::IsMeta.
    inline constexpr uint8 AttackMetaStage1=0x18;
    inline constexpr uint8 AttackMetaStage2=0x19;
    inline bool IsStage1(uint8 Meta){return Meta==AttackMetaStage1;}
    inline bool IsStage2(uint8 Meta){return Meta==AttackMetaStage2;}
    inline bool IsMeta(uint8 Meta){return Meta==AttackMetaStage1||Meta==AttackMetaStage2;}

    // Authored Stage 1 timeline (seconds, 120 fps = 114 frames = 0.95 s).
    inline constexpr float Stage1Duration=.95f;
    inline constexpr float Stage1DashStart=.15f;
    inline constexpr float Stage1DashEnd=.33f;
    inline constexpr float Stage1HitStart=.29f;
    inline constexpr float Stage1HitEnd=.42f;
    inline constexpr float Stage1DualSecondHitStart=.33f;
    inline constexpr float Stage1DualSecondHitEnd=.44f;
    inline constexpr float Stage1FollowupOpen=.38f;
    inline constexpr float Stage1CancelStart=.55f;
    inline constexpr float Stage1DashFOVBoost=9.f;

    // Authored Stage 2 reverse backhand follow-up timeline (seconds, 120 fps = 74 frames = 0.62 s).
    inline constexpr float Stage2Duration=.62f;
    inline constexpr float Stage2HitStart=.07f;
    inline constexpr float Stage2HitEnd=.19f;
    inline constexpr float Stage2DualSecondHitStart=.10f;
    inline constexpr float Stage2DualSecondHitEnd=.21f;
    inline constexpr float Stage2CancelStart=.38f;

    // Default toughness bases & follow-up window constants.
    inline constexpr float DefaultToughnessStage1=220.f;
    inline constexpr float DefaultToughnessStage2=260.f;
    inline constexpr float DefaultFollowupWindow=.45f;
    inline constexpr float DefaultBackstabCritBonus=25.f;

    // 3P body presentation variant names.
    inline const FName BodyVariantStage1(TEXT("ShadowStep"));
    inline const FName BodyVariantStage2(TEXT("ShadowStepFollow"));
    inline const FName BodyVariantOffhandStage1(TEXT("OffhandShadowStep"));
    inline const FName BodyVariantOffhandStage2(TEXT("OffhandShadowStepFollow"));

    inline bool IsBodyVariant(FName Variant)
    {
        return Variant==BodyVariantStage1||Variant==BodyVariantStage2||
            Variant==BodyVariantOffhandStage1||Variant==BodyVariantOffhandStage2;
    }

    inline FShadowStepCast Evaluate(const FShadowStepTuning& T,int32 Level,int32 MaxLevel=20)
    {
        const float Alpha=float(FMath::Clamp(Level,1,MaxLevel)-1)/FMath::Max(1,MaxLevel-1);
        FShadowStepCast Out;
        Out.Stage1DamageMultiplier=FMath::Lerp(T.Stage1DamageBase,T.Stage1DamageMax,Alpha);
        Out.Stage2DamageMultiplier=FMath::Lerp(T.Stage2DamageBase,T.Stage2DamageMax,Alpha);
        Out.DualPerHandRatio=T.DualPerHandRatio;
        Out.FollowupBackstabCritBonus=T.FollowupBackstabCritBonus;
        Out.FollowupWindowSeconds=T.FollowupWindowSeconds;
        Out.DashDistanceCM=FMath::Lerp(T.DashDistanceBaseCM,T.DashDistanceMaxCM,Alpha);
        Out.CooldownSeconds=FMath::Lerp(T.CooldownBase,T.CooldownMin,Alpha);
        Out.StaminaCost=FMath::Lerp(T.StaminaBase,T.StaminaMax,Alpha);
        Out.ToughnessStage1=T.ToughnessStage1;
        Out.ToughnessStage2=T.ToughnessStage2;
        return Out;
    }
}
