#pragma once
#include "CoreMinimal.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
namespace ProductionObservers
{
inline TArray<FVector> Gather(UWorld* World,FVector Local)
{
    TArray<FVector> Views{Local};if(World->GetNetMode()!=NM_Client)
        for(auto It=World->GetPlayerControllerIterator();It;++It)if(APawn* Pawn=It->Get()->GetPawn())Views.AddUnique(Pawn->GetActorLocation());
    return Views;
}
inline double Distance(const TArray<FVector>& Views,FVector Position)
{double Best=DBL_MAX;for(const auto& View:Views)Best=FMath::Min(Best,FVector::DistSquared2D(View,Position));return Best;}
}
