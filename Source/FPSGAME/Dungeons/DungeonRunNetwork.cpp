#include "DungeonRunSubsystem.h"
#include "WardBreakableGlass.h"
#include "../UI/ColdSteelSceneContainer.h"
#include "../Multiplayer/ColdSteelSharedChestVisual.h"
#include "../Building/ColdSteelDoor.h"
#include "AuthoredDungeonGenerator.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelWorldSnapshot.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "UObject/Package.h"
#include "EngineUtils.h"

namespace
{
FString SharedSceneKey(const AActor* Actor)
{
    // Actor names are only unique within a level. Preserve the sublevel/instance
    // package, while removing each PIE world's different package prefix. The
    // persistent level is already identified by the enclosing snapshot's Map.
    if(Actor->GetLevel()==Actor->GetWorld()->PersistentLevel)return Actor->GetName();
    return UWorld::RemovePIEPrefix(Actor->GetLevel()->GetOutermost()->GetName())
        +TEXT(":")+Actor->GetName();
}
}

void UDungeonRunSubsystem::PublishSharedProgress()
{
    if(!bActive||!GetWorld()||GetWorld()->GetNetMode()==NM_Client||!Generator.IsValid()
        ||Generator->NetworkRunId!=CurrentRunId)return;
    auto& State=Generator->SharedProgress;
    const uint32 NextRevision=State.RunId==CurrentRunId?State.Revision+1:1;
    State.RunId=CurrentRunId;State.Revision=NextRevision;
    State.bWelcomeEliteDefeated=IsWelcomeEliteDefeated();State.bCompleted=bCompleted;
    State.bMedicalBossDefeated=IsMedicalBossDefeated();
    State.bFreightBossDefeated=IsFreightBossDefeated();
    State.bEcologyBossDefeated=IsEcologyBossDefeated();
    State.bPowerBossDefeated=IsPowerBossDefeated();
    State.bIncinerationBossDefeated=IsIncinerationBossDefeated();
    State.bStaffLivingBossDefeated=IsStaffLivingBossDefeated();
    State.bFinalBossDefeated=IsFinalBossDefeated();State.bFinalTreasureLooted=bFinalTreasureLooted;
    State.Cleared=Cleared.Array();State.Explored=Explored.Array();
    State.Cleared.Sort(FNameLexicalLess());State.Explored.Sort(FNameLexicalLess());
    Generator->ForceNetUpdate();
}

void UDungeonRunSubsystem::ApplySharedProgress(const FDungeonSharedProgress& State)
{
    if(!GetWorld()||GetWorld()->GetNetMode()!=NM_Client||!bActive||!Generator.IsValid()
        ||!SharedProgressMirror.ApplyNewer(State,CurrentRunId))return;
    Cleared.Reset();Explored.Reset();
    for(const FName Key:State.Cleared)Cleared.Add(Key);
    for(const FName Key:State.Explored)Explored.Add(Key);
    bCompleted=State.bCompleted;bNetworkEliteDefeated=State.bWelcomeEliteDefeated;
    bNetworkMedicalBossDefeated=State.bMedicalBossDefeated;
    bNetworkFreightBossDefeated=State.bFreightBossDefeated;
    bNetworkEcologyBossDefeated=State.bEcologyBossDefeated;
    bNetworkPowerBossDefeated=State.bPowerBossDefeated;
    bNetworkIncinerationBossDefeated=State.bIncinerationBossDefeated;
    bNetworkStaffLivingBossDefeated=State.bStaffLivingBossDefeated;
    bNetworkFinalBossDefeated=State.bFinalBossDefeated;bFinalTreasureLooted=State.bFinalTreasureLooted;
    // This is a read-only client mirror. Do not save, grant rewards, or open local gates here.
}

