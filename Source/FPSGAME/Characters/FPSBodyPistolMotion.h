#pragma once
#include "FPSPlayerBodyTypes.h"
#include "../Weapons/OffhandReloadHandoff.h"
#include "../Weapons/LonePistolTwoHandAssets.h"

namespace FPSBodyPistolMotion
{
// A pair shares a body, not a hand-action channel. Left-hand overlays must not
// restart the right gun's interpolation or blend relative and absolute wrists.
inline FName HandChannel(const FFPSBodyState& State,int32 Side)
{
    if(State.Action==EFPSBodyAction::Dead)return TEXT("Dead");
    if(State.Motion==EFPSBodyMotion::Vault||State.Motion==EFPSBodyMotion::Mantle)return TEXT("Traversal");
    if(State.ConsumeHands&(1<<Side))return TEXT("Consume");
    if(Side==1&&State.Action==EFPSBodyAction::Cast&&State.Contacts.Channel!=TEXT("StaffCast"))return TEXT("Cast");
    if(Side==1&&State.Action==EFPSBodyAction::DoorPush)return TEXT("Door");
    if(State.Action==EFPSBodyAction::GunBash&&
        (State.ActionVariant==TEXT("PistolBashLeft")||State.ActionVariant==TEXT("PistolBashRight")))
        return State.ActionVariant;
    const auto& Hand=Side==0?State.RightHand:State.LeftHand;
    if(Hand.bReloading)return TEXT("PistolReload");
    if(Hand.bEquipping)return TEXT("PistolEquip");
    return TEXT("PistolCarry");
}
inline bool IsPistolChannel(FName Channel)
{
    return Channel==TEXT("PistolCarry")||Channel==TEXT("PistolReload")||Channel==TEXT("PistolEquip")||
        Channel==TEXT("PistolBashLeft")||Channel==TEXT("PistolBashRight");
}
inline bool IsRightSingle(const FFPSBodyState& State)
{
    return State.Family==TEXT("Pistol")&&!State.bDual&&!State.bOffhandPistol&&State.OffhandInstance.IsEmpty()
        &&LonePistolTwoHandAssets::Supports(State.Weapon);
}
inline bool HasRightSupport(const FFPSBodyState& State)
{
    return State.Family==TEXT("Unarmed")&&State.bOffhandPistol&&!State.bDual&&LonePistolTwoHandAssets::Supports(State.Weapon);
}
inline bool IsSingleReload(const FFPSBodyState& State)
{
    return (IsRightSingle(State)&&(State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty))||
        (HasRightSupport(State)&&State.LeftHand.bReloading);
}
inline bool HasSupportOffhand(const FFPSBodyState& State)
{
    return State.Family==TEXT("Pistol")&&!State.bDual&&!State.bOffhandPistol&&!State.OffhandInstance.IsEmpty();
}
inline bool UsesSupportReload(const FFPSBodyState& State)
{
    return HasSupportOffhand(State)&&State.OffhandReloadPhase==uint8(EOffhandReloadPhase::Reload)&&
        (State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty);
}
inline bool UsesPrimaryReload(const FFPSBodyState& State)
{
    return HasSupportOffhand(State)&&State.OffhandReloadPhase!=0&&
        (State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty);
}
inline bool ReturningToOffhand(const FFPSBodyState& State)
{
    return State.OffhandReloadPhase==uint8(EOffhandReloadPhase::Raise)&&State.bOffhandReloadReturnFromReload;
}
inline bool ReturningHandWithoutItem(const FFPSBodyState& State)
{
    return ReturningToOffhand(State)&&State.OffhandReloadProgress<FOffhandReloadHandoff::BodyReturnTransferFraction;
}
inline bool OffhandItemHidden(const FFPSBodyState& State)
{
    return State.OffhandReloadPhase==uint8(EOffhandReloadPhase::Reload)||ReturningHandWithoutItem(State)||
        (State.OffhandReloadPhase==uint8(EOffhandReloadPhase::Lower)&&State.OffhandReloadProgress>=FOffhandReloadHandoff::BodyLowerTransferStart);
}
inline float OffhandBodyLowerWeight(const FFPSBodyState& State)
{
    if(State.OffhandReloadPhase==uint8(EOffhandReloadPhase::Lower))
    {
        const float P=FMath::Clamp(State.OffhandReloadProgress/FOffhandReloadHandoff::BodyLowerTransferStart,0.f,1.f);
        return P*P*(3.f-2.f*P);
    }
    if(!ReturningToOffhand(State))return State.OffhandReloadLowerWeight;
    const float P=FMath::Clamp((State.OffhandReloadProgress-FOffhandReloadHandoff::BodyReturnTransferFraction)/
        (1.f-FOffhandReloadHandoff::BodyReturnTransferFraction),0.f,1.f);
    return 1.f-P*P*(3.f-2.f*P);
}
inline bool OwnsHand(const FFPSBodyState& State,int32 Side)
{
    return State.bDual||(Side==1&&State.bOffhandPistol)||(Side==0&&IsRightSingle(State));
}
inline bool UsesRelativeAction(const FFPSBodyState& State,int32 Side)
{
    if(!OwnsHand(State,Side))return false;
    if(State.ConsumeHands&(1<<Side))return false;
    if(Side==0&&IsRightSingle(State))
        return State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty||
            State.Action==EFPSBodyAction::Equip||State.Action==EFPSBodyAction::Inspect||State.Action==EFPSBodyAction::GunBash;
    const auto& Hand=Side==0?State.RightHand:State.LeftHand;
    return Hand.bReloading||Hand.bEquipping||
        (State.Action==EFPSBodyAction::GunBash&&
         (State.ActionVariant==TEXT("PistolBashLeft")||State.ActionVariant==TEXT("PistolBashRight")||
          (Side==1&&State.ActionVariant==TEXT("StaffOffhandBash"))));
}
}
