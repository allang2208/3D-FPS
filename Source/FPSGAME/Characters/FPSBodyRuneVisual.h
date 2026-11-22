#pragma once
#include "CoreMinimal.h"
class UStaticMeshComponent;
class URuneSwordComponent;
struct FColdSteelItem;
struct FFPSBodyAttachment;
namespace FPSBodyRuneVisual
{
    void Capture(UStaticMeshComponent* Source,const FColdSteelItem* Item,FFPSBodyAttachment& Out,const URuneSwordComponent* Whirlwind=nullptr);
    void Apply(UStaticMeshComponent* Mesh,const FFPSBodyAttachment& Description);
    FString Key(const FFPSBodyAttachment& Description);
}
