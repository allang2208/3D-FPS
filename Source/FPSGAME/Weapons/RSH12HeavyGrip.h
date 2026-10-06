#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;
struct FGunsmithWeapon;

namespace RSH12HeavyGrip
{
    inline constexpr const TCHAR* Slot=TEXT("grip_body");
    inline constexpr const TCHAR* Part=TEXT("rsh12_heavy_grip");
    inline constexpr const TCHAR* QuickDrawPart=TEXT("rsh12_quickdraw_grip");
    inline bool IsPart(const FString& Id) {return Id==Part||Id==QuickDrawPart;}
    inline constexpr const TCHAR* FactorySection=TEXT("M_RSH12_FactoryGrip");
    void ShowFactory(USkeletalMeshComponent* Host,bool bVisible);
    void Configure(AActor* Owner,USkeletalMeshComponent* Host,
        TObjectPtr<UStaticMeshComponent>& Body,TObjectPtr<UStaticMeshComponent>& Surface,
        const FGunsmithWeapon* Weapon,const FString& BodyId,const FString& SurfaceId,bool bEnabled);
}
