#include "ColdSteelSharedInventorySubsystem.h"
#include "../WorldGeneration/ForestVillageMap.h"
#include "../Tasks/BlacksmithApprenticeship.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../Items/FoodSpoilage.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../Production/ProductionToolComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../FPSGAMECharacter.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "EngineUtils.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Crc.h"
#include "HAL/IConsoleManager.h"
#include "TimerManager.h"
using namespace ColdSteelInventory;

namespace
{
bool UsesChangedSharedFootprint(const FColdSteelItem& Item)
{
    return Item.Definition==TEXT("ue_tactical_hatchet")||Item.Definition==TEXT("alchemy_compound_stabilizer")||Item.Definition==TEXT("ue_tactical_magazine_belt")
        ||Item.Definition==TEXT("ue_melee_combat_belt")||Item.Definition==TEXT("ue_arcane_conduit_belt");
}
// Rebase using the old world's durable clock checkpoint before changing domains.
// Ordinary clock advancement changes no item fields and does not cause a disk write.
bool SettleSharedFoodData(FColdSteelSharedInventoryData& Data,const UColdSteelStatusModel* Model,
    const FFoodClockSample& Now,TArray<FString>& ChangedContainers,bool& Changed,FString& Reason)
{
    Changed=false;Reason.Reset();ChangedContainers.Reset();
    if(!Now.Id.IsValid())
    {
        bool HasFood=Data.Drops.ContainsByPredicate([](const auto& I){return ColdSteelFood::LifetimeDays(I)>0.;});
        for(const auto& Pair:Data.Containers)
            HasFood|=Pair.Value.Items.ContainsByPredicate([](const auto& I){return ColdSteelFood::LifetimeDays(I)>0.;});
        if(HasFood)Reason=TEXT("食物时钟尚未就绪，请稍后重试");
        return !HasFood;
    }
    const FFoodClockSample Previous{Data.FoodClockId,Data.FoodClockDay};
    auto Rebase=[&](TArray<FColdSteelItem>& Items)
    {
        bool Result=false;
        for(auto& Item:Items)
        {
            if(ColdSteelFood::LifetimeDays(Item)<=0.)continue;
            if(Previous.Id.IsValid()&&Item.FoodClockId==Previous.Id
                &&(Previous.Id!=Now.Id||Now.Day<Previous.Day))
            {ColdSteelFood::Stamp(Item,Now,ColdSteelFood::AgeDays(Item,Previous));Result=true;}
            else Result|=ColdSteelFood::Rebase(Item,Now);
        }
        return Result;
    };
    Changed|=Rebase(Data.Drops);
    Changed|=ColdSteelFood::SettleLoose(Data.Drops,Model,Now,Reason);
    if(!Reason.IsEmpty())return false;
    for(auto& Pair:Data.Containers)
    {
        auto& Container=Pair.Value;
        bool ContainerChanged=Rebase(Container.Items);
        ContainerChanged|=ColdSteelFood::SettleGrid(Container.Items,Model,Now,Reason);
        if(!Reason.IsEmpty())return false;
        if(!ContainerChanged)continue;
        if(Container.Revision==MAX_int64){Reason=TEXT("容器版本已达上限，保留原有食物");return false;}
        ++Container.Revision;Changed=true;ChangedContainers.Add(Pair.Key);
    }
    Data.FoodVersion=1;Data.FoodClockId=Now.Id;Data.FoodClockDay=Now.Day;
    return true;
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
    if(World.GetNetMode()!=NM_Standalone&&World.GetNetMode()!=NM_Client)
    {
        InitializeAuthority();
        World.GetTimerManager().SetTimer(FoodSpoilageTimer,this,&ThisClass::TickFoodSpoilage,5.f,true);
    }
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
    if(ForestVillageMap::HasVillage(Map))
    {ATemperateHillsWorld* Hills=nullptr;for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
     if(!Hills||!Hills->WorldId.IsValid())return false;RunKey=Hills->WorldId.ToString(EGuidFormats::Digits);}
    bInitialized=true;
    auto* Host=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Host){bBlocked=true;return false;}
    SaveSlot=FString::Printf(TEXT("%s_Shared_%08x"),*Host->ProfileSlot(),FCrc::StrCrc32(*(Map+RunKey)));
    const FString FoodJournalSlot=SaveSlot+TEXT("_FoodTransaction");
    if(UGameplayStatics::DoesSaveGameExist(FoodJournalSlot,0))
    {
        const auto* Food=Cast<UColdSteelSharedFoodJournal>(UGameplayStatics::LoadGameFromSlot(FoodJournalSlot,0));
        // The two commit paths are mutually exclusive. Preserve unexpected
        // overlapping evidence instead of choosing an arbitrary winner.
        if(!Food||Food->Version!=1||Food->WorldKey!=SaveSlot
            ||UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_Transaction"),0))
        {bBlocked=true;return false;}
        // Redo is a complete world snapshot, so it can also restore a damaged
        // main slot after an interrupted write. Replaying it grants no player items.
        if(!SaveWorld(Food->After)||!UGameplayStatics::DeleteGameInSlot(FoodJournalSlot,0))
        {bBlocked=true;return false;}
    }
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
    auto Migrated=Current;bool InventoryChanged=false;FString MigrationReason;
    const auto RetiredQuartz=[](const FColdSteelItem& Item){return Item.Definition==TEXT("quartz");};
    InventoryChanged|=Migrated.Drops.RemoveAll(RetiredQuartz)>0;
    if(UDungeonRoomSubsystem::Supports(GetWorld()))
    {
        // A fresh hub session cannot resume the previous streamed dungeon instance.
        InventoryChanged|=Migrated.Drops.RemoveAll([](const FColdSteelItem& I){return I.Map==TEXT("L_Dungeon_Randomized");})>0;
        for(auto It=Migrated.Containers.CreateIterator();It;++It)
            if(It.Key().Contains(TEXT(".Run."))&&(It.Key().StartsWith(TEXT("DungeonChest."))||It.Key().StartsWith(TEXT("SceneSearch.L_Dungeon_Randomized."))))
            {It.RemoveCurrent();InventoryChanged=true;}
    }
    for(auto& Entry:Migrated.Containers)
        if(Entry.Value.Items.RemoveAll(RetiredQuartz)>0){++Entry.Value.Revision;InventoryChanged=true;}
    for(auto& Item:Migrated.Drops)
    {
        if(!UsesChangedSharedFootprint(Item))continue;
        bool ItemChanged=false;
        if(!MigrateAuthoredItemFootprint(Item,ItemChanged,MigrationReason))
        {UE_LOG(LogTemp,Warning,TEXT("Shared drop migration failed: %s"),*MigrationReason);bBlocked=true;return false;}
        InventoryChanged|=ItemChanged;
    }
    if(InventoryChanged)
    {
        if(!SaveWorld(Migrated)){bBlocked=true;return false;}
        Current=MoveTemp(Migrated);
    }
    FString FoodReason;
    if(!SettleFoodSpoilage(FoodReason))return false;
    RefreshDropActors();
    return true;
}
bool UColdSteelSharedInventorySubsystem::SaveWorld(const FColdSteelSharedInventoryData& Data)
{
    auto* Save=NewObject<UColdSteelSharedInventorySave>();Save->Data=Data;
    const auto Now=ColdSteelFood::Clock(this);
    if(Now.Id.IsValid()&&(!Data.FoodClockId.IsValid()||(Data.FoodClockId==Now.Id&&Now.Day>=Data.FoodClockDay)))
    {Save->Data.FoodVersion=1;Save->Data.FoodClockId=Now.Id;Save->Data.FoodClockDay=Now.Day;}
    return UGameplayStatics::SaveGameToSlot(Save,SaveSlot,0);
}
bool UColdSteelSharedInventorySubsystem::SettleFoodSpoilage(FString& Reason)
{
    Reason.Reset();
    if(!InitializeAuthority()||bCommitting)return false;
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model)return false;
    const auto Now=ColdSteelFood::Clock(this);
    const auto NeedsSettlement=[&](const FColdSteelItem& Item)
    {
        return ColdSteelFood::LifetimeDays(Item)>0.&&(!Now.Id.IsValid()||Item.FoodVersion==0
            ||Item.FoodClockId!=Now.Id||(Current.FoodClockId==Now.Id&&Now.Day<Current.FoodClockDay)
            ||ColdSteelFood::IsExpired(Item,Now));
    };
    bool Needs=Current.Drops.ContainsByPredicate(NeedsSettlement);
    for(const auto& Pair:Current.Containers)Needs|=Pair.Value.Items.ContainsByPredicate(NeedsSettlement);
    if(!Needs)
    {
        // Do not clone the large shared Building/Harvest snapshot every timer pass.
        if(Now.Id.IsValid())
        {Current.FoodVersion=1;Current.FoodClockId=Now.Id;Current.FoodClockDay=Now.Day;}
        return true;
    }
    TGuardValue<bool> Guard(bCommitting,true);
    CaptureDropTransforms();auto After=Current;
    bool Changed=false;TArray<FString> ChangedContainers;
    if(!SettleSharedFoodData(After,Model,Now,ChangedContainers,Changed,Reason))return false;
    if(Changed)
    {
        auto* Journal=NewObject<UColdSteelSharedFoodJournal>();Journal->WorldKey=SaveSlot;Journal->After=After;
        const FString FoodJournalSlot=SaveSlot+TEXT("_FoodTransaction");
        if(!UGameplayStatics::SaveGameToSlot(Journal,FoodJournalSlot,0)||!SaveWorld(After)
            ||!UGameplayStatics::DeleteGameInSlot(FoodJournalSlot,0))
        {
            // A failed write can have reached disk. The complete redo snapshot
            // survives; no live item/actor changes until the commit is confirmed.
            bBlocked=true;Reason=TEXT("腐败转换保存未确认，已保留原物品并暂停共享交易");return false;
        }
    }
    Current=MoveTemp(After);
    if(!Changed)return true;
    RefreshDropActors();
    for(const auto& Key:ChangedContainers)
        if(const auto* Target=FoodContainerAnchors.Find(Key);Target&&Target->IsValid())
            for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)It->ClientContainerInvalidated(Target->Get());
    return true;
}
void UColdSteelSharedInventorySubsystem::TickFoodSpoilage()
{
    FString Reason;SettleFoodSpoilage(Reason);
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
    // A denied hand/equipment action must not create a recovery journal.
    if(const auto* Tool=Model->RuntimePawn()->FindComponentByClass<UProductionToolComponent>();
        Tool&&!Tool->ValidateThunderEquipmentChange(Model->Snapshot(),Profile,Reason))return false;
    TGuardValue<bool> Guard(bCommitting,true);
    const auto Now=ColdSteelFood::Clock(this);
    ColdSteelFood::RebaseProfile(Profile,Now);
    FString FoodReason;
    ColdSteelFood::SettleGrid(Profile.Items,Model,Now,FoodReason);
    if(!FoodReason.IsEmpty()){Reason=FoodReason;return false;}
    bool FoodChanged=false;TArray<FString> ChangedContainers;
    if(!SettleSharedFoodData(After,Model,Now,ChangedContainers,FoodChanged,FoodReason)){Reason=FoodReason;return false;}
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
    for(const auto& Key:ChangedContainers)
        if(const auto* Target=FoodContainerAnchors.Find(Key);Target&&Target->IsValid())
            for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)It->ClientContainerInvalidated(Target->Get());
    if(bBlocked)Reason=TEXT("物品已记账，共享世界保存待恢复");
    return true;
}
bool UColdSteelSharedInventorySubsystem::AddWorldDrops(const TArray<FColdSteelItem>& Items)
{
    if (!InitializeAuthority() || bCommitting || Items.IsEmpty()) return false;
    TGuardValue<bool> Guard(bCommitting, true);
    CaptureDropTransforms();
    auto After = Current;
    After.Drops.Append(Items);
    if (!SaveWorld(After)) return false;
    Current = MoveTemp(After);
    RefreshDropActors();
    return true;
}

