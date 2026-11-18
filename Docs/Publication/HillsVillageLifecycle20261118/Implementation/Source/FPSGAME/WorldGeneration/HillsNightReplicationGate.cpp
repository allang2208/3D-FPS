#include "HillsNightReplicationGate.h"
#include "HillsNightRaidSubsystem.h"
#include "../Monsters/NurseZombie.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

AHillsNightReplicationGate::AHillsNightReplicationGate()
{
    bReplicates=true;bOnlyRelevantToOwner=true;bNetLoadOnClient=false;
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.TickInterval=.1f;
}
void AHillsNightReplicationGate::BeginPlay()
{
    Super::BeginPlay();
    SetActorTickEnabled(GetNetMode()==NM_Client);
}
void AHillsNightReplicationGate::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const auto* PC=Cast<APlayerController>(GetOwner());
    const auto* Raid=GetWorld()->GetSubsystem<UHillsNightRaidSubsystem>();
    if(!PC||!PC->IsLocalController()||!Raid||!Raid->AreAssetsReady())return;
    ServerAssetsPrepared();SetActorTickEnabled(false);
}
void AHillsNightReplicationGate::ServerAssetsPrepared_Implementation()
{
    // RPC ownership ties this acknowledgement to this connection and this world.
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||PC->GetWorld()!=GetWorld()||!GetWorld()->GetSubsystem<UHillsNightRaidSubsystem>())return;
    bPrepared=true;
    UE_LOG(LogTemp,Display,TEXT("HILLS_RAID client resources acknowledged player=%s"),*PC->GetName());
}
void UHillsNightRaidSubsystem::UpdateReplicationGates()
{
    if(GetWorld()->GetNetMode()==NM_Standalone)return;
    for(auto It=ReplicationGates.CreateIterator();It;++It)
        if(!It.Key().IsValid()||It.Key()->IsActorBeingDestroyed())
        {if(It.Value().IsValid())It.Value()->Destroy();It.RemoveCurrent();}
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=It->Get();PC&&!PC->IsLocalController())
        {
            auto& Gate=ReplicationGates.FindOrAdd(PC);
            if(Gate.IsValid())continue;
            FActorSpawnParameters Params;Params.Owner=PC;Params.ObjectFlags|=RF_Transient;
            Gate=GetWorld()->SpawnActor<AHillsNightReplicationGate>(AHillsNightReplicationGate::StaticClass(),Params);
        }
}
bool UHillsNightRaidSubsystem::IsViewerPrepared(const AActor* Viewer) const
{
    if(!bEnabled)return true;
    const auto* PC=Cast<APlayerController>(Viewer);
    if(PC&&PC->IsLocalController())return true;
    const auto* Gate=ReplicationGates.Find(const_cast<APlayerController*>(PC));
    return Gate&&Gate->IsValid()&&Gate->Get()->IsPrepared();
}
bool ANurseZombie::IsNetRelevantFor(const AActor* RealViewer,const AActor* ViewTarget,const FVector& SrcLocation) const
{
    if(ActorHasTag(TEXT("HillsNightRaider")))
        if(const auto* Raid=GetWorld()->GetSubsystem<UHillsNightRaidSubsystem>();Raid&&!Raid->IsViewerPrepared(RealViewer))return false;
    return Super::IsNetRelevantFor(RealViewer,ViewTarget,SrcLocation);
}
