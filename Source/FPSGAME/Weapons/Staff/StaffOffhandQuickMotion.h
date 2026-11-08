#pragma once
#include "CoreMinimal.h"
#include "../Kukri/OffhandKukriAuthoredStrike.h"
#include "../Kukri/OffhandKukriAuthoredUppercut.h"
#include "../Kukri/OffhandAxeQuickMotion.h"

namespace StaffOffhandQuickMotion
{
    // Keep the accepted 0.633 s thrust intact. Change between native forward/reverse grips below the frame.
    inline constexpr float Entry=.14f,Return=.16f,CancelReturn=.18f;
    inline constexpr float End=OffhandKukriStrike::Length+Return;
    inline constexpr float Duration=Entry+End;
    inline const FVector HiddenOffset(-6.f,0.f,-65.f);
    inline float Ease(float A,float B,float T)
    {const float X=FMath::Clamp((T-A)/(B-A),0.f,1.f);return X*X*X*(X*(X*6.f-15.f)+10.f);}
    inline bool StrikeRig(float T,float Length=OffhandKukriStrike::Length){return T>=-Entry*.5f&&T<Length+Return*.5f;}
    inline float NativeLower(float T,float Length=OffhandKukriStrike::Length)
    {return T<0.f?Ease(-Entry,-Entry*.5f,T):1.f-Ease(Length+Return*.5f,Length+Return,T);}
    inline float StrikeLower(float T,float Length=OffhandKukriStrike::Length)
    {return T<0.f?1.f-Ease(-Entry*.5f,0.f,T):Ease(Length,Length+Return*.5f,T);}
    inline float UpperEvade(float T)
    {return Ease(-Entry,.12f,T)*(1.f-Ease(.90f,OffhandKukriUpper::Length+Return,T));}
    inline FVector DonorRightHand(float T,bool Uppercut=false)
    {
        // SourceAssets/DualPistolKukri20261025/Work/strike/strike_keys.json, key 0:
        // left_wrist (29.177,13.518,-12.807) minus wrist_offset (7.283,4.772,-2.516).
        // Recover the donor pistol's unframed grip once, then follow its authored framing.
        // The knife path must not follow the staff's much longer, independently evading shaft.
        static const FVector Native=OffhandKukriStrike::Keys[0].Framing.InverseTransformPosition(FVector(21.894,8.746,-10.291));
        FVector Wrist,Shoulder,Pole;FQuat Hand;FTransform Frame;
        if(Uppercut)OffhandKukriUpper::SamplePose(FMath::Clamp(T,0.f,OffhandKukriUpper::Length),Wrist,Hand,Shoulder,Pole,Frame);
        else OffhandKukriStrike::SamplePose(FMath::Clamp(T,0.f,OffhandKukriStrike::Length),Wrist,Hand,Shoulder,Pole,Frame);
        return Frame.TransformPosition(Native);
    }
}
