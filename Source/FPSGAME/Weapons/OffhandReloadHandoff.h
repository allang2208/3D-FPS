#pragma once
#include "CoreMinimal.h"

// Non-pistol offhands pay real handling time around the existing pistol reload.
// Keep these seconds independent of reload-speed modifiers and source notifies.
enum class EOffhandReloadPhase : uint8 { None, Lower, Reload, Raise };

struct FOffhandReloadHandoff
{
    static constexpr float LowerSeconds=.55f;
    static constexpr float RaiseSeconds=.40f;
    static constexpr float BodyReturnTransferFraction=.35f;
    static constexpr float BodyLowerTransferStart=.76f;
    EOffhandReloadPhase Phase=EOffhandReloadPhase::None;
    FString Weapon,Offhand;
    int32 Slot=INDEX_NONE;
    double StartedAt=0.0;
    float ReturnWeight=1.f;
    bool bReturnFromReload=false;
    bool bEarlyReturn=false,bReloadArmExit=false;
    double ReturnStartedAt=0.0;
    float RaiseDuration=RaiseSeconds;
    EOffhandReloadPhase PresentationPhase() const {return bEarlyReturn&&Phase==EOffhandReloadPhase::Reload?EOffhandReloadPhase::Raise:Phase;}
    bool Active() const {return Phase!=EOffhandReloadPhase::None;}
    bool Transition() const {return Phase==EOffhandReloadPhase::Lower||Phase==EOffhandReloadPhase::Raise;}
    float ProgressRate() const
    {
        if(Phase==EOffhandReloadPhase::Lower)return 1.f/LowerSeconds;
        if(PresentationPhase()==EOffhandReloadPhase::Raise)return 1.f/FMath::Max(.001f,RaiseDuration);
        return 0.f;
    }
    float Progress(double Now) const {return FMath::Clamp(float(Now-(bEarlyReturn?ReturnStartedAt:StartedAt))*ProgressRate(),0.f,1.f);}
    float LowerWeight(double Now) const
    {
        const auto Ease=[](float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);};
        if(Phase==EOffhandReloadPhase::Lower)return Ease(float(Now-StartedAt)/LowerSeconds);
        if(PresentationPhase()==EOffhandReloadPhase::Raise)
        {
            const float P=Progress(Now);
            const float Lift=bReturnFromReload?(P-BodyReturnTransferFraction)/(1.f-BodyReturnTransferFraction):P;
            return ReturnWeight*(1.f-Ease(Lift));
        }
        if(Phase==EOffhandReloadPhase::Reload)return 1.f;
        return 0.f;
    }
};
