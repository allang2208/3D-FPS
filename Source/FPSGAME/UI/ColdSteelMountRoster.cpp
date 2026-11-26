#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "../Movement/StableHorseGear.h"
#include "../Movement/StableHorseAffixes.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FGuid UColdSteelStatusModel::CreditPresentMountExperience(FColdSteelProfile& State,int64 Amount) const
{
    if(Amount<=0 || !State.MountRoster.Deployed.IsValid())return {};
    const auto* Pawn=RuntimePawn();
    if(!IsValid(Pawn) || !Pawn->HasAuthority())return {};
    const auto* Ride=Pawn->FindComponentByClass<UHorseRiderComponent>();
    const auto* Horse=Ride?Ride->GetOwnedHorse():nullptr;
    if(!IsValid(Horse) || Horse->IsActorBeingDestroyed() || Horse->IsRetreating() ||
       Horse->Visit()==EStableHorseVisit::Departing || !Horse->HasActiveKeeper() ||
       Horse->Keeper()!=State.NetworkProfileId || Horse->Identity()!=State.MountRoster.Deployed)return {};
    auto* Entry=State.MountRoster.Find(Horse->Identity());
    if(!Entry || Entry->Level>=FStableHorseTraits::MaxLevel)return {};

    const int32 Previous=Entry->Level;
    const auto Vitals=Horse->Condition();
    Entry->Health=Vitals.Health;
    Entry->Stamina=Vitals.Stamina;
    Entry->bExhausted=Vitals.bExhausted;
    Entry->GainExperience(Amount);
    ++State.MountRoster.Revision;
    // The ordinary owner-only profile mirror already carries XP and this revision.
    // Only a new level needs to change the live movement and vital limits.
    return Previous!=Entry->Level?Entry->HorseId:FGuid();
}

void UColdSteelStatusModel::ApplyCommittedMountLevel(FGuid HorseId) const
{
    if(!HorseId.IsValid())return;
    const auto* Pawn=RuntimePawn();
    const auto* Ride=IsValid(Pawn)?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    auto* Horse=Ride?Ride->GetOwnedHorse():nullptr;
    if(IsValid(Horse) && Horse->Identity()==HorseId && Horse->Keeper()==Current.NetworkProfileId)
        if(const auto* Entry=Current.MountRoster.Find(HorseId))Horse->ApplyEarnedLevel(*Entry);
}

bool UColdSteelStatusModel::CommitMountRoster(FStableMountRoster Roster)
{
    if(!RuntimePawn() || !RuntimePawn()->HasAuthority())return false;
    Roster.Revision=Current.MountRoster.Revision+1;
    auto Next=Snapshot();
    Next.MountRoster=MoveTemp(Roster);
    FString GuestSlot;
    if(bNetShadowProfile)
    {
        const auto* PS=RuntimePawn()->GetPlayerState<AColdSteelPlayerState>();
        if(!PS || PS->CampfireGuestSlot().IsEmpty())return false;
        GuestSlot=PS->CampfireGuestSlot();
    }
    TGuardValue<FString> SlotGuard(CampfireGuestSaveSlot,GuestSlot);
    if(!PersistState(MoveTemp(Next),false))return false;
    if(bNetShadowProfile)
        if(auto* Ride=RuntimePawn()->FindComponentByClass<UHorseRiderComponent>())
        {
            // Gear already travels atomically with its inventory receipt. This RPC carries roster changes only.
            auto Updates=Current.MountRoster;
            for(auto& Entry:Updates.Horses)Entry.Equipment.Empty();
            Ride->ClientMountRoster(Current.NetworkProfileId,Updates);
        }
    return true;
}

void UColdSteelStatusModel::ReceiveMountRoster(FGuid Profile,const FStableMountRoster& Roster)
{
    if(Profile==Current.NetworkProfileId && Roster.Revision>Current.MountRoster.Revision)
    {
        auto Next=Roster;
        StableHorseGear::CopyEquipment(Next,Current.MountRoster);
        Current.MountRoster=MoveTemp(Next);
    }
}

void UColdSteelStatusModel::StageMountCondition(const FStableMountRecord& Horse)
{
    if(auto* Previous=Current.MountRoster.Find(Horse.HorseId))
    {
        // Movement samples must not shorten an escape cooldown or erase progress made in the journal.
        Previous->Health=Horse.Health;Previous->Stamina=Horse.Stamina;Previous->bExhausted=Horse.bExhausted;
        Previous->RecallAfterUtc=FMath::Max(Previous->RecallAfterUtc,Horse.RecallAfterUtc);
    }
}

