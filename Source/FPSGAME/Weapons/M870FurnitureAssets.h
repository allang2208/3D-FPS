#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace M870FurnitureAssets
{
FString ForegripFamily(const FString& Variant);
bool SupportsStock(const FString& Variant);
FString MeshPath(const FString& Part);
FString ProfilePath(FName Family);
FString InstalledPart(const UStaticMeshComponent* Component);
// A replacement stock keeps the original traditional neck and hand contact.
// M870 has no separately replaceable rear grip.
void ConfigureRear(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent*& Stock,UStaticMeshComponent*& Grip,
    const FString& StockVariant,bool Enabled);
UStaticMeshComponent* ConfigureForegrip(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const FString& Family,bool Enabled);
}
