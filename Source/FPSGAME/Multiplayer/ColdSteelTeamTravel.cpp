#include "ColdSteelPlayerState.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "ColdSteelAuthorityContext.h"
#include "ColdSteelNetSessionSubsystem.h"
#include "ColdSteelSharedInventorySubsystem.h"
#include "../Building/SmeltingSystem.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/BowSkillLifecycle.h"
#include "../SceneTestPortal.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "Misc/PackageName.h"
#include "Kismet/GameplayStatics.h"

bool AColdSteelPlayerState::RequestTeamTravel(AActor* Entrance,bool bConfirmUnclaimedReward)
{
    if(GetNetMode()==NM_Standalone||!IsValid(Entrance)||TeamTravelId.IsValid()||RoomTransferToken.IsValid())return false;
    ServerTeamTravel(Entrance,bConfirmUnclaimedReward);return true;
}
void AColdSteelPlayerState::ServerTeamTravel_Implementation(AActor* Entrance,bool bConfirmUnclaimedReward)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->GetPawn()||!IsValid(Entrance)||Entrance->GetWorld()!=GetWorld()||RoomTransferToken.IsValid())return;
    auto* Room=UDungeonRoomSubsystem::Get(GetWorld());
    const bool WasCursor=PC->bShowMouseCursor;PC->bShowMouseCursor=false;
    const bool Focused=ColdSteelWorldInteraction::IsFocused(PC->GetPawn(),Entrance,300);
    PC->bShowMouseCursor=WasCursor;
    FString Destination,Options;
    if(auto* Portal=Cast<ASceneTestPortal>(Entrance))
    {
        if(!Portal->IsWithinInteractionRange(PC->GetPawn()))return;
        if(Portal->ActorHasTag(TEXT("DungeonFinalReturn")))
        {
            const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
            if(!Run||!Run->CanUseFinalReturn())return;
            if(!(Room?bClaimedFinalDungeonTreasure:Run->IsFinalTreasureLooted())&&!bConfirmUnclaimedReward)
            {ClientTeamTravelRejected(TEXT("你尚未领取奖励，请在返程门确认离开"));return;}
        }
        Destination=Portal->DestinationMap();Options=Portal->TravelOptions();
    }
    else if(ColdSteelWorldInteraction::IsExpeditionAltar(Entrance)&&Focused)
        Destination=TEXT("/Game/GameMaps/L_Dungeon_Randomized");
    if(Destination.IsEmpty()||!FPackageName::DoesPackageExist(Destination))return;
    const bool EnterDungeon=Room&&Destination.EndsWith(TEXT("L_Dungeon_Randomized"));
    const bool ReturnToHub=Room&&bInDungeonRoom&&Destination.EndsWith(TEXT("DayNight_Lighting"));
    if(Room&&((EnterDungeon&&bInDungeonRoom)||(ReturnToHub&&!UDungeonRoomSubsystem::IsDungeonActor(Entrance))))return;
    if(Room&&!EnterDungeon&&!ReturnToHub&&(Room->HasOccupants()||Room->HasPendingEntry()))
    {ClientTeamTravelRejected(TEXT("还有队员在地牢或准备出征，当前房间暂时不能整体换图"));return;}
    if(!Room&&Destination.EndsWith(TEXT("DayNight_Lighting"))&&UGameplayStatics::GetCurrentLevelName(this,true)==TEXT("L_Dungeon_Randomized"))
    {ClientTeamTravelRejected(TEXT("此地牢使用旧版换图房间；请重新从主神空间创建房间并出征，以启用单独返程"));return;}
    const bool Individual=ReturnToHub||(EnterDungeon&&(Room->HasInstance()||Room->HasPendingEntry()));
    // Keep the batch exclusive even after ServerTravel accepts it and clears the URL.
    for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)if(It->TeamTravelId.IsValid())return;
    TeamDestination=Destination;TeamOptions=Options;TeamTravelStarted=GetWorld()->GetRealTimeSeconds();
    TeamTravelEntrance=Entrance;
    bTeamReturnUnclaimedConfirmed=bConfirmUnclaimedReward;bTeamReturnCompletionStaged=false;
    const FGuid TravelId=FGuid::NewGuid();
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* State=It->Get()->GetPlayerState<AColdSteelPlayerState>())
        {if(Individual&&State!=this)continue;
         if(State->RoomTransferToken.IsValid())continue;
         State->TeamTravelId=TravelId;State->TeamTravelWorld=GetWorld();State->TeamTravelPawn=It->Get()->GetPawn().Get();State->bTravelReady=false;State->ClientPrepareTeamTravel(TravelId);}
}
void AColdSteelPlayerState::ClientTeamTravelRejected_Implementation(const FString& Reason)
{
    if(auto* M=ColdSteelAuthority::Model(this))M->PostNotice(TEXT("无法返程"),Reason);
}
void AColdSteelPlayerState::ClientPrepareTeamTravel_Implementation(FGuid TravelId)
{
    if(!TravelId.IsValid())return;
    TeamTravelId=TravelId;TeamTravelWorld=GetWorld();
    bTravelFlush=true;bTravelNeedsFreshUpload=true;bHasLastSent=false;HeartbeatTimer=0;
    ASceneTestPortal::CloseLocalReturnConfirmations(Cast<APlayerController>(GetOwner()));
    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner()))
    {
        PC->CloseExpedition();PC->CloseWoodworking();
        if(auto* Pawn=Cast<AFPSGAMECharacter>(PC->GetPawn()))
        {
            Pawn->InterruptActionsForPriority(false);
            if(auto* C=Pawn->FindComponentByClass<UFPSFireballComponent>())C->Cancel();
            if(auto* C=Pawn->FindComponentByClass<UFPSIceSpikeComponent>())C->Cancel();
            if(auto* C=Pawn->FindComponentByClass<UFPSIceWallComponent>())C->Cancel();
            if(auto* C=Pawn->FindComponentByClass<UFPSBlizzardComponent>())C->CancelPending();
        }
    }
    if(auto* M=ColdSteelAuthority::Model(this))M->PostNotice(TEXT("准备传送"),TEXT("正在保存档案，请稍候"));
}
void AColdSteelPlayerState::ServerTeamTravelReady_Implementation(FGuid TravelId,int32 AcceptedUploadId)
{
    if(!TravelId.IsValid()||TravelId!=TeamTravelId)return;
    if(bInventoryRequestPending||bCampfirePending||!IncomingBlob.IsEmpty())return;
    bool Requested=false;
    for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)Requested|=!It->TeamDestination.IsEmpty();
    if(!Requested)return;
    bTravelReady=false;
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(PC&&!PC->IsLocalController()&&(AcceptedUploadId<=0||AcceptedUploadId!=LastAcceptedUploadId))
    {ClientPrepareTeamTravel(TravelId);return;}
    if(SaveTeamTravelParticipant())bTravelReady=true;
}
bool AColdSteelPlayerState::SaveTeamTravelParticipant()
{
    auto* M=ColdSteelAuthority::ForPawn(GetPawn());
    const auto* Health=GetPawn()?GetPawn()->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!M||!Health||Health->IsDead()||TeamTravelPawn.Get()!=GetPawn())
    {AbortTeamTravel(TEXT("队员角色已变化或正在重生，请稍后重试"));return false;}
    if(M->HasUnconfirmedTransactionSave())
    {AbortTeamTravel(TEXT("队员交易保存结果待恢复，暂时无法换图"));return false;}
    // Finish paid jobs and cancel unlaunched casts before persisting readiness.
    CancelPendingNetworkCast();
    SettleSwordUppercut();
    SettleSwordWhirlwind();
    ClearKukriAttack();
    if(auto* Fire=GetPawn()->FindComponentByClass<UFPSFireMagicComponent>())Fire->FinishFireMagicForRemoval();
    if(auto* Ice=GetPawn()->FindComponentByClass<UFPSIceArmorComponent>())Ice->FinishForRemoval();
    if(auto* Ice=GetPawn()->FindComponentByClass<UFPSLightningHasteComponent>())Ice->FinishForRemoval();
    if(auto* Electric=GetPawn()->FindComponentByClass<UFPSElectricMagicComponent>())Electric->FinishDomainForRemoval();
    if(auto* Blizzard=GetPawn()->FindComponentByClass<UFPSBlizzardComponent>())Blizzard->FinishZonesForRemoval();
    BowSkillLifecycle::FinishForRemoval(GetPawn());
    if(!CloseStationSessions()){AbortTeamTravel(TEXT("工作站结算或档案保存失败，请稍后重试"));return false;}
    M->SyncRuntime();
    if(auto* Run=UDungeonRunSubsystem::Get(GetWorld());Run&&Run->IsRunActive()
        &&(!UDungeonRoomSubsystem::Supports(GetWorld())||bInDungeonRoom))
    {
        Run->EnsurePlayerRun(M);
        const auto& SavedRun=M->Snapshot().DungeonRun;
        if(SavedRun.RunId!=Run->RunId()||(!UDungeonRoomSubsystem::Supports(GetWorld())&&SavedRun.bCompleted!=Run->IsRunCompleted()))
        {AbortTeamTravel(TEXT("队员地牢进度保存失败，请稍后重试"));return false;}
    }
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!(PC&&PC->IsLocalController()?M->SaveNow():SaveShadowToHostDisk()))
    {AbortTeamTravel(TEXT("队员档案保存失败，请稍后重试"));return false;}
    return true;
}
void AColdSteelPlayerState::InvalidateTeamTravelReady()
{
    if(!HasAuthority()||!TeamTravelId.IsValid()||!bTravelReady)return;
    bTravelReady=false;
    ClientPrepareTeamTravel(TeamTravelId);
}
void AColdSteelPlayerState::AbortTeamTravel(const FString& Reason)
{
    if(!HasAuthority())return;
    // The failure callback can arrive on any participant, including after the
    // URL was accepted. Roll back the initiator's staged completion first.
    for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)It->RollbackTeamReturnCompletion();
    for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)
    {
        if(!It->TeamTravelId.IsValid())continue;
        const FGuid Cancelled=It->TeamTravelId;
        It->TeamDestination.Reset();It->TeamOptions.Reset();It->bTravelReady=false;It->TeamTravelEntrance.Reset();
        It->bTeamReturnUnclaimedConfirmed=false;
        It->ClientTeamTravelSaveFailed(Cancelled,Reason);It->TeamTravelId.Invalidate();
    }
}
void AColdSteelPlayerState::RollbackTeamReturnCompletion()
{
    if(!HasAuthority()||!bTeamReturnCompletionStaged)return;
    bTeamReturnCompletionStaged=false;
    if(TeamTravelWorld.Get()!=GetWorld())return;
    auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    if(!Run||!TeamTravelEntrance.IsValid())return;
    Run->CancelFinalReturn(TeamTravelEntrance.Get());
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PS=It->Get()->GetPlayerState<AColdSteelPlayerState>())
        {
            auto* M=ColdSteelAuthority::ForPawn(PS->GetPawn());
            const bool Reverted=M&&M->Snapshot().DungeonRun.RunId==Run->RunId()&&!M->Snapshot().DungeonRun.bCompleted;
            const bool Saved=Reverted&&(It->Get()->IsLocalController()?M->SaveNow():PS->SaveShadowToHostDisk());
            if(!Saved)UE_LOG(LogTemp,Error,TEXT("[FinalBoss] Failed to persist cancelled return for %s"),*PS->GetName());
        }
}
void AColdSteelPlayerState::ClientTeamTravelSaveFailed_Implementation(FGuid TravelId,const FString& Reason)
{
    if(TravelId!=TeamTravelId)return;
    TeamTravelId.Invalidate();bTravelFlush=false;bTravelNeedsFreshUpload=false;
    if(auto* M=ColdSteelAuthority::Model(this))M->PostNotice(TEXT("换图未完成"),Reason);
}
void AColdSteelPlayerState::TickTeamTravel()
{
    if(TeamTravelId.IsValid()&&TeamTravelWorld.Get()!=GetWorld())
    {TeamTravelId.Invalidate();TeamDestination.Reset();TeamOptions.Reset();TeamTravelEntrance.Reset();bTravelFlush=bTravelReady=bTravelNeedsFreshUpload=false;bTeamReturnUnclaimedConfirmed=bTeamReturnCompletionStaged=false;}
    if(bTravelFlush&&!bInventoryRequestPending&&!bCampfirePending)
    {
        auto* PC=Cast<APlayerController>(GetOwner());
        if(PC&&PC->IsLocalController())
        {
            // A pre-existing upload/transaction can finish after preparation begins.
            // Drain it, then require a new snapshot containing the closed/cancelled actions.
            if(!HasAuthority()&&bTravelNeedsFreshUpload&&PendingUpload.IsEmpty())
            {bTravelNeedsFreshUpload=false;bHasLastSent=false;HeartbeatTimer=0.;}
            else if(HasAuthority()||(!bTravelNeedsFreshUpload&&bHasLastSent&&PendingUpload.IsEmpty()))
            {bTravelFlush=bTravelNeedsFreshUpload=false;ServerTeamTravelReady(TeamTravelId,HasAuthority()?0:PendingUploadId);}
        }
    }
    if(!HasAuthority()||TeamDestination.IsEmpty())return;
    if(GetWorld()->GetRealTimeSeconds()-TeamTravelStarted>60.)
    {AbortTeamTravel(TEXT("队员档案尚未保存，请稍后重试"));return;}
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PS=It->Get()->GetPlayerState<AColdSteelPlayerState>();PS&&PS->TeamTravelId==TeamTravelId&&(!PS->bTravelReady||!PS->InventoryReplyOutgoing.IsEmpty()))return;
    if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();Shared&&!Shared->FlushForTravel())
    {AbortTeamTravel(TEXT("共享库存保存失败或交易尚待恢复，暂时无法换图"));return;}
    if(auto* Smelting=GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>())
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(Smelting->IsCampfireSaveBlocked(*It))
        {AbortTeamTravel(TEXT("篝火交易尚待恢复，暂时无法换图"));return;}
    // Readiness may be followed by host-local edits or a death before another peer finishes uploading.
    // Commit the final authority state for every participant in this same game-thread transition.
    if(!TeamTravelEntrance.IsValid()||TeamTravelEntrance->GetWorld()!=GetWorld())
    {AbortTeamTravel(TEXT("换图入口已失效，请重新交互"));return;}
    auto* ReturnPortal=Cast<ASceneTestPortal>(TeamTravelEntrance.Get());
    auto* ReturnRun=ReturnPortal&&ReturnPortal->ActorHasTag(TEXT("DungeonFinalReturn"))?UDungeonRunSubsystem::Get(GetWorld()):nullptr;
    if(ReturnRun&&(!ReturnPortal->IsWithinInteractionRange(GetPawn())||!ReturnRun->CanUseFinalReturn()))
    {AbortTeamTravel(TEXT("返程入口已不可用，请靠近传送门重试"));return;}
    auto* Room=UDungeonRoomSubsystem::Get(GetWorld());
    if(ReturnRun&&!(Room?bClaimedFinalDungeonTreasure:ReturnRun->IsFinalTreasureLooted())&&!bTeamReturnUnclaimedConfirmed)
    {AbortTeamTravel(TEXT("队伍尚未领取奖励，请在返程门确认离开"));return;}
    if(ReturnRun&&!Room)
    {
        ReturnRun->MarkFinalReturnUsed(ReturnPortal);bTeamReturnCompletionStaged=ReturnRun->IsRunCompleted();
        if(!bTeamReturnCompletionStaged){AbortTeamTravel(TEXT("地牢返程进度尚未就绪"));return;}
    }
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PS=It->Get()->GetPlayerState<AColdSteelPlayerState>();PS&&PS->TeamTravelId==TeamTravelId&&!PS->SaveTeamTravelParticipant())return;
    for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(!It->FlushCampfirePersistence()){AbortTeamTravel(TEXT("建筑存档保存失败，请稍后重试"));return;}
    if(Room&&(TeamDestination.EndsWith(TEXT("L_Dungeon_Randomized"))||
        (bInDungeonRoom&&TeamDestination.EndsWith(TEXT("DayNight_Lighting")))))
    {
        const FGuid Batch=TeamTravelId;FString Reason;bool Accepted=false;
        if(TeamDestination.EndsWith(TEXT("L_Dungeon_Randomized")))
        {
            TArray<AColdSteelPlayerState*> Players;
            for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
                if(auto* PS=It->Get()->GetPlayerState<AColdSteelPlayerState>();PS&&PS->TeamTravelId==Batch)Players.Add(PS);
            Accepted=Room->QueueEntry(Players,Reason);
        }
        else Accepted=Room->ReturnPlayer(this,TeamTravelEntrance.Get(),bTeamReturnUnclaimedConfirmed,Reason);
        if(Accepted)FinishTravelBatch(Batch);else AbortTeamTravel(Reason);
        return;
    }
    FString URL=TeamDestination+(TeamOptions.IsEmpty()?FString():TEXT("?")+TeamOptions);
    if(auto* Session=GetGameInstance()->GetSubsystem<UColdSteelNetSessionSubsystem>())
    {
        const FString RoomOption=Session->TravelOption(GetWorld());
        if(!RoomOption.IsEmpty())URL+=TEXT("?")+RoomOption;
    }
    TeamDestination.Reset();
    if(auto* Mode=GetWorld()->GetAuthGameMode())Mode->bUseSeamlessTravel=true;
    const bool TravelAccepted=GetWorld()->ServerTravel(URL,false);
    if(!TravelAccepted)AbortTeamTravel(TEXT("换图请求未被服务器接受，请稍后重试"));
    // Retain the entrance/completion until the world changes or loading fails.
}
void AColdSteelPlayerState::CopyProperties(APlayerState* Other)
{
    Super::CopyProperties(Other);
    if(auto* Next=Cast<AColdSteelPlayerState>(Other))
    {Next->ShadowModel=ShadowModel;Next->SlotName=SlotName;Next->BoundProfileId=BoundProfileId;Next->SessionDoorKeys=SessionDoorKeys;Next->bServerDirty=true;Next->bGuestInitialized=bGuestInitialized;Next->bRestoreGuestAmmo=true;}
}
