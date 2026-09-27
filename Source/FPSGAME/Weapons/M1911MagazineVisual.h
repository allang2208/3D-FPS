#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace M1911MagazineVisual
{
    void ShowFactoryMagazine(USkeletalMeshComponent* Host, bool bVisible);
    UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
        UStaticMeshComponent* Existing, bool bEnabled);
}
