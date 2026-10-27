#include "FluidPresentationSubsystem.h"
#include "../Building/ColdSteelCampfire.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

void UFluidPresentationSubsystem::RegisterCampfire(AColdSteelCampfire* Fire)
{
    if(IsValid(Fire)&&GetWorld()->GetNetMode()!=NM_DedicatedServer)Campfires.AddUnique(Fire);
}

void UFluidPresentationSubsystem::UnregisterCampfire(AColdSteelCampfire* Fire)
{
    Campfires.Remove(Fire);
}

void UFluidPresentationSubsystem::UpdateCampfires()
{
    Campfires.RemoveAllSwap([](const auto& Fire){return !Fire.IsValid();});
    if(Campfires.IsEmpty())return;
    TArray<FVector,TInlineAllocator<4>> Views;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(const APlayerController* PC=It->Get();PC&&PC->IsLocalController()&&PC->PlayerCameraManager)
            Views.Add(PC->PlayerCameraManager->GetCameraLocation());
    struct FCandidate {AColdSteelCampfire* Fire;double Distance;};
    TArray<FCandidate,TInlineAllocator<9>> Nearest;
    for(const auto& Entry:Campfires)
    {
        AColdSteelCampfire* Fire=Entry.Get();
        if(!Fire||!Fire->IsAvailable()||Fire->ActorHasTag(TEXT("VoxelDetached")))continue;
        // Finished meals stay visible after the fuel ends, until collected.
        if(!Fire->IsProvidingWarmth()&&Fire->SharedState().Recipe.IsNone()&&Fire->SharedState().Products.IsEmpty())continue;
        double Distance=TNumericLimits<double>::Max();
        for(const FVector& View:Views)Distance=FMath::Min(Distance,FVector::DistSquared(View,Fire->GetActorLocation()));
        // 30 m admission, 35 m retention and a small preference for active fires avoid churn.
        if(Distance>FMath::Square(Fire->HasPresentation()?3500.:3000.))continue;
        if(Fire->HasPresentation())Distance*=.81;
        const int32 At=Nearest.IndexOfByPredicate([Distance](const FCandidate& Other){return Distance<Other.Distance;});
        Nearest.Insert(FCandidate{Fire,Distance},At==INDEX_NONE?Nearest.Num():At);
        if(Nearest.Num()>8)Nearest.RemoveAt(8);
    }
    // Release the old selection first: never briefly exceed eight fire systems/lights.
    for(const auto& Entry:Campfires)
        if(AColdSteelCampfire* Fire=Entry.Get();Fire&&!Nearest.ContainsByPredicate([Fire](const FCandidate& C){return C.Fire==Fire;}))
            Fire->SetPresentationActive(false);
    for(const FCandidate& Candidate:Nearest)Candidate.Fire->SetPresentationActive(true);
}
