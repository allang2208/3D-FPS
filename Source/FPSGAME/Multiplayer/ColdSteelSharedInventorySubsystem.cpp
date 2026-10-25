#include "ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../FPSGAMECharacter.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "EngineUtils.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Crc.h"
#include "HAL/IConsoleManager.h"
using namespace ColdSteelInventory;

namespace
{
bool UsesChangedSharedFootprint(const FColdSteelItem& Item)
{
    return Item.Definition==TEXT("alchemy_compound_stabilizer")||Item.Definition==TEXT("ue_tactical_magazine_belt")
        ||Item.Definition==TEXT("ue_melee_combat_belt")||Item.Definition==TEXT("ue_arcane_conduit_belt");
}
}

bool UColdSteelSharedInventorySubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
    const auto* World=Cast<UWorld>(Outer);
    return World&&World->IsGameWorld();
}
void UColdSteelSharedInventorySubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if(World.GetNetMode()!=NM_Standalone&&World.GetNetMode()!=NM_Client)InitializeAuthority();
}
bool UColdSteelSharedInventorySubsystem::InitializeAuthority()
{
    if(GetWorld()->GetNetMode()==NM_Client||GetWorld()->GetNetMode()==NM_Standalone)return false;
    if(bInitialized)return !bBlocked;
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    FString RunKey;
    if(Map==TEXT("L_Dungeon_Randomized"))
    {
        const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
        if(!Run||!Run->IsRunActive())return false;
        RunKey=Run->RunId();
    }
    if(Map==TEXT("L_TemperateHills_Initial"))
    {ATemperateHillsWorld* Hills=nullptr;for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
     if(!Hills||!Hills->WorldId.IsValid())return false;RunKey=Hills->WorldId.ToString(EGuidFormats::Digits);}
    bInitialized=true;
    auto* Host=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Host){bBlocked=true;return false;}
    SaveSlot=FString::Printf(TEXT("%s_Shared_%08x"),*Host->ProfileSlot(),FCrc::StrCrc32(*(Map+RunKey)));
    if(UGameplayStatics::DoesSaveGameExist(SaveSlot,0))
    {
        const auto* Save=Cast<UColdSteelSharedInventorySave>(UGameplayStatics::LoadGameFromSlot(SaveSlot,0));
        if(!Save||Save->Version!=1){bBlocked=true;return false;}
        Current=Save->Data;
    }
    const FString JournalSlot=SaveSlot+TEXT("_Transaction");
    if(UGameplayStatics::DoesSaveGameExist(JournalSlot,0))
    {
        const auto* Journal=Cast<UColdSteelSharedInventoryJournal>(UGameplayStatics::LoadGameFromSlot(JournalSlot,0));
        if(!Journal){bBlocked=true;return false;}
        int64 Committed=-1;
        if(Journal->bGuest)
        {
            if(!UGameplayStatics::DoesSaveGameExist(Journal->PlayerSlot,0))Committed=0;
            if(const auto* Player=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(Journal->PlayerSlot,0)))
                Committed=Player->Profile.CampfireWorldReceipts.FindRef(SaveSlot);
        }
        else if(Journal->PlayerSlot==Host->ProfileSlot())Committed=Host->Snapshot().CampfireWorldReceipts.FindRef(SaveSlot);
        if(Committed<0||Committed>Journal->InventoryRevision){bBlocked=true;return false;}
        if(Committed==Journal->InventoryRevision)
        {
            Current=Journal->After;
            if(!SaveWorld(Current)){bBlocked=true;return false;}
        }
        if(!UGameplayStatics::DeleteGameInSlot(JournalSlot,0)){bBlocked=true;return false;}
    }
    // Recover transactions first, then migrate the authoritative world snapshot
    // before spawning replicated pickup actors. No player inventory is changed here.
    auto Migrated=Current;bool DropsChanged=false;FString MigrationReason;
    for(auto& Item:Migrated.Drops)
    {
        if(!UsesChangedSharedFootprint(Item))continue;
        bool ItemChanged=false;
        if(!MigrateAuthoredItemFootprint(Item,ItemChanged,MigrationReason))
        {UE_LOG(LogTemp,Warning,TEXT("Shared drop migration failed: %s"),*MigrationReason);bBlocked=true;return false;}
        DropsChanged|=ItemChanged;
    }
    if(DropsChanged)
    {
        if(!SaveWorld(Migrated)){bBlocked=true;return false;}
        Current=MoveTemp(Migrated);
    }
    RefreshDropActors();
    return true;
}
bool UColdSteelSharedInventorySubsystem::SaveWorld(const FColdSteelSharedInventoryData& Data)
{
    auto* Save=NewObject<UColdSteelSharedInventorySave>();Save->Data=Data;
    return UGameplayStatics::SaveGameToSlot(Save,SaveSlot,0);
}
void UColdSteelSharedInventorySubsystem::CaptureDropTransforms()
{
    for(auto& Item:Current.Drops)
        if(const auto* Actor=DropActors.Find(Item.InstanceId);Actor&&Actor->IsValid())
        {Item.Position=Actor->Get()->GetActorLocation();Item.WorldRotation=Actor->Get()->GetActorRotation();}
}
void UColdSteelSharedInventorySubsystem::RefreshDropActors()
{
    for(auto It=DropActors.CreateIterator();It;++It)
    {
        if(!Current.Drops.ContainsByPredicate([&](const auto& I){return I.InstanceId==It.Key();}))
        {if(It.Value().IsValid())It.Value()->Destroy();It.RemoveCurrent();}
    }
    for(const auto& Item:Current.Drops)
    {
        if(const auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();Harvest&&!Harvest->IsDropReady(Item.InstanceId))continue;
        if(const auto* Existing=DropActors.Find(Item.InstanceId);Existing&&Existing->IsValid())continue;
        FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if(auto* Actor=GetWorld()->SpawnActor<AColdSteelPickup>(Item.Position,Item.WorldRotation,Spawn))
        {Actor->InitializeSharedItem(Item);DropActors.Add(Item.InstanceId,Actor);}
    }
}
bool UColdSteelSharedInventorySubsystem::Commit(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,
    FColdSteelProfile Profile,FColdSteelSharedInventoryData After,FString& Reason)
{
    if(!InitializeAuthority()||bCommitting||!Model||Model->HasUnconfirmedTransactionSave()||!Model->RuntimePawn()||!Model->RuntimePawn()->HasAuthority())
    {Reason=TEXT("共享库存尚未就绪或保存待恢复");return false;}
    TGuardValue<bool> Guard(bCommitting,true);
    const FString PlayerSlot=Guest?Guest->CampfireGuestSlot():Model->ProfileSlot();
    if(PlayerSlot.IsEmpty()||Profile.CampfireInventoryRevision==MAX_int64)return false;
    auto* Journal=NewObject<UColdSteelSharedInventoryJournal>();
    Journal->PlayerSlot=PlayerSlot;Journal->bGuest=Guest!=nullptr;
    Journal->InventoryRevision=Profile.CampfireInventoryRevision+1;Journal->After=After;
    const FString JournalSlot=SaveSlot+TEXT("_Transaction");
    if(!UGameplayStatics::SaveGameToSlot(Journal,JournalSlot,0))
    {Reason=TEXT("交易日志保存失败，物品未移动");return false;}
    if(!Model->CommitCampfireState(MoveTemp(Profile),SaveSlot,Guest?PlayerSlot:FString()))
    {
        // A failed write may have reached disk. Keep the journal for recovery.
        bBlocked=true;
        Reason=Model->ResultMessage();return false;
    }
    Current=MoveTemp(After);
    bBlocked=!SaveWorld(Current)||!UGameplayStatics::DeleteGameInSlot(JournalSlot,0);
    RefreshDropActors();
    if(bBlocked)Reason=TEXT("物品已记账，共享世界保存待恢复");
    return true;
}
bool UColdSteelSharedInventorySubsystem::ImportPlayerDrops(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest)
{
    if(!Model||bCommitting||!InitializeAuthority())return false;
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    Model->SyncRuntime();auto Profile=Model->Snapshot();
    CaptureDropTransforms();auto After=Current;
    for(int32 I=Profile.Items.Num()-1;I>=0;--I)
    {
        auto Item=Profile.Items[I];
        if(Item.Place!=2||Item.Map!=Map||Item.HarvestWorldId.IsValid())continue;
        Item.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        After.Drops.Add(MoveTemp(Item));Profile.Items.RemoveAt(I);
    }
    if(After.Drops.Num()==Current.Drops.Num())return true;
    FString Reason;return Commit(Model,Guest,MoveTemp(Profile),MoveTemp(After),Reason);
}
bool UColdSteelSharedInventorySubsystem::Drop(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,const FString& Id,FString& Reason)
{
    if(!Model||!Model->RuntimePawn()||!InitializeAuthority())return false;
    Model->SyncRuntime();auto Profile=Model->Snapshot();
    const int32 Index=Profile.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});
    if(Index<0)return false;
    auto Item=Profile.Items[Index];
    if(Item.Place!=0&&Item.Place!=1&&Item.Place!=ColdSteelCompartment::Place)
    {Reason=TEXT("请先将物品取入背包");return false;}
    if(Item.Place==1&&Item.Cell==14)
        for(const auto& Other:Profile.Items)
            if(Other.Place==ColdSteelCompartment::Place||(Other.Place==0&&Other.Cell+(Other.Height-1)*18+Other.Width-1>=4*18))
            {Reason=TEXT("请先清空夹层和扩展背包格");return false;}
    auto* Pawn=Model->RuntimePawn();const FVector Origin=Pawn->GetActorLocation();
    FVector Candidate=Origin+Pawn->GetActorForwardVector()*120.f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SharedDrop),false,Pawn);
    FHitResult Obstacle,Ground;
    if(GetWorld()->SweepSingleByChannel(Obstacle,Origin,Candidate,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(45.f),Query))
        Candidate=Obstacle.Location-Pawn->GetActorForwardVector()*2.f;
    const auto FindGround=[&](FVector At)
    {return GetWorld()->LineTraceSingleByChannel(Ground,At+FVector(0,0,40),At-FVector(0,0,500),ECC_Visibility,Query)
        &&Ground.ImpactNormal.Z>=.5f&&FVector::Dist(Origin,Ground.ImpactPoint)<=230.f;};
    if(!FindGround(Candidate)&&!FindGround(Origin)){Reason=TEXT("附近没有可放置物品的地面");return false;}
    Profile.Items.RemoveAt(Index);
    Item.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);Item.Place=2;Item.Container.Reset();
    Item.Map=UGameplayStatics::GetCurrentLevelName(this,true);Item.Position=Ground.ImpactPoint;
    Item.Position.Z=FMath::Max(Ground.ImpactPoint.Z+60.f,Origin.Z+15.f);
    Item.WorldRotation=FRotator(5,Pawn->GetActorRotation().Yaw,-65);
    Model->StampProductionDrop(Item);
    // Shared drops are owned by this world journal, not the private harvest streamer.
    Item.HarvestWorldId.Invalidate();
    CaptureDropTransforms();auto After=Current;After.Drops.Add(Item);
    Reason=TEXT("已丢弃物品");return Commit(Model,Guest,MoveTemp(Profile),MoveTemp(After),Reason);
}
bool UColdSteelSharedInventorySubsystem::Pickup(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,AColdSteelPickup* Actor,bool Nearby,FString& Reason)
{
    if(!Model||!Model->RuntimePawn()||!InitializeAuthority()||!IsValid(Actor)||!Actor->IsSharedPickup())return false;
    auto* Pawn=Model->RuntimePawn();
    const auto* Registered=DropActors.Find(Actor->ItemId);
    if(!Registered||Registered->Get()!=Actor)return false;
    if(!Nearby&&!Actor->CanInteract(Pawn)){Reason=TEXT("物品不可达");return false;}
    if(Nearby&&!ColdSteelWorldInteraction::CanReachPickup(GetWorld(),Pawn,Actor,Actor->GetActorLocation()))return false;
    Model->SyncRuntime();auto Profile=Model->Snapshot();CaptureDropTransforms();auto After=Current;
    const int32 Index=After.Drops.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Actor->ItemId;});
    if(Index<0)return false;
    auto Item=After.Drops[Index];bool FootprintChanged=false;
    if(UsesChangedSharedFootprint(Item)&&!MigrateAuthoredItemFootprint(Item,FootprintChanged,Reason))return false;
    const bool Added=Model->AmmoType(Item.Definition)?Model->AddAmmoToState(Profile,Item.Definition,Item.Count)
        :ColdSteelInventory::Insert(Profile.Items,Item);
    if(!Added){Reason=TEXT("背包已满，物品留在地面");return false;}
    After.Drops.RemoveAt(Index);Reason=TEXT("已拾取物品");
    return Commit(Model,Guest,MoveTemp(Profile),MoveTemp(After),Reason);
}
bool UColdSteelSharedInventorySubsystem::PickupNearby(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,FString& Reason)
{
    if(!Model||!Model->RuntimePawn()||!InitializeAuthority())return false;
    const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Pickup.AreaRadiusCm"));
    const float Radius=Setting?Setting->GetFloat():500.f;
    auto* Pawn=Model->RuntimePawn();Model->SyncRuntime();auto Profile=Model->Snapshot();
    CaptureDropTransforms();auto After=Current;int32 Taken=0;
    for(int32 Index=After.Drops.Num()-1;Index>=0;--Index)
    {
        auto Item=After.Drops[Index];
        const auto* Actor=DropActors.Find(Item.InstanceId);
        if(!Actor||!Actor->IsValid()||FVector::DistSquared(Pawn->GetActorLocation(),Item.Position)>FMath::Square(FMath::Max(25.f,Radius))
            ||!ColdSteelWorldInteraction::CanReachPickup(GetWorld(),Pawn,Actor->Get(),Item.Position))continue;
        bool FootprintChanged=false;FString MigrationReason;
        if(UsesChangedSharedFootprint(Item)&&!MigrateAuthoredItemFootprint(Item,FootprintChanged,MigrationReason))continue;
        auto Trial=Profile;
        const bool Added=Model->AmmoType(Item.Definition)?Model->AddAmmoToState(Trial,Item.Definition,Item.Count)
            :ColdSteelInventory::Insert(Trial.Items,Item);
        if(!Added)continue;
        Profile=MoveTemp(Trial);After.Drops.RemoveAt(Index);++Taken;
    }
    if(!Taken){Reason=TEXT("附近没有可拾取的物品或背包已满");return false;}
    Reason=FString::Printf(TEXT("已拾取 %d 件物品"),Taken);
    return Commit(Model,Guest,MoveTemp(Profile),MoveTemp(After),Reason);
}
bool UColdSteelSharedInventorySubsystem::FlushForTravel()
{
    if(bBlocked||bCommitting)return false;
    if(!bInitialized)return true;
    CaptureDropTransforms();return !SaveSlot.IsEmpty()&&SaveWorld(Current);
}
void UColdSteelSharedInventorySubsystem::Deinitialize()
{
    if(bInitialized&&!bBlocked&&!SaveSlot.IsEmpty()){CaptureDropTransforms();SaveWorld(Current);}
    DropActors.Reset();Super::Deinitialize();
}
