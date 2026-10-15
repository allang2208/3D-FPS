#pragma once
#include "CoreMinimal.h"
class UStaticMeshComponent;
struct FColdSteelItem;
struct FFPSBodyAttachment;
namespace FPSBodyRuneVisual
{
    void Capture(UStaticMeshComponent* Source,const FColdSteelItem* Item,FFPSBodyAttachment& Out);
    void Apply(UStaticMeshComponent* Mesh,const FFPSBodyAttachment& Description);
    FString Key(const FFPSBodyAttachment& Description);
}
