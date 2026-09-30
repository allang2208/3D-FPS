#pragma once
#include "CoreMinimal.h"
class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace HK416Attachments
{
// Fittings are authored in the same reference frame as the complete viewmodel.
FTransform ReferenceMount(const USkeletalMeshComponent* Host);
UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing, const FString& Part, bool Enabled);
}
