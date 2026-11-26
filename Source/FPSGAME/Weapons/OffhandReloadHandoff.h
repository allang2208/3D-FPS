#pragma once
#include "CoreMinimal.h"
#include "../UI/ColdSteelInventoryTypes.h"

// Non-pistol offhands pay real handling time around the existing pistol reload.
// Keep these seconds independent of reload-speed modifiers and source notifies.
enum class EOffhandReloadPhase : uint8 { None, Lower, Reload, Raise };

struct FOffhandReloadHandoff
{
    static constexpr float LowerSeconds=.55f;
    static constexpr float RaiseSeconds=.40f;
    // A knife hand just drops out of view (OffhandKukriComponent's lowering arc); a book is tucked away.
    static constexpr float BladeLowerSeconds=.30f;
    static constexpr float BodyReturnTransferFraction=.35f;
    static constexpr float BodyLowerTransferStart=.76f;
    static float LowerSecondsFor(const FColdSteelItem& Item) {return ColdSteelInventory::UsesKukriMoveset(Item)?BladeLowerSeconds:LowerSeconds;}
    EOffhandReloadPhase Phase=EOffhandReloadPhase::None;
    FString Weapon,Offhand;
    int32 Slot=INDEX_NONE;
    double StartedAt=0.0;
    float LowerDuration=LowerSeconds;
    float ReturnWeight=1.f;
    bool bReturnFromReload=false;
    bool bWaitForReloadEnd=false;
    bool bEarlyReturn=false,bReloadArmExit=false;
    double ReturnStartedAt=0.0;
    float RaiseDuration=RaiseSeconds;
    EOffhandReloadPhase PresentationPhase() const {return bEarlyReturn&&Phase==EOffhandReloadPhase::Reload?EOffhandReloadPhase::Raise:Phase;}
    bool Active() const {return Phase!=EOffhandReloadPhase::None;}
    bool Transition() const {return Phase==EOffhandReloadPhase::Lower||Phase==EOffhandReloadPhase::Raise;}
    float ProgressRate() const
    {
        if(Phase==EOffhandReloadPhase::Lower)return 1.f/LowerDuration;
        if(PresentationPhase()==EOffhandReloadPhase::Raise)return 1.f/FMath::Max(.001f,RaiseDuration);
        return 0.f;
    }
    float Progress(double Now) const {return FMath::Clamp(float(Now-(bEarlyReturn?ReturnStartedAt:StartedAt))*ProgressRate(),0.f,1.f);}
    float LowerWeight(double Now) const
    {
        const auto Ease=[](float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);};
        if(Phase==EOffhandReloadPhase::Lower)return Ease(float(Now-StartedAt)/LowerDuration);
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
