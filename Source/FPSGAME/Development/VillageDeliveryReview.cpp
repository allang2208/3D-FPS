// Opt-in editor game probe; gameplay and replication use the production entry points.
#if WITH_EDITOR
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/TemperateVillageSite.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../NPC/VillageMillKeeper.h"
#include "Components/DynamicMeshComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

namespace
{
void ReviewVillageDelivery(const TArray<FString>& Args,UWorld* World)
{
    FString Directory;
    if (!World || Args.Num()!=1 || !FParse::Param(FCommandLine::Get(),TEXT("VillageDeliveryReview"))
        || !FParse::Value(FCommandLine::Get(),TEXT("VillageDeliveryOutput="),Directory)) return;
    const FString& Mode=Args[0];
    if (Mode==TEXT("ground"))
    {
        for (TActorIterator<ATemperateHillsWorld> Hills(World); Hills; ++Hills)
        {
            if (!Hills->bReady || !Hills->IsForestVillage()) continue;
            FString Rows=TEXT("local_x,local_y,height_cm,collision_cm\n");
            for (FVector2D Local : {FVector2D(-13,4),{-27,-1},{25,8},{-18,18},{1,13},{-37,21},
                                    {-34.5,26.6},{-34.5,31.5},{16.5,41},{12,38},{24,35},{21,-26}})
            {
                const FVector2D At=Hills->GetVillageSite().World(Local.X*100.,Local.Y*100.);
                const double Z=Hills->Height(At.X,At.Y);
                FHitResult Hit;
                bool Found=false;
                for (auto* C:TInlineComponentArray<UDynamicMeshComponent*>(*Hills))
                    if (C->GetFName()==TEXT("ForestVillageFoundation") &&
                        C->LineTraceComponent(Hit,FVector(At,Z+250.),FVector(At,Z-250.),FCollisionQueryParams::DefaultQueryParam))
                    {Found=true;break;}
                Rows+=FString::Printf(TEXT("%.1f,%.1f,%.3f,%.3f\n"),Local.X,Local.Y,Z,Found?Hit.ImpactPoint.Z:-999999.);
            }
            FFileHelper::SaveStringToFile(Rows,*(Directory/TEXT("ground.csv")));
            break;
        }
        return;
    }
    if (Mode==TEXT("repair") && World->GetNetMode()==NM_ListenServer)
    {
        for (TActorIterator<ATemperateHillsWorld> Hills(World); Hills; ++Hills)
        {
            if (!Hills->bReady || !Hills->IsForestVillage()) continue;
            FText Why;
            const bool OK=Hills->UnlockVillagePlan(TEXT("windmill"),Why) && Hills->UnlockVillagePlan(TEXT("tavern"),Why);
            FFileHelper::SaveStringToFile(OK?FString(TEXT("ok")):Why.ToString(),*(Directory/TEXT("repair.txt")));
            return;
        }
    }
    if (World->GetNetMode()!=NM_Client) return;
    APlayerController* Local=World->GetFirstPlayerController();
    auto* Dialogue=Local?Local->FindComponentByClass<UChapelDialogueComponent>():nullptr;
    if (!Dialogue || !Local->IsLocalController()) return;
    if (Mode==TEXT("speak"))
    {
        for (TActorIterator<AVillageMillKeeper> Keeper(World); Keeper; ++Keeper)
            if (Dialogue->CanStartConversation(*Keeper)){Dialogue->OpenMerchant(*Keeper);return;}
    }
    if (Mode==TEXT("dialogue") && Dialogue->IsOpen() && Dialogue->IsMillKeeper() && !Dialogue->IsPending())
    {
        FFileHelper::SaveStringToFile(TEXT("accepted"),*(Directory/TEXT("client-dialogue.txt")));
        Dialogue->Close();
    }
}
FAutoConsoleCommandWithWorldAndArgs GReviewVillageDelivery(TEXT("fps.Test.VillageDelivery"),
    TEXT("Review the isolated village repair and conversation session."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&ReviewVillageDelivery));
}
#endif