bool UColdSteelStatusModel::GiveMountPotion(FGuid HorseId,const FString& ItemId,FString& Reason)
{
    auto* Pawn=RuntimePawn();
    if(!Pawn||!Pawn->HasAuthority())return false;
    auto P=Snapshot();
    auto* Horse=P.MountRoster.Find(HorseId);
    if(!Horse){Reason=TEXT("马匹不在当前角色的马匹栏");return false;}
    AStableRidingHorse* Live=nullptr;
    for(TActorIterator<AStableRidingHorse> It(Pawn->GetWorld());It;++It)
    {
        if(It->Identity()!=HorseId||It->Keeper()!=P.NetworkProfileId||!It->HasActiveKeeper()||It->IsRetreating())continue;
        Live=*It;break;
    }
    const float Health=Live?Live->GetHealth():Horse->Health;
    if(Health>=Horse->MaxHealth){Reason=TEXT("马匹生命已满");return false;}
    const int32 I=P.Items.IndexOfByPredicate([&](const auto& Item){return Item.InstanceId==ItemId;});
    if(!P.Items.IsValidIndex(I)){Reason=TEXT("药水已用完");return false;}
    auto& Item=P.Items[I];
    if((Item.Place!=0&&Item.Place!=ColdSteelInventory::ColdSteelCompartment::Place)||Item.Count<1||Item.Cooldown>0.f||
        !(Item.Definition==TEXT("hp_potion")||Item.Definition.StartsWith(TEXT("hp_potion_"))))
    {Reason=TEXT("请选择随身携带的可用生命药水");return false;}
    const auto* Def=Definitions.Find(Item.Definition);
    TSharedPtr<FJsonObject> Json;
    const TSharedPtr<FJsonObject>* Effect=nullptr;
    if(!Def||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Def),Json)||!Json||
        !Json->TryGetObjectField(TEXT("useEffect"),Effect)){Reason=TEXT("生命药水没有治疗配置");return false;}
    double Flat=0.,Percent=0.;(*Effect)->TryGetNumberField(TEXT("hp"),Flat);(*Effect)->TryGetNumberField(TEXT("maxHpPercent"),Percent);
    const float TackPotionScale=1.f+StableHorseGear::Bonuses(*Horse).PotionHealBonus;
    const float Restored=FMath::Min(Horse->MaxHealth-Health,float((Flat+.01*Percent*Horse->MaxHealth)*TackPotionScale));
    if(Restored<=0.f){Reason=TEXT("药水当前无法使用");return false;}
    Horse->Health=Health+Restored;
    const float After=Horse->Health;
    if(--Item.Count==0)P.Items.RemoveAt(I);
    ++P.MountRoster.Revision;
    const auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
    const FString Slot=bNetShadowProfile&&PS?PS->CampfireGuestSlot():FString();
    if(!CommitCampfireState(MoveTemp(P),TEXT("MountPotion"),Slot))
    {Reason=ResultMessage();return false;}
    if(Live)Live->ApplyPotionHealth(After);
    Reason=FString::Printf(TEXT("马匹恢复 %.0f 点生命"),Restored);
    return true;
}

FStableHorseAffixBonuses UColdSteelStatusModel::ActiveMountAura() const
{
    const auto* Pawn=RuntimePawn();
    if(!IsValid(Pawn))return {};
    const auto* Ride=Pawn->FindComponentByClass<UHorseRiderComponent>();
    const auto* Horse=Ride?Ride->GetOwnedHorse():nullptr;
    if(!IsValid(Horse) || Horse->IsActorBeingDestroyed() || Horse->IsMarketShowcase() ||
       Horse->IsRetreating() || Horse->GetHealth()<=0.f ||
       Horse->Visit()==EStableHorseVisit::Departing)
        return {};
    if(!Horse->Identity().IsValid())return {};
    if(Horse->Keeper().IsValid() && Current.NetworkProfileId.IsValid() && Horse->Keeper()!=Current.NetworkProfileId)
        return {};
    return Horse->Affixes();
}

int32 UColdSteelStatusModel::CountMountBagItems(FGuid HorseId) const
{
    if(!HorseId.IsValid())return 0;
    const FString Key=StableHorseAffixes::BagContainerKey(HorseId);
    int32 Count=0;
    for(const auto& I:Current.Items)if(I.Place==ColdSteelWarehouse::Place && I.Container==Key)++Count;
    return Count;
}

