#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"

void UDungeonRunSubsystem::InitializeShrine()
{
    const TArray<TSharedPtr<FJsonValue>>* Statues=nullptr;
    if(!ShrineConfig||!ShrineConfig->TryGetArrayField(TEXT("statues"),Statues)||Statues->IsEmpty())return;
    const FName Tag(*ShrineConfig->GetStringField(TEXT("actor_tag")));
    for(TActorIterator<AActor> It(GetWorld());It;++It)
        if(It->ActorHasTag(Tag)){ShrineActor=*It;break;}
    if(!ShrineActor.IsValid())return;
    FRandomStream Random=GameplayStream(DungeonRunDomains::ShrineSelection);
    const auto Choice=(*Statues)[Random.RandRange(0,Statues->Num()-1)]->AsObject();
    const FString Path=Choice->GetStringField(TEXT("mesh"));
    // The generator's resource stage already loaded all choices and retains them.
    UStaticMesh* Mesh=FindObject<UStaticMesh>(nullptr,*Path);
    auto* Component=ShrineActor->FindComponentByClass<UStaticMeshComponent>();
    if(!Mesh||!Component){ShrineActor.Reset();return;}
    Component->UnregisterComponent();
    Component->SetStaticMesh(Mesh);
    Component->EmptyOverrideMaterials();
    // Imported FBX axes are per-asset data; the original +X assumption turned
    // the six -Y Blender fronts sideways after UE's Y reflection.
    double MeshFrontYaw=90.;
    Choice->TryGetNumberField(TEXT("front_local_yaw_deg"),MeshFrontYaw);
    const TArray<TSharedPtr<FJsonValue>>* Exit=nullptr;
    if(ShrineConfig->TryGetArrayField(TEXT("exit_target_cm"),Exit)&&Exit->Num()==3)
    {
        const FVector Target((*Exit)[0]->AsNumber(),(*Exit)[1]->AsNumber(),(*Exit)[2]->AsNumber());
        const FVector Outward=Target-ShrineActor->GetActorLocation();
        if(!Outward.IsNearlyZero())
            ShrineActor->SetActorRotation(FRotator(0.,Outward.Rotation().Yaw-MeshFrontYaw,0.));
    }
    Component->SetCanEverAffectNavigation(false); // The permanent pedestal owns the floor obstruction.
    Component->RegisterComponent();
    ShrineName=Choice->GetStringField(TEXT("name"));
    ShrineDescription=Choice->GetStringField(TEXT("description"));
    ShrineBlessing=FName(*Choice->GetStringField(TEXT("buff_id")));
    Choice->TryGetNumberField(TEXT("heal_fraction"),ShrineHealFraction);
    const TSharedPtr<FJsonObject>* Effects=nullptr;
    if(Choice->TryGetObjectField(TEXT("effects"),Effects))
        for(const auto& Pair:(*Effects)->Values)if(Pair.Value->Type==EJson::Number)
            ShrineEffects.Add(FName(*Pair.Key),Pair.Value->AsNumber());
}

bool UDungeonRunSubsystem::IsShrine(const AActor* Actor) const
{return bActive&&IsValid(Actor)&&Actor==ShrineActor.Get()&&!ShrineBlessing.IsNone();}

FString UDungeonRunSubsystem::ShrinePrompt() const
{
    return ShrineName+(bShrineClaimed?TEXT(" · 已获赐福（本次地牢）"):TEXT(" · 祈求赐福\n")+ShrineDescription);
}

double UDungeonRunSubsystem::ShrineEffect(FName Key) const
{return bActive&&bShrineClaimed?ShrineEffects.FindRef(Key):0.;}

bool UDungeonRunSubsystem::ClaimShrine(APlayerController* Controller,AActor* Target)
{
    if(!IsShrine(Target)||!CanClaimShrine()||!Controller||Controller->GetNetMode()!=NM_Standalone
        ||ColdSteelWorldInteraction::TraceTarget(Controller)!=Target)return false;
    APawn* Pawn=Controller->GetPawn();
    auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    UColdSteelStatusModel* Model=StatusModel();
    if(!Model||!Health||Health->IsDead())return false;
    Model->SyncRuntime();auto Profile=Model->Snapshot();
    static const FName Receipt(TEXT("start_shrine"));
    if(Profile.DungeonRun.RunId!=CurrentRunId||Profile.DungeonRun.Claimed.Contains(Receipt))return false;
    Profile.DungeonRun.Claimed.Add(Receipt);
    Profile.Health=FMath::Min(Health->MaxHealth,float(Profile.Health+Health->MaxHealth*FMath::Clamp(ShrineHealFraction,0.,1.)));
    // The receipt and instant heal are committed together. A failed save never consumes the shrine.
    if(!Model->CommitState(MoveTemp(Profile)))return false;
    bShrineClaimed=true;ShrineRecipient=Pawn;
    UStatusEffectsComponent::Notify(Pawn);Model->NotifyChanged();
    return true;
}
