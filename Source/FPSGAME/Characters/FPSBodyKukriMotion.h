#pragma once
#include "FPSPlayerBodyTypes.h"

/** Single-hand library selection; the Kukri component retains all gameplay. */
namespace FPSBodyKukriMotion
{
inline bool IsOffhandThrust(const FFPSBodyState& S)
{
    return S.Family==TEXT("Pistol")&&!S.bDual&&!S.bOffhandPistol&&
        S.Action==EFPSBodyAction::Thrust&&S.ActionVariant==TEXT("OffhandKukriThrust");
}
inline bool IsOffhandUppercut(const FFPSBodyState& S)
{
    return S.Family==TEXT("Pistol")&&!S.bDual&&!S.bOffhandPistol&&
        S.Action==EFPSBodyAction::HeavyStrike&&S.ActionVariant==TEXT("OffhandKukriUppercut");
}
inline bool MatchesOffhand(const FFPSBodyState& S,bool bLoaded,const FString& LoadedInstance)
{
    // Equipment and body-state properties can arrive in either order.
    return bLoaded&&!S.OffhandInstance.IsEmpty()&&S.OffhandInstance==LoadedInstance;
}
inline bool IsAttack(const FFPSBodyState& S)
{
    if(IsOffhandUppercut(S))return true;
    if(S.Family!=TEXT("Kukri"))return false;
    switch(S.Action)
    {
    case EFPSBodyAction::Strike:case EFPSBodyAction::Thrust:case EFPSBodyAction::HeavyStrike:
    case EFPSBodyAction::Pommel:case EFPSBodyAction::Charge:case EFPSBodyAction::Whirlwind:return true;
    default:return false;
    }
}
inline bool HasExecutorClock(const FFPSBodyState& S)
{
    return S.bHasActionProgress&&(IsAttack(S)||IsOffhandThrust(S)||
        (S.Family==TEXT("Kukri")&&S.Action==EFPSBodyAction::Equip));
}
inline float AttackLegWeight(const FFPSBodyState& S,float Speed,bool bAuthoredDualDash=false)
{
    if(!IsAttack(S))return 0.f;
    // Keep attack weight transfer at every travel speed, without freezing a
    // running stride for an entire slow cut or indefinitely held charge.
    if(S.Action==EFPSBodyAction::Whirlwind)return 1.f;
    if(S.Action==EFPSBodyAction::Charge)return 1.f-FMath::Clamp(Speed/100.f,0.f,1.f);
    const float P=FMath::Clamp(S.ActionProgress,0.f,1.f);
    const float Enter=(S.ActionVariant==TEXT("HeavyRelease")||S.ActionVariant==TEXT("DualHeavyRelease"))?1.f:FMath::SmoothStep(0.f,.12f,P);
    const float Exit=1.f-FMath::SmoothStep(.82f,1.f,P);
    const float Travel=FMath::Clamp(Speed/120.f,0.f,1.f);
    if(S.Action==EFPSBodyAction::HeavyStrike&&S.ActionVariant==TEXT("SprintAttack")&&
        (S.OffhandInstance.IsEmpty()||bAuthoredDualDash))
    {
        // Carry the actual braking stride into the authored lead-foot landing.
        // Fast residual travel still retains some gait instead of sliding a
        // fully planted pose; once stopped the complete support take owns it.
        const float Hit=FMath::Clamp(S.ContactFraction,.10f,.65f);
        const float Release=FMath::Clamp(S.ReleaseFraction,Hit+.01f,.75f);
        const float Plant=FMath::SmoothStep(Hit-.18f,Hit-.025f,P)*
            (1.f-.35f*FMath::SmoothStep(150.f,420.f,Speed))*
            (1.f-FMath::SmoothStep(Release+.16f,.91f,P));
        return FMath::Lerp(1.f,Plant,Travel);
    }
    // The uppercut has a contact-aligned forward stride authored into the
    // full-body take. Its own lunge speed must not replace it with live jogging.
    const bool Uppercut=(S.Action==EFPSBodyAction::HeavyStrike&&S.ActionVariant==TEXT("Uppercut"))||IsOffhandUppercut(S);
    const float MovingCommit=Uppercut?1.f:1.f-.60f*FMath::SmoothStep(20.f,240.f,Speed);
    return FMath::Lerp(1.f,Enter*Exit*MovingCommit,Travel);
}
inline bool IsCarry(const FFPSBodyState& S)
{
    return S.Action==EFPSBodyAction::None||S.Action==EFPSBodyAction::Cast||S.Action==EFPSBodyAction::DoorPush||
        (S.Action==EFPSBodyAction::Consume&&(S.ConsumeHands&1)==0);
}
inline FName Clip(const FFPSBodyState& S)
{
    if(IsOffhandUppercut(S)&&S.Motion==EFPSBodyMotion::Ground)return TEXT("Pistol.KukriUppercut");
    if(S.Family!=TEXT("Kukri")||S.Motion==EFPSBodyMotion::Vault||S.Motion==EFPSBodyMotion::Mantle||S.Action==EFPSBodyAction::Dead)return NAME_None;
    if(IsCarry(S))return TEXT("Kukri.FullBody.Idle");
    switch(S.Action)
    {
    case EFPSBodyAction::Equip:return TEXT("Kukri.FullBody.Equip");
    case EFPSBodyAction::Strike:return S.ActionVariant==TEXT("Attack2")||S.ActionVariant==TEXT("DualAttack2")?
        TEXT("Kukri.FullBody.Slash2"):TEXT("Kukri.FullBody.Slash1");
    case EFPSBodyAction::Thrust:return TEXT("Kukri.FullBody.Thrust");
    case EFPSBodyAction::Charge:return TEXT("Kukri.FullBody.Charge");
    case EFPSBodyAction::HeavyStrike:
        if(S.ActionVariant==TEXT("Uppercut"))return TEXT("Kukri.FullBody.Uppercut");
        if(S.ActionVariant==TEXT("SprintAttack"))return TEXT("Kukri.FullBody.Dash");
        return TEXT("Kukri.FullBody.Heavy");
    case EFPSBodyAction::Pommel:return TEXT("Kukri.FullBody.Pommel");
    case EFPSBodyAction::Whirlwind:
        if(S.ActionVariant==TEXT("DualWhirlwind"))
            return S.ActionProgress<S.ContactFraction?TEXT("Kukri.FullBody.Dual.Whirlwind.Start"):
                S.ActionProgress<S.ReleaseFraction?TEXT("Kukri.FullBody.Dual.Whirlwind.Loop"):TEXT("Kukri.FullBody.Dual.Whirlwind.End");
        return S.ActionProgress<S.ContactFraction?TEXT("Kukri.FullBody.Whirlwind.Start"):
            S.ActionProgress<S.ReleaseFraction?TEXT("Kukri.FullBody.Whirlwind.Loop"):TEXT("Kukri.FullBody.Whirlwind.End");
    default:return NAME_None;
    }
}
inline FName DualClip(FName Base)
{
    static const FName Single[]={TEXT("Kukri.FullBody.Idle"),TEXT("Kukri.FullBody.Uppercut"),TEXT("Kukri.FullBody.Dash"),
        TEXT("Kukri.FullBody.Slash1"),TEXT("Kukri.FullBody.Slash2"),TEXT("Kukri.FullBody.Thrust"),
        TEXT("Kukri.FullBody.Charge"),TEXT("Kukri.FullBody.Heavy"),TEXT("Kukri.FullBody.Recover1"),TEXT("Kukri.FullBody.Recover2"),
        TEXT("Kukri.FullBody.Equip"),TEXT("Kukri.FullBody.Pommel")};
    static const FName Dual[]={TEXT("Kukri.FullBody.Dual.Idle"),TEXT("Kukri.FullBody.Dual.Uppercut"),TEXT("Kukri.FullBody.Dual.Dash"),
        TEXT("Kukri.FullBody.Dual.Slash1"),TEXT("Kukri.FullBody.Dual.Slash2"),TEXT("Kukri.FullBody.Dual.Thrust"),
        TEXT("Kukri.FullBody.Dual.Charge"),TEXT("Kukri.FullBody.Dual.Heavy"),TEXT("Kukri.FullBody.Dual.Recover1"),TEXT("Kukri.FullBody.Dual.Recover2"),
        TEXT("Kukri.FullBody.Dual.Equip"),TEXT("Kukri.FullBody.Dual.Pommel")};
    for(int32 I=0;I<UE_ARRAY_COUNT(Single);++I)if(Base==Single[I])return Dual[I];
    return NAME_None;
}
inline bool UsesAuthoredClock(FName Key)
{
    return Key==TEXT("Kukri.FullBody.Dual.Slash1")||Key==TEXT("Kukri.FullBody.Dual.Slash2")||
        Key==TEXT("Kukri.FullBody.Dual.Thrust")||Key==TEXT("Kukri.FullBody.Dual.Charge")||Key==TEXT("Kukri.FullBody.Dual.Heavy")||
        Key==TEXT("Pistol.KukriUppercut")||Key==TEXT("Kukri.FullBody.Dual.Pommel");
}
inline uint8 PreserveHands(const FFPSBodyState& S,bool bOffhandKukriEquipment)
{
    if(IsOffhandUppercut(S)&&bOffhandKukriEquipment)return 0;
    // The dual whirlwind owns both weapon arms. The generic offhand-preserve
    // mask would otherwise discard the authored left-arm extension.
    if(S.Family==TEXT("Kukri")&&S.Action==EFPSBodyAction::Whirlwind&&S.ActionVariant==TEXT("DualWhirlwind"))return 0;
    const bool IndependentLeft=S.bOffhandPistol||S.Action==EFPSBodyAction::Cast||
        S.Action==EFPSBodyAction::DoorPush||(S.Action==EFPSBodyAction::Consume&&(S.ConsumeHands&2));
    // Dual whirlwind endpoints match the authored carry. Keep that left arm
    // through the carry crossfade instead of snapping to the generic offhand IK.
    if(S.Family==TEXT("Kukri")&&bOffhandKukriEquipment&&IsCarry(S)&&!IndependentLeft)return 0;
    // Casting, consumables and unrelated offhand equipment retain their poses.
    return IndependentLeft||!S.OffhandInstance.IsEmpty()?2:0;
}

/** Cosmetic recovery only. Buffered attacks keep their matching loaded poses;
 * an ended chain gets its own full-body return without changing attack timing. */
struct FComboRecovery
{
    FName PreviousNormal,Active;
    float PreviousProgress=0.f,Seconds=0.f;
    FName Advance(const FFPSBodyState& S,float Delta)
    {
        const FName Next=Clip(S);
        if(S.Family!=TEXT("Kukri")||S.Motion!=EFPSBodyMotion::Ground||S.Action!=EFPSBodyAction::None)
        {
            Active=NAME_None;Seconds=0.f;
            const bool Normal=Next==TEXT("Kukri.FullBody.Slash1")||Next==TEXT("Kukri.FullBody.Slash2");
            PreviousNormal=Normal?Next:NAME_None;PreviousProgress=S.ActionProgress;
            return Next;
        }
        if(!PreviousNormal.IsNone())
        {
            if(PreviousProgress>.80f)
                Active=PreviousNormal==TEXT("Kukri.FullBody.Slash1")?TEXT("Kukri.FullBody.Recover1"):TEXT("Kukri.FullBody.Recover2");
            PreviousNormal=NAME_None;Seconds=0.f;
        }
        if(!Active.IsNone())
        {
            Seconds+=Delta;
            if(Seconds<.5f)return Active;
            Active=NAME_None;
        }
        return Next;
    }
};
}
