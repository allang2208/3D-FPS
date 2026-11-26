#include "DungeonRunSubsystem.h"
#include "RandomShrine.h"
#include "../WorldGeneration/ChapelShrine.h"
#include "DungeonRoomSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
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
#include "Kismet/GameplayStatics.h"

void UDungeonRunSubsystem::InitializeShrine()
{
    if(!ShrineConfig)return;
    const FName Tag(*ShrineConfig->GetStringField(TEXT("actor_tag")));
    for(TActorIterator<AActor> It(GetWorld());It;++It)
        if(It->ActorHasTag(Tag)){ShrineActor=*It;break;}
    if(!ShrineActor.IsValid())return;
    FRandomStream Random=GameplayStream(DungeonRunDomains::ShrineSelection);
    const auto Choice=RandomShrine::Choose(Random,ShrineConfig);
    auto* Component=ShrineActor->FindComponentByClass<UStaticMeshComponent>();
    if(!Component){ShrineActor.Reset();return;}
    Component->UnregisterComponent();
    if(!ApplyShrineChoice(Choice)){Component->RegisterComponent();ShrineActor.Reset();return;}
    // Imported FBX axes are per-asset data; the original +X assumption turned
    // the six -Y Blender fronts sideways after UE's Y reflection.
    double MeshFrontYaw=90.;
    Choice->TryGetNumberField(TEXT("front_local_yaw_deg"),MeshFrontYaw);
    const TArray<TSharedPtr<FJsonValue>>* Exit=nullptr;
    if(ShrineConfig->TryGetArrayField(TEXT("exit_target_cm"),Exit)&&Exit->Num()==3)
    {
        const FVector Target((*Exit)[0]->AsNumber(),(*Exit)[1]->AsNumber(),(*Exit)[2]->AsNumber());
        const FVector Outward=Target+(Generator.IsValid()?Generator->RuntimeOffset():FVector::ZeroVector)-ShrineActor->GetActorLocation();
        if(!Outward.IsNearlyZero())
            ShrineActor->SetActorRotation(FRotator(0.,Outward.Rotation().Yaw-MeshFrontYaw,0.));
    }
    Component->RegisterComponent();
}

bool UDungeonRunSubsystem::ApplyShrineChoice(const TSharedPtr<FJsonObject>& Choice)
{
    if(!Choice||!ShrineActor.IsValid())return false;
    UStaticMesh* Mesh=FindObject<UStaticMesh>(nullptr,*Choice->GetStringField(TEXT("mesh")));
    auto* Chapel=Cast<AChapelShrine>(ShrineActor.Get());
    auto* Component=Chapel?Chapel->GetStatueComponent():ShrineActor->FindComponentByClass<UStaticMeshComponent>();
    if(!Mesh||!Component)return false;
    const bool bRegistered=Component->IsRegistered();
    if(bRegistered)Component->UnregisterComponent();
    Component->SetStaticMesh(Mesh);
    Component->EmptyOverrideMaterials();
    Component->SetCanEverAffectNavigation(HillsShrineWorldId.IsValid());
    if(bRegistered)Component->RegisterComponent();
    ShrineEffects.Reset();ShrineHealFraction=0.;
    ShrineName=Choice->GetStringField(TEXT("name"));
    ShrineDescription=Choice->GetStringField(TEXT("description"));
    ShrineBlessing=FName(*Choice->GetStringField(TEXT("buff_id")));
    Choice->TryGetNumberField(TEXT("heal_fraction"),ShrineHealFraction);
    const TSharedPtr<FJsonObject>* Effects=nullptr;
    if(Choice->TryGetObjectField(TEXT("effects"),Effects))
        for(const auto& Pair:(*Effects)->Values)if(Pair.Value->Type==EJson::Number)
            ShrineEffects.Add(FName(*Pair.Key),Pair.Value->AsNumber());
    if(HillsShrineWorldId.IsValid())ShrineDescription.ReplaceInline(TEXT("本次地牢"),TEXT("当前丘陵世界"));
    return true;
}

bool UDungeonRunSubsystem::BindHillsShrine(AActor* Actor,FGuid WorldId,const TSharedPtr<FJsonObject>& Choice)
{
    if(bActive||!IsValid(Actor)||Actor->GetWorld()!=GetWorld()||!WorldId.IsValid())return false;
    HillsShrineWorldId=WorldId;ShrineActor=Actor;
    if(ApplyShrineChoice(Choice))return true;
    UnbindHillsShrine(Actor);return false;
}

void UDungeonRunSubsystem::UnbindHillsShrine(const AActor* Actor)
{
    if(!HillsShrineWorldId.IsValid()||ShrineActor.Get()!=Actor)return;
    HillsShrineWorldId.Invalidate();ShrineActor.Reset();ShrineEffects.Reset();ShrineBlessing=NAME_None;
}

FString UDungeonRunSubsystem::HillsShrineReceipt() const
{
    return TEXT("HillsShrine.")+HillsShrineWorldId.ToString(EGuidFormats::Digits);
}

bool UDungeonRunSubsystem::IsShrine(const AActor* Actor) const
{return (bActive||HillsShrineWorldId.IsValid())&&IsValid(Actor)&&Actor==ShrineActor.Get()&&!ShrineBlessing.IsNone();}

