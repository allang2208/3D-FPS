#include "ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelInventoryRequestTypes.h"
#include "ColdSteelPlayerState.h"
#include "../Building/ColdSteelPlantingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"

bool UColdSteelSharedInventorySubsystem::CommitPlantingWorld(FColdSteelSharedInventoryData After,FString& Reason)
{
    if(!InitializeAuthority()||bCommitting){Reason=TEXT("共享世界保存尚待恢复");return false;}
    TGuardValue<bool> Guard(bCommitting,true);
    // Reuse the existing complete world-only redo envelope/recovery slot. Its
    // historical Food name does not limit the fields in its complete After image.
    auto* Journal=NewObject<UColdSteelSharedFoodJournal>();Journal->WorldKey=SaveSlot;Journal->After=After;
    const FString Slot=SaveSlot+TEXT("_FoodTransaction");
    if(!UGameplayStatics::SaveGameToSlot(Journal,Slot,0)||!SaveWorld(After)||!UGameplayStatics::DeleteGameInSlot(Slot,0))
    {bBlocked=true;Reason=TEXT("种植世界保存未确认，已暂停操作并保留恢复日志");return false;}
    Current=MoveTemp(After);return true;
}

bool UColdSteelSharedInventorySubsystem::EnsurePlantingWorld(AVoxelBuildWorld* World,FString& Reason)
{
    if(!World||World->GetWorld()!=GetWorld()||!World->HasAuthority()||!World->IsReady()||!InitializeAuthority())
    {Reason=TEXT("共享种植地尚未同步或保存待恢复");return false;}
    const FString& Key=World->BuildingWorldKey();
    if(Current.PlantingSeededWorlds.Contains(Key))return true;
    if(Current.PlantingRevision==MAX_int64){Reason=TEXT("种植版本已达上限");return false;}
    if(!World->FlushCampfirePersistence()){Reason=TEXT("种植地身份尚未保存，请稍后重试");return false;}
    auto After=Current;
    const auto* System=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
    const int32 Limit=System?System->Capacity():1024;
    // Like shared harvest seeding, only the host's solo world is imported once.
    // Guest profile uploads never seed or replace public plants. The solo domain
    // stays private and is not overwritten with other players' shared crops.
    if(GetWorld()->GetNetMode()==NM_ListenServer)
        if(auto* Host=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            for(const auto& Plant:Host->PlantingCrops())
            {
                const auto* Bed=Cast<AVoxelBuildPrefabActor>(World->PrefabActorAt(Plant.BedCell));
                if(Plant.WorldKey!=Key||!Plant.PlantId.IsValid()||!Bed||Bed->IsFalling()||Bed->PrefabId()!=UColdSteelPlantingSystem::BedPrefabId()
                    ||World->PrefabInstanceIdentity(Plant.BedCell)!=Plant.BedId||!FColdSteelCropPlant::Fits(Plant.Slot,Plant.Footprint))continue;
                if(After.PlantingCrops.Num()>=Limit)break;
                const bool Conflict=After.PlantingCrops.ContainsByPredicate([&](const auto& Other)
                {
                    if(Other.PlantId==Plant.PlantId)return true;
                    if(Other.WorldKey!=Key||Other.BedId!=Plant.BedId)return false;
                    for(int32 Slot=0;Slot<16;++Slot)if(Other.Occupies(Slot)&&Plant.Occupies(Slot))return true;
                    return false;
                });
                if(!Conflict)After.PlantingCrops.Add(Plant);
            }
    After.PlantingSeededWorlds.Add(Key);++After.PlantingRevision;
    return CommitPlantingWorld(MoveTemp(After),Reason);
}

bool UColdSteelSharedInventorySubsystem::PrunePlanting(AVoxelBuildWorld* World,const TSet<FGuid>& Orphans,FString& Reason)
{
    if(Orphans.IsEmpty())return true;
    if(!EnsurePlantingWorld(World,Reason)||Current.PlantingRevision==MAX_int64)return false;
    auto After=Current;
    After.PlantingCrops.RemoveAll([&](const auto& Plant){return Plant.WorldKey==World->BuildingWorldKey()&&Orphans.Contains(Plant.PlantId);});
    ++After.PlantingRevision;return CommitPlantingWorld(MoveTemp(After),Reason);
}

bool UColdSteelSharedInventorySubsystem::PlantingAction(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,
    const FColdSteelInventoryRequest& Request,FString& Reason)
{
    if(Request.Action!=EColdSteelInventoryAction::Planting||!Model||!Model->RuntimePawn()||!InitializeAuthority())
    {Reason=TEXT("服务端种植或操作者档案尚未就绪");return false;}
    auto* Pawn=Model->RuntimePawn();auto* PC=Cast<APlayerController>(Pawn->GetController());
    if(!PC||PC->GetPawn()!=Request.Pawn||Request.Pawn!=Pawn||!Pawn->HasAuthority()
        ||(Guest&&(Guest!=Pawn->GetPlayerState<AColdSteelPlayerState>()||Guest->GetShadowModel()!=Model||Guest->CampfireGuestSlot().IsEmpty()))
        ||(!Guest&&!PC->IsLocalController()))
    {Reason=TEXT("没有该房间的有效种植操作身份");return false;}
    for(auto It=PlantingRequestAt.CreateIterator();It;++It)if(!It.Key().IsValid())It.RemoveCurrent();
    const double Now=GetWorld()->GetTimeSeconds();
    if(const auto* Last=PlantingRequestAt.Find(Model);Last&&Now-*Last<.15)
    {Reason=TEXT("操作过快，请稍后重试");return false;}
    PlantingRequestAt.Add(Model,Now);
    auto* Bed=Cast<AVoxelBuildPrefabActor>(Request.Target);
    auto* World=Bed?Cast<AVoxelBuildWorld>(Bed->GetOwner()):nullptr;
    if(!World||World->GetWorld()!=GetWorld()||!EnsurePlantingWorld(World,Reason))
    {if(Reason.IsEmpty())Reason=TEXT("种植地不属于当前房间");return false;}
    auto* System=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
    if(!System||Current.PlantingRevision==MAX_int64)return false;
    Model->SyncRuntime();auto Profile=Model->Snapshot();auto After=Current;
    if(!System->PrepareNetwork(World,Request,Model,Profile,After.PlantingCrops,Reason))return false;
    // Persist the actual bed identity before creating a payable world record.
    if(!World->FlushCampfirePersistence()){Reason=TEXT("种植地保存未确认，操作未提交");return false;}
    ++After.PlantingRevision;
    Reason=Request.Mode==TEXT("planting.harvest")?TEXT("已收获，产物已放入你的背包"):TEXT("已播种，植株在公共种植地生长");
    return Commit(Model,Guest,MoveTemp(Profile),MoveTemp(After),Reason);
}