void UDungeonRunSubsystem::FillNetworkState(UColdSteelWorldSnapshot* Out) const
{
    if (!Out) return;
    Out->RunId.Reset();
    Out->Cleared.Reset();
    Out->Explored.Reset();
    Out->bCompleted = false;
    if (!GetWorld() || GetWorld()->GetNetMode() == NM_Client) return;
    // Shared scene visuals also exist in the hub and authored maps. A dungeon
    // run scopes generated names, but must not gate late-join chest/door state.

    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        const FString Key=SharedSceneKey(*It);
        if(auto* Container=Cast<AColdSteelSceneContainer>(*It);Container&&Container->bSearched)Out->OpenedContainers.Add(Key);
        if(It->ActorHasTag(TEXT("DungeonTreasure.Opened")))Out->OpenedChests.Add(Key);
        if(auto* Glass=It->FindComponentByClass<UWardBreakableGlass>();Glass&&Glass->bBroken)Out->BrokenGlass.Add(Key);
        if(auto* Door=Cast<AColdSteelDoor>(*It);Door&&!Door->GetIsReplicated())Out->DoorSwings.Add(Key,Door->NetworkSwing());
        // Generated service-door poses travel on their encounter actor. The
        // slower scene snapshot must not overwrite a newer open/close motion.
    }
    if(bActive)Out->RunId = CurrentRunId;
    // Task progress travels on the generator's small replicated state, not this bulk transfer.
}

bool UDungeonRunSubsystem::ApplyNetworkState(UColdSteelWorldSnapshot* State)
{
    if (!State || !GetWorld() || GetWorld()->GetNetMode() != NM_Client)return false;
    if(!State->RunId.IsEmpty()&&(!bActive||CurrentRunId.IsEmpty()||State->RunId!=CurrentRunId))return false;
    const auto Complete=[State]()
    {
        return State->OpenedContainers.IsEmpty()&&State->OpenedChests.IsEmpty()
            &&State->BrokenGlass.IsEmpty()&&State->SceneTransforms.IsEmpty()&&State->DoorSwings.IsEmpty();
    };
    if(Complete())return true;

    // Apply presentation only. MarkRoomCleared/CommitProfileRunState can grant
    // rewards and save; those authority operations do not belong in this mirror.
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        const FString Name=SharedSceneKey(*It);
        if(State->OpenedContainers.Contains(Name))
            if(auto* Container=Cast<AColdSteelSceneContainer>(*It))
            {Container->OpenSharedVisual(true);State->OpenedContainers.Remove(Name);}
        if(State->OpenedChests.Contains(Name))
            if(It->ActorHasTag(TEXT("DungeonTreasure.Opened"))||ColdSteelSharedChest::Open(*It,true))State->OpenedChests.Remove(Name);
        if(const auto* Transform=State->SceneTransforms.Find(Name))
        {It->SetActorTransform(*Transform);State->SceneTransforms.Remove(Name);}
        if(auto* Door=Cast<AColdSteelDoor>(*It))if(const auto* Swing=State->DoorSwings.Find(Name))
        {Door->ApplyNetworkSwing(*Swing);State->DoorSwings.Remove(Name);}
        if(State->BrokenGlass.Contains(Name))
            if(auto* G=It->FindComponentByClass<UWardBreakableGlass>())
            {
                if(!G->bBroken){G->bBroken=true;G->SetCollisionEnabled(ECollisionEnabled::NoCollision);G->SetVisibility(false,true);}
                State->BrokenGlass.Remove(Name);
            }
    }
    // An actor channel or streamed level can arrive after this reliable snapshot.
    // Only unresolved entries remain. Waiting for one late actor must not replay
    // old transforms or animations on actors which have already caught up.
    // Delayed scene snapshots must never roll newer team objective progress backwards.
    return Complete();
}

void UDungeonRunSubsystem::EnsurePlayerRun(UColdSteelStatusModel* M)
{
    if(!bActive||!M||GetWorld()->GetNetMode()==NM_Client)return;
    if(M->Snapshot().DungeonRun.RunId!=CurrentRunId)
    {
        M->SyncRuntime();auto P=M->Snapshot();P.DungeonRun={};auto& R=P.DungeonRun;
        R.RunId=CurrentRunId;R.Seed=Seed;R.GeneratorVersion=5;
        if(Generator.IsValid())R.LayoutManifestJson=Generator->LayoutManifestJson;
        if(!M->CommitState(MoveTemp(P)))return;
    }
    SyncPlayerRun(M);
}
