#include "ColdSteelPlayerState.h"
#include "ColdSteelAuthorityContext.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"

void AColdSteelPlayerState::ClientBeginRoomEntry_Implementation(FGuid Token,FGuid Instance,APawn* Pawn)
{
    if(!Token.IsValid()||!Instance.IsValid())return;
    RoomTransferToken=Token;RoomTransferInstance=Instance;RoomTransferPawn=Pawn;bRoomEntryAckSent=false;
    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner())){PC->CloseExpedition();PC->CloseWoodworking();}
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
        Loading->BeginRoomTransition(FSimpleDelegate::CreateWeakLambda(this,[this,Token](){ServerCancelRoomEntry(Token);}));
}
void AColdSteelPlayerState::TickRoomEntry()
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->IsLocalController()||!RoomTransferToken.IsValid()||bRoomEntryAckSent)return;
    if(!RoomTransferPawn.IsValid()||RoomTransferPawn.Get()!=GetPawn())
    {bRoomEntryAckSent=true;ServerCancelRoomEntry(RoomTransferToken);return;}
    auto* Room=UDungeonRoomSubsystem::Get(GetWorld());
    if(Room&&Room->LocalAssemblyReady(RoomTransferInstance))
    {bRoomEntryAckSent=true;ServerRoomEntryReady(RoomTransferToken,RoomTransferInstance,GetPawn());}
}
void AColdSteelPlayerState::ServerRoomEntryReady_Implementation(FGuid Token,FGuid Instance,APawn* Pawn)
{
    if(auto* Room=UDungeonRoomSubsystem::Get(GetWorld()))Room->AcknowledgeEntry(this,Token,Instance,Pawn);
}
void AColdSteelPlayerState::ServerCancelRoomEntry_Implementation(FGuid Token)
{
    if(auto* Room=UDungeonRoomSubsystem::Get(GetWorld()))Room->CancelEntry(this,Token);
}
void AColdSteelPlayerState::ClientFinishRoomEntry_Implementation(FGuid Token,bool Dungeon,const FString& Reason)
{
    // Listen authority clears its pending token before dispatching this local RPC.
    if(RoomTransferToken.IsValid()&&Token!=RoomTransferToken)return;
    RoomTransferToken.Invalidate();RoomTransferInstance.Invalidate();RoomTransferPawn.Reset();bRoomEntryAckSent=false;
    bInDungeonRoom=Dungeon;
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
    {if(Reason.IsEmpty())Loading->FinishRoomTransition();else Loading->CancelTransition();}
    if(auto* Room=UDungeonRoomSubsystem::Get(GetWorld()))Room->RefreshPresentation();
    if(!Reason.IsEmpty())if(auto* M=ColdSteelAuthority::Model(this))M->PostNotice(TEXT("出征未完成"),Reason);
}
void AColdSteelPlayerState::ClientRoomRegionChanged_Implementation(bool Dungeon)
{
    bInDungeonRoom=Dungeon;
    if(auto* Room=UDungeonRoomSubsystem::Get(GetWorld()))Room->RefreshPresentation();
}
void AColdSteelPlayerState::ClientTeamTravelFinished_Implementation(FGuid TravelId)
{
    if(TeamTravelId.IsValid()&&TeamTravelId!=TravelId)return;
    TeamTravelId.Invalidate();TeamDestination.Reset();TeamOptions.Reset();TeamTravelEntrance.Reset();
    bTravelFlush=bTravelReady=bTravelNeedsFreshUpload=false;
    bTeamReturnUnclaimedConfirmed=bTeamReturnCompletionStaged=false;
}
void AColdSteelPlayerState::FinishTravelBatch(FGuid Id)
{
    if(!HasAuthority())return;
    for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)if(It->TeamTravelId==Id)
    {
        It->ClientTeamTravelFinished(Id);
        It->TeamTravelId.Invalidate();It->TeamDestination.Reset();It->TeamOptions.Reset();It->TeamTravelEntrance.Reset();
        It->bTravelFlush=It->bTravelReady=It->bTravelNeedsFreshUpload=false;
        It->bTeamReturnUnclaimedConfirmed=It->bTeamReturnCompletionStaged=false;
    }
}
