#include "DungeonRoomSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonRunSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../SceneTestPortal.h"
#include "Engine/Level.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

ADungeonRoomState::ADungeonRoomState()
{
    bReplicates=true;bAlwaysRelevant=true;SetNetUpdateFrequency(2.f);
}
void ADungeonRoomState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(ADungeonRoomState,Instance);
}
void ADungeonRoomState::OnRep_Instance()
{
    if(auto* Room=UDungeonRoomSubsystem::Get(GetWorld()))Room->ApplyInstance(this);
}
UDungeonRoomSubsystem* UDungeonRoomSubsystem::Get(const UWorld* World)
{
    return Supports(World)?World->GetSubsystem<UDungeonRoomSubsystem>():nullptr;
}
bool UDungeonRoomSubsystem::Supports(const UWorld* World)
{
    return World&&World->IsGameWorld()&&World->GetNetMode()!=NM_Standalone
        &&UGameplayStatics::GetCurrentLevelName(World,true)==TEXT("DayNight_Lighting");
}
bool UDungeonRoomSubsystem::IsDungeonPawn(const APawn* Pawn)
{
    if(!Pawn)return false;
    if(Supports(Pawn->GetWorld()))
    {
        const auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
        return PS?PS->bInDungeonRoom:IsDungeonActor(Pawn);
    }
    return UGameplayStatics::GetCurrentLevelName(Pawn,true)==TEXT("L_Dungeon_Randomized");
}
bool UDungeonRoomSubsystem::IsDungeonActor(const AActor* Actor)
{
    if(!Actor)return false;
    if(!Supports(Actor->GetWorld()))return UGameplayStatics::GetCurrentLevelName(Actor,true)==TEXT("L_Dungeon_Randomized");
    // The package predicate works during streamed actors' BeginPlay, before GetLoadedLevel is published.
    const auto* Level=Actor->GetLevel();
    return Level&&Level!=Actor->GetWorld()->PersistentLevel
        &&Level->GetOutermost()->GetName().Contains(TEXT("SessionDungeon_"));
}
FString UDungeonRoomSubsystem::LogicalMap(const AActor* Actor)
{
    return (Cast<APawn>(Actor)?IsDungeonPawn(Cast<APawn>(Actor)):IsDungeonActor(Actor))?TEXT("L_Dungeon_Randomized"):UGameplayStatics::GetCurrentLevelName(Actor,true);
}
FString UDungeonRoomSubsystem::SceneActorKey(const AActor* Actor)
{
    if(!Actor)return FString();
    if(Supports(Actor->GetWorld())&&IsDungeonActor(Actor))
        return UWorld::RemovePIEPrefix(Actor->GetLevel()->GetOutermost()->GetName())+TEXT(":")+Actor->GetName();
    return Actor->GetName();
}
bool UDungeonRoomSubsystem::IsTickable() const
{
    return !IsTemplate()&&Supports(GetWorld())&&Super::IsTickable();
}
TStatId UDungeonRoomSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(DungeonRoom,STATGROUP_Tickables); }
bool UDungeonRoomSubsystem::HasInstance() const { return RoomState&&RoomState->Instance.IsValid(); }
bool UDungeonRoomSubsystem::HasOccupants() const
{
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(const auto* PC=It->Get())if(const auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();PS&&PS->bInDungeonRoom)return true;
    return false;
}
void UDungeonRoomSubsystem::ApplyInstance(ADungeonRoomState* State)
{
    if(!Supports(GetWorld())||!State)return;
    RoomState=State;
    if(LoadedInstance==State->Instance)return;
    if(Streaming)
    {
        Streaming->SetShouldBeVisible(false);Streaming->SetShouldBeLoaded(false);
        Streaming->SetIsRequestingUnloadAndRemoval(true);Retiring.Add(Streaming);Streaming=nullptr;
    }
    LoadedInstance=State->Instance;bLoadFailed=false;
    if(!LoadedInstance.IsValid())return;
    bool Loaded=false;
    Streaming=ULevelStreamingDynamic::LoadLevelInstance(this,TEXT("/Game/GameMaps/L_Dungeon_Randomized"),
        DungeonOffset(),FRotator::ZeroRotator,Loaded,TEXT("SessionDungeon_")+LoadedInstance.ToString(EGuidFormats::Digits));
    bLoadFailed=!Loaded||!Streaming;
}
AAuthoredDungeonGenerator* UDungeonRoomSubsystem::Generator() const
{
    if(!Streaming||!Streaming->GetLoadedLevel())return nullptr;
    for(AActor* Actor:Streaming->GetLoadedLevel()->Actors)
        if(auto* G=Cast<AAuthoredDungeonGenerator>(Actor))return G;
    return nullptr;
}
bool UDungeonRoomSubsystem::LocalAssemblyReady(FGuid Instance) const
{
    auto* G=Generator();
    return Instance.IsValid()&&Instance==LoadedInstance&&Streaming&&Streaming->IsLevelVisible()
        &&G&&G->ActorHasTag(TEXT("DungeonAssembly.Ready"));
}
bool UDungeonRoomSubsystem::QueueEntry(const TArray<AColdSteelPlayerState*>& Players,FString& Reason)
{
    if(GetWorld()->GetNetMode()==NM_Client||Players.IsEmpty())return false;
    if(HasInstance()&&!HasOccupants()&&Pending.IsEmpty())
    {
        ReleaseInstance();
        if(HasInstance()){Reason=TEXT("上一轮地牢库存清理尚未保存，请稍后重试");return false;}
    }
    Retiring.RemoveAll([](const auto& Level){return !Level.IsValid()||Level->GetLevelStreamingState()==ELevelStreamingState::Removed;});
    if(!Retiring.IsEmpty()){Reason=TEXT("上一轮地牢正在释放，请稍后再次出征");return false;}
    if(!RoomState)
    {
        FActorSpawnParameters Params;Params.OverrideLevel=GetWorld()->PersistentLevel;
        RoomState=GetWorld()->SpawnActor<ADungeonRoomState>(ADungeonRoomState::StaticClass(),FTransform::Identity,Params);
    }
    if(!RoomState){Reason=TEXT("无法建立地牢区域");return false;}
    for(auto* PS:Players)
    {
        if(!PS||!PS->GetPawn()||PS->bInDungeonRoom||PS->RoomTransferToken.IsValid())
        {Reason=TEXT("出征角色已变化，请重新发起");return false;}
    }
    if(!RoomState->Instance.IsValid())RoomState->Instance=FGuid::NewGuid();
    for(auto* PS:Players)
    {
        FEntry Entry;Entry.Player=PS;Entry.Pawn=PS->GetPawn();Entry.Token=FGuid::NewGuid();Entry.Started=GetWorld()->GetRealTimeSeconds();
        Pending.Add(Entry);PS->RoomTransferToken=Entry.Token;
        ReturnPositions.Add(PS,PS->GetPawn()->GetActorTransform());
        PS->ClientBeginRoomEntry(Entry.Token,RoomState->Instance,PS->GetPawn());
    }
    RoomState->ForceNetUpdate();ApplyInstance(RoomState);return true;
}
void UDungeonRoomSubsystem::AcknowledgeEntry(AColdSteelPlayerState* Player,FGuid Token,FGuid Instance,APawn* Pawn)
{
    if(GetWorld()->GetNetMode()==NM_Client||!RoomState||Instance!=RoomState->Instance)return;
    for(auto& Entry:Pending)if(Entry.Player==Player&&Entry.Token==Token&&Entry.Pawn==Pawn&&Player->GetPawn()==Pawn)Entry.Ready=true;
}
void UDungeonRoomSubsystem::CancelEntry(AColdSteelPlayerState* Player,FGuid Token)
{
    if(GetWorld()->GetNetMode()==NM_Client)return;
    for(int32 I=Pending.Num()-1;I>=0;--I)if(Pending[I].Player==Player&&Pending[I].Token==Token)
        FinishEntry(I,TEXT("已取消出征，你仍在主神空间"));
}
bool UDungeonRoomSubsystem::FindSpawn(bool Dungeon,APawn* Pawn,FTransform& Out) const
{
    for(TActorIterator<APlayerStart> It(GetWorld());It;++It)
    {
        if(IsDungeonActor(*It)!=Dungeon)continue;
        FVector Point=It->GetActorLocation();const FRotator Facing=It->GetActorRotation();
        if(!Pawn||GetWorld()->FindTeleportSpot(Pawn,Point,Facing)){Out=FTransform(Facing,Point);return true;}
    }
    return false;
}
bool UDungeonRoomSubsystem::MovePlayer(AColdSteelPlayerState* PS,const FTransform& Destination)
{
    auto* Pawn=PS?PS->GetPawn():nullptr;
    auto* PC=PS?Cast<APlayerController>(PS->GetOwner()):nullptr;
    if(!Pawn||!PC||!Pawn->TeleportTo(Destination.GetLocation(),Destination.Rotator()))return false;
    if(auto* Character=Cast<ACharacter>(Pawn))Character->GetCharacterMovement()->StopMovementImmediately();
    PC->SetControlRotation(Destination.Rotator());PC->ClientSetLocation(Pawn->GetActorLocation(),Destination.Rotator());
    Pawn->ForceNetUpdate();return true;
}
void UDungeonRoomSubsystem::FinishEntry(int32 Index,const FString& Reason)
{
    const FEntry Entry=Pending[Index];Pending.RemoveAt(Index);
    if(auto* PS=Entry.Player.Get())
    {
        PS->RoomTransferToken.Invalidate();
        PS->ClientFinishRoomEntry(Entry.Token,PS->bInDungeonRoom,Reason);
    }
}
bool UDungeonRoomSubsystem::ReturnPlayer(AColdSteelPlayerState* PS,AActor* Entrance,bool Confirm,FString& Reason)
{
    auto* Portal=Cast<ASceneTestPortal>(Entrance);
    if(GetWorld()->GetNetMode()==NM_Client||!PS||!PS->bInDungeonRoom||!Portal
        ||!IsDungeonActor(Portal)||!Portal->IsWithinInteractionRange(PS->GetPawn()))
    {Reason=TEXT("请靠近地牢返程入口重试");return false;}
    auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    const bool Final=Portal->ActorHasTag(TEXT("DungeonFinalReturn"));
    if(Final&&(!Run||!Run->CanUseFinalReturn())){Reason=TEXT("尚未击败最终首领");return false;}
    if(Final&&!PS->bClaimedFinalDungeonTreasure&&!Confirm){Reason=TEXT("你尚未领取奖励，请确认后离开");return false;}
    auto* Model=ColdSteelAuthority::ForPawn(PS->GetPawn());
    if(!Model){Reason=TEXT("个人档案尚未就绪");return false;}
    const FTransform Previous=PS->GetPawn()->GetActorTransform();
    FTransform Target;bool Found=false;
    if(const auto* Saved=ReturnPositions.Find(PS))
    {
        FVector Point=Saved->GetLocation();
        if(GetWorld()->FindTeleportSpot(PS->GetPawn(),Point,Saved->Rotator())){Target=FTransform(Saved->Rotator(),Point);Found=true;}
    }
    if(!Found)Found=FindSpawn(false,PS->GetPawn(),Target);
    if(!Found||!MovePlayer(PS,Target)){Reason=TEXT("主神空间落点暂时被占用，请稍后重试");return false;}
    const bool WasCompleted=Model->Snapshot().DungeonRun.bCompleted;
    auto* ReturnPC=Cast<APlayerController>(PS->GetOwner());
    if(Final&&(!Run->CompletePlayerReturn(Model)||(!(ReturnPC&&ReturnPC->IsLocalController())&&!PS->SaveShadowToHostDisk())))
    {
        auto Restored=Model->Snapshot();Restored.DungeonRun.bCompleted=WasCompleted;Model->CommitState(MoveTemp(Restored));
        if(ReturnPC&&!ReturnPC->IsLocalController())PS->SaveShadowToHostDisk();
        PS->GetPawn()->TeleportTo(Previous.GetLocation(),Previous.Rotator(),false,true);
        if(ReturnPC)ReturnPC->ClientSetLocation(Previous.GetLocation(),Previous.Rotator());
        Reason=TEXT("个人通关记录保存失败，已保留在地牢");return false;
    }
    PS->bInDungeonRoom=false;PS->ForceNetUpdate();PS->ClientRoomRegionChanged(false);
    if(!HasOccupants()&&Pending.IsEmpty())ReleaseInstance();
    return true;
}
void UDungeonRoomSubsystem::ReleaseInstance()
{
    if(!RoomState||!RoomState->Instance.IsValid())return;
    if(GetWorld()->GetRealTimeSeconds()<RetireRetryAt)return;
    RetireRetryAt=GetWorld()->GetRealTimeSeconds()+5.;
    const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();
        Shared&&!Shared->RetireDungeonInventory(Run&&Run->IsRunActive()?Run->RunId():FString()))return;
    RoomState->Instance.Invalidate();RoomState->ForceNetUpdate();ApplyInstance(RoomState);
    ReturnPositions.Reset();
}
void UDungeonRoomSubsystem::Tick(float DeltaTime)
{
    Accumulator+=DeltaTime;if(Accumulator<.1f)return;Accumulator=0.f;
    RefreshPresentation();
    if(GetWorld()->GetNetMode()==NM_Client)return;
    auto* G=Generator();
    const bool Failed=bLoadFailed||(G&&G->ActorHasTag(TEXT("DungeonAssembly.Failed")));
    for(int32 I=Pending.Num()-1;I>=0;--I)
    {
        const FEntry Entry=Pending[I];auto* PS=Entry.Player.Get();auto* Pawn=Entry.Pawn.Get();
        const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(!PS||!Cast<APlayerController>(PS->GetOwner())||!Pawn||Pawn!=PS->GetPawn()||!Health||Health->IsDead())
        {FinishEntry(I,TEXT("角色已变化或正在重生，出征已取消"));continue;}
        if(Failed||GetWorld()->GetRealTimeSeconds()-Entry.Started>240.)
        {FinishEntry(I,Failed?TEXT("地牢准备失败，你仍在主神空间"):TEXT("地牢准备超时，请重新出征"));continue;}
        if(!Entry.Ready||!LocalAssemblyReady(LoadedInstance))continue;
        FTransform Spawn;
        if(!FindSpawn(true,Pawn,Spawn)){FinishEntry(I,TEXT("地牢入口暂时没有安全落点"));continue;}
        auto* Run=UDungeonRunSubsystem::Get(GetWorld());auto* Model=ColdSteelAuthority::ForPawn(Pawn);
        if(!Run||!Model){FinishEntry(I,TEXT("个人档案尚未就绪"));continue;}
        if(PS->InventoryRequestPending())continue;
        if(Model->HasUnconfirmedTransactionSave())
        {FinishEntry(I,TEXT("物品交易保存尚待恢复，出征已取消"));continue;}
        PS->bInDungeonRoom=true;
        Run->EnsurePlayerRun(Model);
        const auto* PC=Cast<APlayerController>(PS->GetOwner());
        if(Model->Snapshot().DungeonRun.RunId!=Run->RunId()||(!(PC&&PC->IsLocalController())&&!PS->SaveShadowToHostDisk()))
        {PS->bInDungeonRoom=false;FinishEntry(I,TEXT("个人地牢记录保存失败"));continue;}
        if(!MovePlayer(PS,Spawn)){PS->bInDungeonRoom=false;FinishEntry(I,TEXT("地牢入口被占用，请重新出征"));continue;}
        PS->bInDungeonRoom=true;
        PS->bClaimedFinalDungeonTreasure=Model->Snapshot().DungeonRun.Claimed.Contains(TEXT("FinalTreasure.Taken"));
        PS->ForceNetUpdate();FinishEntry(I,FString());
    }
    if(Pending.IsEmpty()&&!HasOccupants())ReleaseInstance();
}
void UDungeonRoomSubsystem::Deinitialize()
{
    RestoreEnvironment();Pending.Reset();ReturnPositions.Reset();Super::Deinitialize();
}