bool UColdSteelSharedInventorySubsystem::ImportPlayerDrops(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest)
{
    if(!Model||bCommitting||!InitializeAuthority())return false;
    FString FoodReason;if(!SettleFoodSpoilage(FoodReason))return false;
    const FString Map=Model->RuntimePawn()?UDungeonRoomSubsystem::LogicalMap(Model->RuntimePawn()):UGameplayStatics::GetCurrentLevelName(this,true);
    Model->SyncRuntime();auto Profile=Model->Snapshot();
    ColdSteelFood::RebaseProfile(Profile,ColdSteelFood::Clock(this));
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
    if(!SettleFoodSpoilage(Reason))return false;
    Model->SyncRuntime();auto Profile=Model->Snapshot();
    ColdSteelFood::RebaseProfile(Profile,ColdSteelFood::Clock(this));
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
    Item.Map=UDungeonRoomSubsystem::LogicalMap(Pawn);Item.Position=Ground.ImpactPoint;
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
    if(!SettleFoodSpoilage(Reason)||!IsValid(Actor))return false;
    auto* Pawn=Model->RuntimePawn();
    const auto* Registered=DropActors.Find(Actor->ItemId);
    if(!Registered||Registered->Get()!=Actor)return false;
    if(!Nearby&&!Actor->CanInteract(Pawn)){Reason=TEXT("物品不可达");return false;}
    if(Nearby&&!ColdSteelWorldInteraction::CanReachPickup(GetWorld(),Pawn,Actor,Actor->GetActorLocation()))return false;
    Model->SyncRuntime();auto Profile=Model->Snapshot();
    ColdSteelFood::RebaseProfile(Profile,ColdSteelFood::Clock(this));
    CaptureDropTransforms();auto After=Current;
    const int32 Index=After.Drops.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Actor->ItemId;});
    if(Index<0)return false;
    auto Item=After.Drops[Index];bool FootprintChanged=false;
    if(UsesChangedSharedFootprint(Item)&&!MigrateAuthoredItemFootprint(Item,FootprintChanged,Reason))return false;
    const bool Added=Model->AmmoType(Item.Definition)?Model->AddAmmoToState(Profile,Item.Definition,Item.Count)
        :BlacksmithApprenticeship::InsertPickup(Profile,Item);
    if(!Added){Reason=TEXT("背包已满，物品留在地面");return false;}
    After.Drops.RemoveAt(Index);Reason=TEXT("已拾取物品");
    return Commit(Model,Guest,MoveTemp(Profile),MoveTemp(After),Reason);
}
bool UColdSteelSharedInventorySubsystem::PickupNearby(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,FString& Reason)
{
    if(!Model||!Model->RuntimePawn()||!InitializeAuthority())return false;
    if(!SettleFoodSpoilage(Reason))return false;
    const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Pickup.AreaRadiusCm"));
    const float Radius=Setting?Setting->GetFloat():500.f;
    auto* Pawn=Model->RuntimePawn();Model->SyncRuntime();auto Profile=Model->Snapshot();
    ColdSteelFood::RebaseProfile(Profile,ColdSteelFood::Clock(this));
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
            :BlacksmithApprenticeship::InsertPickup(Trial,Item);
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
    if(!UWildlifeSubsystem::FlushPendingLoot(GetWorld()))return false;
    if(!bInitialized)return true;
    FString Reason;if(!SettleFoodSpoilage(Reason))return false;
    CaptureDropTransforms();return !SaveSlot.IsEmpty()&&SaveWorld(Current);
}
void UColdSteelSharedInventorySubsystem::Deinitialize()
{
    GetWorld()->GetTimerManager().ClearTimer(FoodSpoilageTimer);
    if(bInitialized&&!bBlocked&&!SaveSlot.IsEmpty()){CaptureDropTransforms();SaveWorld(Current);}
    DropActors.Reset();FoodContainerAnchors.Reset();Super::Deinitialize();
}


bool UColdSteelSharedInventorySubsystem::RetireDungeonInventory(const FString& RunId)
{
    if(!bInitialized)return true;
    if(bBlocked||bCommitting||!UDungeonRoomSubsystem::Supports(GetWorld()))return false;
    CaptureDropTransforms();auto After=Current;
    bool Changed=After.Drops.RemoveAll([](const FColdSteelItem& Item){return Item.Map==TEXT("L_Dungeon_Randomized");})>0;
    const FString Suffix=TEXT(".Run.")+RunId;
    for(auto It=After.Containers.CreateIterator();It;++It)
        if(!RunId.IsEmpty()&&It.Key().EndsWith(Suffix)
            &&(It.Key().StartsWith(TEXT("DungeonChest."))||It.Key().StartsWith(TEXT("SceneSearch.L_Dungeon_Randomized."))))
        {It.RemoveCurrent();Changed=true;}
    if(!Changed)return true;
    if(!SaveWorld(After))return false;
    Current=MoveTemp(After);RefreshDropActors();
    for(auto It=FoodContainerAnchors.CreateIterator();It;++It)
        if(!It.Value().IsValid()||UDungeonRoomSubsystem::IsDungeonActor(It.Value().Get()))It.RemoveCurrent();
    return true;
}
