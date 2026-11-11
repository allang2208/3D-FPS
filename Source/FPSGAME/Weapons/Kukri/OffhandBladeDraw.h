#pragma once
#include "CoreMinimal.h"

class USoundBase;
namespace OffhandBladeDraw
{
    inline const FName Kukri(TEXT("OffhandKukriEquip")),Hatchet(TEXT("OffhandHatchetEquip"));
    inline const TCHAR* Asset(bool Axe)
    {
        return Axe?TEXT("/Game/Weapons/TacticalHatchet20261101/OffhandDraw/Arms/A_OffhandHatchetEquip.A_OffhandHatchetEquip"):
            TEXT("/Game/Weapons/TacticalHatchet20261101/OffhandDraw/Arms/A_OffhandKukriEquip.A_OffhandKukriEquip");
    }
    inline bool IsClip(FName Clip){return Clip==Kukri||Clip==Hatchet;}
    float Length(bool Axe);
    FTransform InHand(bool Axe,float Time);
    FTransform FlightDelta(bool Axe,float Time);
    FVector WristOffset(bool Axe,float Time);
    float OpenHand(bool Axe,float Time);
    void Camera(bool Axe,float Time,FRotator& Rotation,float& Fov);
    void PlayCues(UObject* Owner,bool Axe,float Before,float Now,USoundBase* Toss,USoundBase* Catch);
}
