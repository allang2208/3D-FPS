#include "ColdSteelPlayerState.h"
#include "ColdSteelAuthorityContext.h"
#include "ColdSteelNetSessionSubsystem.h"
#include "ColdSteelSharedInventorySubsystem.h"
#include "../Building/SmeltingSystem.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
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

bool AColdSteelPlayerState::RequestTeamTravel(AActor* Entrance)
{
    if(GetNetMode()==NM_Standalone||!IsValid(Entrance))return false;
    ServerTeamTravel(Entrance);return true;
}
void AColdSteelPlayerState::ServerTeamTravel_Implementation(AActor* Entrance)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->GetPawn()||!IsValid(Entrance)||Entrance->GetWorld()!=GetWorld())return;
    const bool WasCursor=PC->bShowMouseCursor;PC->bShowMouseCursor=false;
    const bool Focused=ColdSteelWorldInteraction::IsFocused(PC->GetPawn(),Entrance,300);
    PC->bShowMouseCursor=WasCursor;
    FString Destination,Options;
    if(auto* Portal=Cast<ASceneTestPortal>(Entrance))
    {if(!Portal->IsWithinInteractionRange(PC->GetPawn()))return;Destination=Portal->DestinationMap();Options=Portal->TravelOptions();}
    else if(ColdSteelWorldInteraction::IsExpeditionAltar(Entrance)&&Focused)
        Destination=TEXT("/Game/GameMaps/L_Dungeon_Randomized");
    if(Destination.IsEmpty()||!FPackageName::DoesPackageExist(Destination))return;
    for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)if(!It->TeamDestination.IsEmpty())return;
    TeamDestination=Destination;TeamOptions=Options;TeamTravelStarted=GetWorld()->GetRealTimeSeconds();
    const FGuid TravelId=FGuid::NewGuid();
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* State=It->Get()->GetPlayerState<AColdSteelPlayerState>())
        {State->TeamTravelId=TravelId;State->TeamTravelWorld=GetWorld();State->TeamTravelPawn=It->Get()->GetPawn().Get();State->bTravelReady=false;State->ClientPrepareTeamTravel(TravelId);}
}
void AColdSteelPlayerState::ClientPrepareTeamTravel_Implementation(FGuid TravelId)
{
    if(!TravelId.IsValid())return;
    TeamTravelId=TravelId;TeamTravelWorld=GetWorld();
    bTravelFlush=true;bTravelNeedsFreshUpload=true;bHasLastSent=false;HeartbeatTimer=0;
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
    if(auto* M=ColdSteelAuthority::Model(this))M->PostNotice(TEXT("队伍换图"),TEXT("正在保存队伍档案，请稍候"));
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
    if(auto* Fire=GetPawn()->FindComponentByClass<UFPSFireMagicComponent>())Fire->FinishDragonBreathForRemoval();
    if(auto* Electric=GetPawn()->FindComponentByClass<UFPSElectricMagicComponent>())Electric->FinishDomainForRemoval();
    if(auto* Blizzard=GetPawn()->FindComponentByClass<UFPSBlizzardComponent>())Blizzard->FinishZonesForRemoval();
    if(!CloseStationSessions()){AbortTeamTravel(TEXT("工作站结算或档案保存失败，请稍后重试"));return false;}
    M->SyncRuntime();
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
    for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)
    {
        if(!It->TeamTravelId.IsValid())continue;
        const FGuid Cancelled=It->TeamTravelId;
        It->TeamDestination.Reset();It->TeamOptions.Reset();It->bTravelReady=false;
        It->ClientTeamTravelSaveFailed(Cancelled,Reason);It->TeamTravelId.Invalidate();
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
    {TeamTravelId.Invalidate();TeamDestination.Reset();TeamOptions.Reset();bTravelFlush=bTravelReady=bTravelNeedsFreshUpload=false;}
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
        if(auto* PS=It->Get()->GetPlayerState<AColdSteelPlayerState>();PS&&(!PS->bTravelReady||!PS->InventoryReplyOutgoing.IsEmpty()))return;
    if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();Shared&&!Shared->FlushForTravel())
    {AbortTeamTravel(TEXT("共享库存保存失败或交易尚待恢复，暂时无法换图"));return;}
    if(auto* Smelting=GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>())
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(Smelting->IsCampfireSaveBlocked(*It))
        {AbortTeamTravel(TEXT("篝火交易尚待恢复，暂时无法换图"));return;}
    // Readiness may be followed by host-local edits or a death before another peer finishes uploading.
    // Commit the final authority state for every participant in this same game-thread transition.
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PS=It->Get()->GetPlayerState<AColdSteelPlayerState>();PS&&!PS->SaveTeamTravelParticipant())return;
    for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(!It->FlushCampfirePersistence()){AbortTeamTravel(TEXT("建筑存档保存失败，请稍后重试"));return;}
    FString URL=TeamDestination+(TeamOptions.IsEmpty()?FString():TEXT("?")+TeamOptions);
    if(auto* Session=GetGameInstance()->GetSubsystem<UColdSteelNetSessionSubsystem>())
    {
        const FString RoomOption=Session->TravelOption(GetWorld());
        if(!RoomOption.IsEmpty())URL+=TEXT("?")+RoomOption;
    }
    TeamDestination.Reset();
    if(auto* Mode=GetWorld()->GetAuthGameMode())Mode->bUseSeamlessTravel=true;
    if(!GetWorld()->ServerTravel(URL,false))AbortTeamTravel(TEXT("换图请求未被服务器接受，请稍后重试"));
}
void AColdSteelPlayerState::CopyProperties(APlayerState* Other)
{
    Super::CopyProperties(Other);
    if(auto* Next=Cast<AColdSteelPlayerState>(Other))
    {Next->ShadowModel=ShadowModel;Next->SlotName=SlotName;Next->BoundProfileId=BoundProfileId;Next->SessionDoorKeys=SessionDoorKeys;Next->bServerDirty=true;Next->bGuestInitialized=bGuestInitialized;Next->bRestoreGuestAmmo=true;}
}
