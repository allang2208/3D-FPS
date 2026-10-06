#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace RSH12ForegripAssets
{
    UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
        UStaticMeshComponent* Existing, const TCHAR* Family, bool bEnabled);
    inline FString ProfilePath(FName Family)
    {
        return TEXT("/Game/Weapons/RSH12/Foregrips20261004/Profiles/DA_RSH12_")+Family.ToString();
    }
}
