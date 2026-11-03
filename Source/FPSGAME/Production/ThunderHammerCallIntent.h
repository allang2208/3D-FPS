#pragma once
#include "CoreMinimal.h"

namespace ThunderHammerCallIntent
{
    enum class EPhase : uint8 { TapPending, Charging, Ready };
    // Reserve the click window before either hand enters the single-hand lift.
    // Fast charge modifiers retain a positive lift window and the same full-charge deadline.
    inline float PendingSeconds(float ChargeSeconds)
    {
        return FMath::Min(.24f,FMath::Max(.01f,ChargeSeconds)*.25f);
    }
    inline EPhase Phase(float Held,float ChargeSeconds)
    {
        if(Held>=ChargeSeconds)return EPhase::Ready;
        return Held<=PendingSeconds(ChargeSeconds)?EPhase::TapPending:EPhase::Charging;
    }
    inline float LiftSeconds(float ChargeSeconds)
    {
        return FMath::Max(.01f,ChargeSeconds-PendingSeconds(ChargeSeconds));
    }
    inline float Progress(float Held,float ChargeSeconds)
    {
        return FMath::Clamp((Held-PendingSeconds(ChargeSeconds))/LiftSeconds(ChargeSeconds),0.f,1.f);
    }
}
