#pragma once
#include "FPSBodyPistolMotion.h"
#include "FPSBodyPistolMagazineTiming.h"
#include "../Weapons/DanWesson715WeaponAssets.h"

namespace FPSBodySinglePistolSource
{
inline bool Eligible(const FFPSBodyState& State)
{
    if(!(FPSBodyPistolMotion::IsRightSingle(State)||FPSBodyPistolMotion::HasRightSupport(State))||
        State.Motion!=EFPSBodyMotion::Ground||State.ConsumeHands)return false;
    return State.Action==EFPSBodyAction::None||State.Action==EFPSBodyAction::Equip||
        State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty;
}
inline int32 Primary(const FFPSBodyState& State){return FPSBodyPistolMotion::HasRightSupport(State)?1:0;}
struct FReloadSample {FString Phase;float Fraction=0.f;bool Active=false;};
inline FReloadSample Reload(const FFPSBodyState& State)
{
    const bool Left=Primary(State)==1;
    const auto& Hand=Left?State.LeftHand:State.RightHand;
    FReloadSample Result;
    Result.Active=Left?Hand.bReloading:FPSBodyPistolMotion::IsSingleReload(State);
    if(!Result.Active)return Result;
    const float P=FMath::Clamp(Left?Hand.Progress:State.ActionProgress,0.f,1.f);
    float Begin=.18f,End=.60f;
    if(Hand.bRevolver&&!Hand.bSpeedloaderReload&&Hand.ReloadCount>0&&Hand.ReloadSourceLength>0.f)
    {
        const float Time=P*Hand.ReloadSourceLength;
        const float Start=DanWesson715WeaponAssets::SingleLoopBegin(Hand.ReloadStart==0);
        const float Finish=Start+DanWesson715WeaponAssets::SingleStep*Hand.ReloadCount;
        if(Time<Start){Result.Phase=TEXT("Reload.Init");Result.Fraction=Time/FMath::Max(Start,.01f);}
        else if(Time<Finish){Result.Phase=TEXT("Reload.Loop");Result.Fraction=FMath::Fmod(Time-Start,DanWesson715WeaponAssets::SingleStep)/DanWesson715WeaponAssets::SingleStep;}
        else {Result.Phase=TEXT("Reload.End");Result.Fraction=(Time-Finish)/FMath::Max(.01f,Hand.ReloadSourceLength-Finish);}
    }
    else
    {
        if(Hand.bRevolver){Begin=.30f;End=.68f;}
        else if(Hand.ReloadSourceLength>0.f)
        {
            // Ordinary/empty reloads share the magazine contact keys. Mapping
            // by total duration shifted the empty reload's insert past the hand.
            Begin=FPSBodyPistolMagazineTiming::Appear/Hand.ReloadSourceLength;
            End=FPSBodyPistolMagazineTiming::Seat/Hand.ReloadSourceLength;
        }
        if(P<Begin){Result.Phase=TEXT("Reload.Init");Result.Fraction=P/Begin;}
        else if(P<End){Result.Phase=TEXT("Reload.Loop");Result.Fraction=(P-Begin)/(End-Begin);}
        else {Result.Phase=TEXT("Reload.End");Result.Fraction=(P-End)/(1.f-End);}
    }
    Result.Fraction=FMath::Clamp(Result.Fraction,0.f,1.f);
    return Result;
}
}