bool UColdSteelStatusModel::ReleaseMount(FGuid HorseId,FString& Reason)
{
    using namespace ColdSteelInventory;
    auto* Pawn=RuntimePawn();
    if(!Pawn || !Pawn->HasAuthority() || !HorseId.IsValid())
    {Reason=TEXT("解散马匹操作无效");return false;}
    if(const auto* Ride=Pawn->FindComponentByClass<UHorseRiderComponent>())
    {
        if(Ride->Active() && (!Ride->GetMount() || Ride->GetMount()->Identity()==HorseId))
        {Reason=TEXT("请先下马后再解散马匹");return false;}
    }

    SyncRuntime();
    auto Next=Snapshot();
    const int32 HorseIdx=Next.MountRoster.Horses.IndexOfByPredicate([HorseId](const auto& Entry){return Entry.HorseId==HorseId;});
    if(HorseIdx==INDEX_NONE){Reason=TEXT("马匹不在当前名册");return false;}

    const FString HorseName=Next.MountRoster.Horses[HorseIdx].DisplayName();
    const FString BagKey=StableHorseAffixes::BagContainerKey(HorseId);

    // Collect all items stored inside this horse's backpack + all equipped tack.
    TArray<FColdSteelItem> Evacuate;
    for(int32 I=Next.Items.Num()-1;I>=0;--I)
    {
        if(Next.Items[I].Place==ColdSteelWarehouse::Place && Next.Items[I].Container==BagKey)
        {
            Evacuate.Add(MoveTemp(Next.Items[I]));
            Next.Items.RemoveAt(I);
        }
    }
    for(auto& Gear:Next.MountRoster.Horses[HorseIdx].Equipment)
    {
        Evacuate.Add(MoveTemp(Gear));
    }

    Next.MountRoster.Horses.RemoveAt(HorseIdx);
    if(Next.MountRoster.Deployed==HorseId)Next.MountRoster.Deployed.Invalidate();
    ++Next.MountRoster.Revision;

    int32 ToBag=0, ToWarehouse=0, ToGround=0;
    TArray<FColdSteelItem> GroundDrops;
    const FIntPoint CompGrid=CompartmentGrid(Next.Items);
    const int32 MainWarehouseCap=Next.WarehousePages*ColdSteelWarehouse::CellsPerPage;
    const FString LogicalMap=UDungeonRoomSubsystem::LogicalMap(Pawn);
    const FString StandaloneMap=UGameplayStatics::GetCurrentLevelName(this,true);
    const FVector Origin=Pawn->GetActorLocation();
    const float PlayerYaw=Pawn->GetActorRotation().Yaw;

    auto ComputeGroundSpot=[&](int32 DropIndex,FVector& OutPos,FRotator& OutRot)
    {
        const float AngleDeg=PlayerYaw + (DropIndex==0 ? 0.f : (DropIndex * 53.f));
        const float Radius=DropIndex==0 ? 85.f : FMath::Min(155.f, 70.f + float(DropIndex)*18.f);
        const FVector Dir(FMath::Cos(FMath::DegreesToRadians(AngleDeg)),FMath::Sin(FMath::DegreesToRadians(AngleDeg)),0.f);
        FVector Candidate=Origin + Dir*Radius;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(MountReleaseDrop),false,Pawn);
        FHitResult Obstacle,Ground;
        if(Pawn->GetWorld()->SweepSingleByChannel(Obstacle,Origin,Candidate,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(35.f),Query))
            Candidate=Obstacle.Location - Dir*4.f;
        auto FindGround=[&](const FVector& At)
        {
            return Pawn->GetWorld()->LineTraceSingleByChannel(Ground,At+FVector(0,0,60),At-FVector(0,0,500),ECC_Visibility,Query)
                && Ground.ImpactNormal.Z>=.45f;
        };
        if(FindGround(Candidate) || FindGround(Origin))
        {
            OutPos=Ground.ImpactPoint;
            OutPos.Z=FMath::Max(Ground.ImpactPoint.Z+45.f,Origin.Z+12.f);
        }
        else
        {
            OutPos=Origin + FVector(0,0,25.f);
        }
        OutRot=FRotator(5.f,AngleDeg,-65.f);
    };

    // Strict evacuation order: 1. Player Backpack (+Compartment) -> 2. Main Warehouse -> 3. Player Ground
    for(auto& Item:Evacuate)
    {
        Item.Container.Reset();
        Item.Map.Reset();
        Item.Position=FVector::ZeroVector;

        bool Placed=false;
        // 1a) Player spatial backpack (Place 0), try current & rotated orientation
        Item.Place=0;
        if(Insert(Next.Items,Item))
        {
            Placed=true;
            ++ToBag;
        }
        else if(CanRotate(Item))
        {
            FColdSteelItem Turned=Item;
            ApplyOrientation(Turned,Turned.bRotated?0:1);
            if(Insert(Next.Items,Turned))
            {
                Placed=true;
                ++ToBag;
            }
        }
        // 1b) Player backpack compartment (Place 5)
        if(!Placed && CompGrid.X>0 && CompGrid.Y>0)
        {
            FColdSteelItem CompItem=Item;
            CompItem.Place=ColdSteelCompartment::Place;
            for(int32 Ori=0;Ori<2 && !Placed;++Ori)
            {
                if(Ori==1)
                {
                    if(!CanRotate(CompItem))break;
                    ApplyOrientation(CompItem,CompItem.bRotated?0:1);
                }
                for(int32 Cell=0;Cell<CompGrid.X*CompGrid.Y;++Cell)
                {
                    if(ColdSteelCompartment::Fits(Next.Items,CompItem,Cell,CompGrid))
                    {
                        CompItem.Cell=Cell;
                        Next.Items.Add(MoveTemp(CompItem));
                        Placed=true;
                        ++ToBag;
                        break;
                    }
                }
            }
        }
        // 2) Main Warehouse (Place 4, Container="")
        if(!Placed && MainWarehouseCap>=ColdSteelWarehouse::Columns)
        {
            FColdSteelItem WhItem=Item;
            WhItem.Place=ColdSteelWarehouse::Place;
            WhItem.Container.Reset();
            if(ColdSteelWarehouse::Insert(Next.Items,WhItem,MainWarehouseCap))
            {
                Placed=true;
                ++ToWarehouse;
            }
            else if(CanRotate(WhItem))
            {
                ApplyOrientation(WhItem,WhItem.bRotated?0:1);
                if(ColdSteelWarehouse::Insert(Next.Items,WhItem,MainWarehouseCap))
                {
                    Placed=true;
                    ++ToWarehouse;
                }
            }
        }
        // 3) Player Ground (Place 2)
        if(!Placed)
        {
            FVector DropPos;
            FRotator DropRot;
            ComputeGroundSpot(ToGround,DropPos,DropRot);
            Item.Place=2;
            Item.Container.Reset();
            Item.Cell=INDEX_NONE;
            Item.Map=(Pawn->GetNetMode()==NM_Standalone)?StandaloneMap:LogicalMap;
            Item.Position=DropPos;
            Item.WorldRotation=DropRot;
            StampProductionDrop(Item);
            GroundDrops.Add(MoveTemp(Item));
            ++ToGround;
        }
    }

    if(Pawn->GetNetMode()==NM_Standalone)
    {
        for(auto& DropItem:GroundDrops)Next.Items.Add(MoveTemp(DropItem));
        if(!CommitState(Next))
        {Reason=ResultMessage().IsEmpty()?TEXT("解散马匹保存失败，已保留原状态"):ResultMessage();return false;}
        if(ToGround>0)RefreshDrops();
    }
    else
    {
        auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
        if(bNetShadowProfile && (!PS || PS->CampfireGuestSlot().IsEmpty()))
        {Reason=TEXT("角色档案尚未就绪");return false;}
        if(!GroundDrops.IsEmpty())
        {
            auto* Shared=Pawn->GetWorld()?Pawn->GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>():nullptr;
            if(!Shared || !Shared->CommitProfileWithDrops(this,bNetShadowProfile?PS:nullptr,MoveTemp(Next),GroundDrops,Reason))
            {if(Reason.IsEmpty())Reason=TEXT("共享地面掉落保存失败，已保留原状态");return false;}
        }
        else
        {
            if(!CommitCampfireState(MoveTemp(Next),TEXT("MountRelease"),bNetShadowProfile?PS->CampfireGuestSlot():FString()))
            {Reason=ResultMessage();return false;}
        }
    }

    // Dismiss & destroy live world horse actor if summoned, and immediately clear rider's replicated OwnedHorse reference.
    if(UWorld* World=Pawn->GetWorld())
    {
        for(TActorIterator<AStableRidingHorse> It(World);It;++It)
        {
            if(It->Identity()==HorseId && It->Keeper()==Current.NetworkProfileId && !It->IsMarketShowcase())
            {
                It->Destroy();
            }
        }
    }
    if(auto* Ride=Pawn->FindComponentByClass<UHorseRiderComponent>())
        Ride->ClearReleasedHorse(HorseId);

    if(bMountBagOpen && ActiveContainer==BagKey)EndMountBagSession();

    const int32 TotalEvacuated=ToBag+ToWarehouse+ToGround;
    if(TotalEvacuated==0)
    {
        Reason=FString::Printf(TEXT("已永久解散「%s」"),*HorseName);
    }
    else
    {
        TArray<FString> Parts;
        if(ToBag>0)Parts.Add(FString::Printf(TEXT("背包 %d 件"),ToBag));
        if(ToWarehouse>0)Parts.Add(FString::Printf(TEXT("仓库 %d 件"),ToWarehouse));
        if(ToGround>0)Parts.Add(FString::Printf(TEXT("地面 %d 件"),ToGround));
        Reason=FString::Printf(TEXT("已永久解散「%s」，物品已转移：%s"),*HorseName,*FString::Join(Parts,TEXT("、")));
    }
    return true;
}
