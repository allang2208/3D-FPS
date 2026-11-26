#include "ColdSteelContainerSearchSubsystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "ColdSteelSceneContainer.h"
#include "ColdSteelDungeonLoot.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelItemRarity.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

bool UColdSteelContainerSearchSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{return Type==EWorldType::Game||Type==EWorldType::PIE;}
TStatId UColdSteelContainerSearchSubsystem::GetStatId() const
{RETURN_QUICK_DECLARE_CYCLE_STAT(ColdSteelContainerSearch,STATGROUP_Tickables);}
FString UColdSteelContainerSearchSubsystem::Canonical(const FString& Key)
{return Key.StartsWith(TEXT("NetView."))?Key.Mid(8):Key;}
const UColdSteelContainerSearchSubsystem::FViewer* UColdSteelContainerSearchSubsystem::Find(const APlayerController* Player) const
{return Viewers.Find(TWeakObjectPtr<APlayerController>(const_cast<APlayerController*>(Player)));}
bool UColdSteelContainerSearchSubsystem::CanAccess(const APawn* Pawn,const AActor* Target)
{
    if(!IsValid(Pawn)||!IsValid(Target)||Pawn->GetWorld()!=Target->GetWorld()||!Pawn->GetController()
        ||FVector::DistSquared(Pawn->GetActorLocation(),Target->GetActorLocation()+FVector(0,0,70))>FMath::Square(250.f))return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    if(const auto* Scene=Cast<AColdSteelSceneContainer>(Target);Scene&&!Scene->IsAvailableForSearch())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ContainerSearchReach),false,Pawn);Query.AddIgnoredActor(Target);
    FHitResult Wall;
    return !Pawn->GetWorld()->LineTraceSingleByChannel(Wall,Pawn->GetPawnViewLocation(),Target->GetActorLocation()+FVector(0,0,70),ECC_Visibility,Query);
}
bool UColdSteelContainerSearchSubsystem::Resolve(AActor* Target,FString& Key,int32& Pages,FString& Caption)
{
    if(auto* Scene=Cast<AColdSteelSceneContainer>(Target))
    {Key=Scene->StorageKey();Pages=FMath::Clamp(Scene->StoragePages,1,8);Caption=Scene->Caption;return !Key.IsEmpty();}
    if(IsValid(Target)&&ColdSteelWorldInteraction::IsTreasureChest(Target)&&!Target->ActorHasTag(TEXT("DungeonReward.Locked")))
    {Key=FColdSteelDungeonLoot::ChestStorageKey(Target);Pages=1;Caption=TEXT("宝箱战利品");return !Key.IsEmpty();}
    return false;
}
const TArray<FColdSteelItem>* UColdSteelContainerSearchSubsystem::Contents(APlayerController* Player,const FString& Key) const
{
    if(GetWorld()->GetNetMode()==NM_Standalone)
    {
        const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        return Model?&Model->Items():nullptr;
    }
    const auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();
    const auto* Container=Shared?Shared->Data().Containers.Find(Key):nullptr;
    return Container?&Container->Items:nullptr;
}
float UColdSteelContainerSearchSubsystem::DurationFor(const FColdSteelItem& Item)
{
    if(!bSettingsLoaded)
    {
        bSettingsLoaded=true;
        RaritySeconds={{TEXT("common"),.6f},{TEXT("uncommon"),1.f},{TEXT("rare"),1.6f},{TEXT("epic"),2.3f},{TEXT("mythic"),3.2f},{TEXT("legendary"),4.5f}};
        FString Json;TSharedPtr<FJsonObject> Data;
        if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/container_search.json")))
            &&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Data)&&Data)
        {
            double Seconds;
            for(auto& Pair:RaritySeconds)if(Data->TryGetNumberField(Pair.Key,Seconds)&&FMath::IsFinite(Seconds))Pair.Value=FMath::Clamp(float(Seconds),.1f,30.f);
            if(Data->TryGetNumberField(TEXT("equipment"),Seconds)&&FMath::IsFinite(Seconds))EquipmentSeconds=FMath::Clamp(float(Seconds),.1f,30.f);
        }
    }
    if(ColdSteelItemRarity::IsEquipment(Item))return EquipmentSeconds;
    const auto* Seconds=RaritySeconds.Find(ColdSteelInventory::Text(Item,TEXT("rarity")));
    return Seconds?*Seconds:.6f;
}
bool UColdSteelContainerSearchSubsystem::Reconcile(FRecord& Record,const FString& Key,const TArray<FColdSteelItem>& Items)
{
    const FColdSteelItem* Next=nullptr;bool CurrentExists=false;Record.Total=0;Record.Found=0;
    for(const auto& Item:Items)if(Item.Place==4&&Canonical(Item.Container)==Key)
    {
        ++Record.Total;
        if(Record.Revealed.Contains(Item.InstanceId)){++Record.Found;continue;}
        if(Item.InstanceId==Record.Searching)CurrentExists=true;
        if(!Next||Item.Cell<Next->Cell||(Item.Cell==Next->Cell&&Item.InstanceId<Next->InstanceId))Next=&Item;
    }
    if(CurrentExists)return false;
    const FString NextId=Next?Next->InstanceId:FString();
    const bool Changed=Record.Searching!=NextId;
    Record.Searching=NextId;Record.Elapsed=0;Record.Duration=Next?DurationFor(*Next):0;
    return Changed;
}
void UColdSteelContainerSearchSubsystem::Begin(APlayerController* Player,AActor* Target)
{
    FString Key,Caption;int32 Pages;
    if(!Player||!Player->HasAuthority()||!CanAccess(Player->GetPawn(),Target)||!Resolve(Target,Key,Pages,Caption))return;
    auto& Viewer=Viewers.FindOrAdd(Player);
    if(Viewer.Anchor==Target&&Viewer.Key==Key)return;
    auto* Previous=Cast<AColdSteelSceneContainer>(Viewer.Anchor.Get());
    Viewer.Anchor=Target;Viewer.Key=Key;Viewer.UpdatedAt=GetWorld()->GetTimeSeconds();
    if(Previous)Previous->CloseLootVisual();
    auto& Record=Viewer.Records.FindOrAdd(Key);
    if(const auto* Items=Contents(Player,Key))Reconcile(Record,Key,*Items);
}
bool UColdSteelContainerSearchSubsystem::IsActive(const APlayerController* Player,const AActor* Target) const
{const auto* Viewer=Find(Player);return Viewer&&Viewer->Anchor.IsValid()&&(!Target||Viewer->Anchor.Get()==Target);}
bool UColdSteelContainerSearchSubsystem::HasViewers(const AActor* Target) const
{
    for(const auto& Pair:Viewers)if(Pair.Key.IsValid()&&Pair.Value.Anchor.Get()==Target)return true;
    return false;
}
bool UColdSteelContainerSearchSubsystem::IsSearching(const APlayerController* Player,const FString& Key) const
{
    const auto* Viewer=Find(Player);if(!Viewer||!Viewer->Anchor.IsValid()||Canonical(Key)!=Viewer->Key)return false;
    const auto* Record=Viewer->Records.Find(Viewer->Key);return Record&&!Record->Searching.IsEmpty();
}
void UColdSteelContainerSearchSubsystem::Close(APlayerController* Player,AActor* Target)
{
    auto* Viewer=Viewers.Find(Player);
    if(Viewer&&Viewer->Anchor==Target)
    {
        Viewer->Anchor.Reset();Viewer->Key.Empty();
        if(GetWorld()->GetNetMode()!=NM_Client)if(auto* Scene=Cast<AColdSteelSceneContainer>(Target))Scene->CloseLootVisual();
    }
}
void UColdSteelContainerSearchSubsystem::CloseLocal(APlayerController* Player,AActor* Target)
{
    if(!Player)return;
    if(!Player->HasAuthority())if(auto* PS=Player->GetPlayerState<AColdSteelPlayerState>())PS->ServerCloseContainerSearch(Target);
    Close(Player,Target);
}
void AColdSteelPlayerState::ServerCloseContainerSearch_Implementation(AActor* Target)
{
    if(auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>())Search->Close(Cast<APlayerController>(GetOwner()),Target);
}
bool UColdSteelContainerSearchSubsystem::Hidden(const APlayerController* Player,const FColdSteelItem& Item)
{
    if(Item.Definition==TEXT("container_unsearched"))return true;
    if(!Player||Item.Place!=4)return false;
    const auto* Search=Player->GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>();
    const auto* Viewer=Search?Search->Find(Player):nullptr;
    if(!Viewer)return false;
    const auto* Record=Viewer->Records.Find(Canonical(Item.Container));
    return Record&&!Record->Revealed.Contains(Item.InstanceId);
}
void UColdSteelContainerSearchSubsystem::FillView(APlayerController* Player,UColdSteelInventoryReply& Reply)
{
    auto* Viewer=Viewers.Find(Player);
    if(!Viewer||!Viewer->Anchor.IsValid()||Viewer->Key!=Reply.ContainerKey){Reply.bContainerView=false;Reply.ContainerItems.Empty();return;}
    auto& Record=Viewer->Records.FindChecked(Viewer->Key);Reconcile(Record,Viewer->Key,Reply.ContainerItems);
    Reply.bContainerSearch=true;Reply.ContainerRevealed=Record.Revealed.Array();
    Reply.ContainerSearchItem=Record.Searching;Reply.ContainerSearchElapsed=Record.Elapsed;Reply.ContainerSearchDuration=Record.Duration;
    for(auto& Item:Reply.ContainerItems)if(!Record.Revealed.Contains(Item.InstanceId))
    {
        FColdSteelItem Mask;Mask.InstanceId=Item.InstanceId;Mask.Definition=TEXT("container_unsearched");Mask.Data=TEXT("{}");
        Mask.Place=4;Mask.Container=Item.Container;Mask.Cell=Item.Cell;Mask.Width=Item.Width;Mask.Height=Item.Height;Mask.bRotated=Item.bRotated;
        Item=MoveTemp(Mask);
    }
}
void UColdSteelContainerSearchSubsystem::ApplyView(APlayerController* Player,AActor* Target,const UColdSteelInventoryReply& Reply)
{
    if(!Player||Player->HasAuthority()||!Reply.bContainerSearch)return;
    auto& Viewer=Viewers.FindOrAdd(Player);Viewer.Anchor=Target;Viewer.Key=Reply.ContainerKey;Viewer.UpdatedAt=GetWorld()->GetTimeSeconds();
    auto& Record=Viewer.Records.FindOrAdd(Viewer.Key);Record.Revealed.Empty();
    for(const auto& Id:Reply.ContainerRevealed)Record.Revealed.Add(Id);
    Record.Searching=Reply.ContainerSearchItem;Record.Elapsed=Reply.ContainerSearchElapsed;Record.Duration=Reply.ContainerSearchDuration;
    Record.Total=Reply.ContainerItems.Num();Record.Found=0;
    for(const auto& Item:Reply.ContainerItems)Record.Found+=Record.Revealed.Contains(Item.InstanceId)?1:0;
}
bool UColdSteelContainerSearchSubsystem::ValidateChange(APlayerController* Player,const TArray<FColdSteelItem>& Before,const TArray<FColdSteelItem>& After,FString& Reason) const
{
    const auto* Viewer=Find(Player);if(!Viewer||!Viewer->Anchor.IsValid())return true;
    const auto* Record=Viewer->Records.Find(Viewer->Key);if(!Record)return true;
    for(auto Item:Before)if(Item.Place==4&&Canonical(Item.Container)==Viewer->Key&&!Record->Revealed.Contains(Item.InstanceId))
    {
        const auto* Next=After.FindByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId;});
        bool Same=false;
        if(Next){auto Copy=*Next;Copy.Container=Canonical(Copy.Container);Item.Container=Canonical(Item.Container);Copy.Cooldown=Item.Cooldown;
            Same=FColdSteelItem::StaticStruct()->CompareScriptStruct(&Item,&Copy,0);}
        if(!Same){Reason=TEXT("请等待物品搜索完成；未搜索的物品不能移动、合并或整理");return false;}
    }
    return true;
}
void UColdSteelContainerSearchSubsystem::ObserveChange(APlayerController* Player,const TArray<FColdSteelItem>& Before,const TArray<FColdSteelItem>& After)
{
    auto* Viewer=Viewers.Find(Player);if(!Viewer||!Viewer->Anchor.IsValid())return;
    if(Player&&Player->HasAuthority()&&Viewer->Anchor->ActorHasTag(TEXT("DungeonFinalTreasure")))
    {
        // This callback runs after a committed local/shared inventory change.
        // Compare quantities by definition, so sorting/merging/splitting stacks
        // cannot count as looting. Ammo converted to the ammo pool counts too.
        TMap<FString,int64> Counts;
        for(const auto& Item:Before)if(Item.Place==4&&Canonical(Item.Container)==Viewer->Key)Counts.FindOrAdd(Item.Definition)+=Item.Count;
        for(const auto& Item:After)if(Item.Place==4&&Canonical(Item.Container)==Viewer->Key)Counts.FindOrAdd(Item.Definition)-=Item.Count;
        for(const auto& Pair:Counts)if(Pair.Value>0)
        {if(auto* Run=UDungeonRunSubsystem::Get(GetWorld()))Run->MarkFinalTreasureLooted(Viewer->Anchor.Get(),Player);break;}
    }
    auto& Record=Viewer->Records.FindChecked(Viewer->Key);
    bool Learned=false;
    for(const auto& Item:After)if(Item.Place==4&&Canonical(Item.Container)==Viewer->Key)
        if(!Before.ContainsByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId&&I.Place==4&&Canonical(I.Container)==Viewer->Key;}))
        {Record.Revealed.Add(Item.InstanceId);Learned=true;}
    Reconcile(Record,Viewer->Key,After);
    if(Learned&&GetWorld()->GetNetMode()==NM_Standalone)Notify(Player,Viewer->Anchor.Get());
}
float UColdSteelContainerSearchSubsystem::Progress(const APlayerController* Player,const FString& ItemId) const
{
    const auto* Viewer=Find(Player);if(!Viewer||!Viewer->Anchor.IsValid())return -1.f;
    const auto* Record=Viewer->Records.Find(Viewer->Key);if(!Record||Record->Searching!=ItemId||Record->Duration<=0)return -1.f;
    const float Prediction=Player->HasAuthority()?0.f:float(GetWorld()->GetTimeSeconds()-Viewer->UpdatedAt);
    return FMath::Clamp((Record->Elapsed+Prediction)/Record->Duration,0.f,1.f);
}
FString UColdSteelContainerSearchSubsystem::Status(const APlayerController* Player,const FString& Key) const
{
    const auto* Viewer=Find(Player);if(!Viewer||Canonical(Key)!=Viewer->Key)return FString();
    const auto* Record=Viewer->Records.Find(Viewer->Key);if(!Record)return FString();
    return Record->Searching.IsEmpty()?TEXT("搜索完成"):FString::Printf(TEXT("搜索中 %d / %d"),Record->Found,Record->Total);
}
void UColdSteelContainerSearchSubsystem::Notify(APlayerController* Player,AActor* Target)
{
    if(GetWorld()->GetNetMode()==NM_Standalone)
    {if(auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Model->OnChanged.Broadcast();}
    else if(auto* PS=Player->GetPlayerState<AColdSteelPlayerState>())PS->ClientContainerInvalidated(Target);
}
void UColdSteelContainerSearchSubsystem::Tick(float DeltaTime)
{
    if(GetWorld()->GetNetMode()==NM_Client)return;
    TickAccumulator+=DeltaTime;if(TickAccumulator<.1f)return;TickAccumulator=0;
    const double Now=GetWorld()->GetTimeSeconds();
    for(auto It=Viewers.CreateIterator();It;++It)
    {
        auto* Player=It.Key().Get();if(!Player)
        {
            auto* Scene=Cast<AColdSteelSceneContainer>(It.Value().Anchor.Get());It.RemoveCurrent();
            if(Scene)Scene->CloseLootVisual();continue;
        }
        auto& Viewer=It.Value();auto* Target=Viewer.Anchor.Get();if(!Target)continue;
        FString Key,Caption;int32 Pages;
        if(!CanAccess(Player->GetPawn(),Target)||!Resolve(Target,Key,Pages,Caption)||Key!=Viewer.Key)
        {Viewer.Anchor.Reset();Viewer.Key.Empty();if(auto* Scene=Cast<AColdSteelSceneContainer>(Target))Scene->CloseLootVisual();continue;}
        const auto* Items=Contents(Player,Viewer.Key);if(!Items)continue;
        auto& Record=Viewer.Records.FindChecked(Viewer.Key);
        bool Changed=Reconcile(Record,Viewer.Key,*Items);
        if(!Record.Searching.IsEmpty())
        {
            if(!Changed)Record.Elapsed+=FMath::Max(0.f,float(Now-Viewer.UpdatedAt));
            if(Record.Elapsed>=Record.Duration)
            {Record.Revealed.Add(Record.Searching);Reconcile(Record,Viewer.Key,*Items);Changed=true;}
        }
        Viewer.UpdatedAt=Now;
        if(Changed)Notify(Player,Target);
    }
}