FString UDungeonRunSubsystem::ShrinePrompt() const
{
    if(const auto* Shrine=Cast<AChapelShrine>(ShrineActor.Get()))
    {
        if(Shrine->IsDormant())return ShrineName+TEXT(" · 赐福中断，黎明恢复");
        return ShrineName+FString::Printf(TEXT(" · 耐久 %.0f / %.0f\n"),Shrine->Durability,Shrine->MaxDurability)
            +(HasShrineBlessing()?TEXT("已获赐福（当前丘陵世界）"):TEXT("祈求赐福 · ")+ShrineDescription);
    }
    return ShrineName+(HasShrineBlessing()?TEXT(" · 已获赐福（")+ShrineLifetimeText()+TEXT("）"):TEXT(" · 祈求赐福\n")+ShrineDescription);
}

bool UDungeonRunSubsystem::ShrineAvailable() const
{
    const auto* Shrine=Cast<AChapelShrine>(ShrineActor.Get());
    return !Shrine||!Shrine->IsDormant();
}

bool UDungeonRunSubsystem::HasShrineBlessing(const APawn* Viewer) const
{
    if(HillsShrineWorldId.IsValid())
    {
        const auto* M=Viewer?ColdSteelAuthority::ForPawn(Viewer):StatusModel();
        return ShrineActor.IsValid()&&ShrineAvailable()&&M&&M->Snapshot().CampfireWorldReceipts.Contains(HillsShrineReceipt());
    }
    if(UDungeonRoomSubsystem::Supports(GetWorld()))
    {
        const APawn* LocalViewer=Viewer?Viewer:UGameplayStatics::GetPlayerPawn(GetWorld(),0);
        if(!UDungeonRoomSubsystem::IsDungeonPawn(LocalViewer))return false;
    }
    const auto* M=Viewer?ColdSteelAuthority::ForPawn(Viewer):StatusModel();
    return bActive&&M&&M->Snapshot().DungeonRun.RunId==CurrentRunId&&M->Snapshot().DungeonRun.Claimed.Contains(TEXT("start_shrine"));
}
double UDungeonRunSubsystem::ShrineEffect(FName Key,const APawn* Viewer) const
{return HasShrineBlessing(Viewer)?ShrineEffects.FindRef(Key):0.;}

bool UDungeonRunSubsystem::ClaimShrine(APlayerController* Controller,AActor* Target)
{
    if(!Controller||!IsShrine(Target)||!ShrineAvailable()||HasShrineBlessing(Controller->GetPawn())
        ||ColdSteelWorldInteraction::TraceTarget(Controller)!=Target)return false;
    if(Controller->GetNetMode()==NM_Client)
    {auto* PS=Controller->GetPlayerState<AColdSteelPlayerState>();return PS&&PS->RequestInventoryAction(EColdSteelInventoryAction::Shrine,FString(),Target);}
    APawn* Pawn=Controller->GetPawn();
    auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    UColdSteelStatusModel* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!Model||!Health||Health->IsDead())return false;
    Model->SyncRuntime();auto Profile=Model->Snapshot();
    if(HillsShrineWorldId.IsValid())
    {
        const FString Receipt=HillsShrineReceipt();
        if(Profile.CampfireWorldReceipts.Contains(Receipt))return false;
        auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
        if(!Controller->IsLocalController()&&!PS)return false;
        Profile.Health=FMath::Min(Health->MaxHealth,float(Profile.Health+Health->MaxHealth*FMath::Clamp(ShrineHealFraction,0.,1.)));
        // The existing transaction receipt survives travel/reconnect without touching DungeonRun.
        if(!Model->CommitCampfireState(MoveTemp(Profile),Receipt,Controller->IsLocalController()?FString():PS->CampfireGuestSlot()))return false;
        UStatusEffectsComponent::Notify(Pawn);Model->NotifyChanged();return true;
    }
    static const FName Receipt(TEXT("start_shrine"));
    if(Profile.DungeonRun.RunId!=CurrentRunId)
    {Profile.DungeonRun={};Profile.DungeonRun.RunId=CurrentRunId;Profile.DungeonRun.Seed=Seed;}
    if(Profile.DungeonRun.Claimed.Contains(Receipt))return false;
    Profile.DungeonRun.Claimed.Add(Receipt);
    Profile.Health=FMath::Min(Health->MaxHealth,float(Profile.Health+Health->MaxHealth*FMath::Clamp(ShrineHealFraction,0.,1.)));
    // The receipt and instant heal are committed together. A failed save never consumes the shrine.
    auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
    if(GetWorld()->GetNetMode()==NM_Standalone){if(!Model->CommitState(MoveTemp(Profile)))return false;}
    else if(!Model->CommitCampfireState(MoveTemp(Profile),TEXT("Shrine"),Controller->IsLocalController()?FString():PS->CampfireGuestSlot()))return false;
    bShrineClaimed=true;ShrineRecipient=Pawn;
    UStatusEffectsComponent::Notify(Pawn);Model->NotifyChanged();
    return true;
}
