#pragma once
#include "FPSVisualRecoil.h"

// M24 single-shot presentation. The catalog still owns control-aim recoil,
// stability and accessory multipliers; no bone or resting aim pose is edited.
namespace M24Recoil
{
    inline constexpr float ReferenceRecoilScale = 2.6f;
    inline constexpr float CameraPitchGain = 1.65f;
    inline FPSVisualRecoil::FProfile VisualProfile()
    {
        FPSVisualRecoil::FProfile P;
        P.Position=FVector(.35f,.50f,1.50f);
        P.Rotation=FVector(1.60f,.35f,.22f);
        P.Flip=1.10f;P.Jitter=.35f;
        P.PositionStiffness=260.f;P.PositionDamping=26.f;
        P.RotationStiffness=250.f;P.RotationDamping=25.f;
        P.ClipPosition=FVector(0.f,.002f,.016f);
        P.ClipRotation=FVector(FMath::DegreesToRadians(4.f),0.f,0.f);
        P.ClipADSPosition=FVector(0.f,0.f,.018f);
        P.ClipADSRotation=FVector(FMath::DegreesToRadians(.7f),0.f,0.f);
        P.ADSRotationScale=.65f;
        return P;
    }
    inline float Pulse(float Seconds)
    {
        // A sharp rise followed by a finite recovery, clear of the bolt-hand
        // contact later in the fire clip. Retiming the bolt does not stretch it.
        if(Seconds<0.f||Seconds>=.38f)return 0.f;
        return FPSVisualRecoil::ClipWave(Seconds)*(1.f-FMath::SmoothStep(.20f,.38f,Seconds));
    }
}
