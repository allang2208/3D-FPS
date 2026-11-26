#pragma once
#include "CoreMinimal.h"

class UStaticMeshComponent;
class UPrimitiveComponent;
namespace GhostScytheMist
{
    extern const TCHAR* const MaterialPath;
    extern const TCHAR* const PlanePath;
    extern const FName HolderTag;
    void Refresh(UStaticMeshComponent* Blade);
    void Refresh(UStaticMeshComponent* Blade,bool bEquipped);
    void Clear(UStaticMeshComponent* Blade);
    UPrimitiveComponent* Find(const UPrimitiveComponent* Blade);
    void MatchVisibility(const UPrimitiveComponent* Blade);
}
