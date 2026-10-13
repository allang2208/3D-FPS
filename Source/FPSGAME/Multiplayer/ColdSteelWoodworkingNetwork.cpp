#include "ColdSteelPlayerState.h"
#include "ColdSteelProfileTransfer.h"
#include "../Building/WoodworkingSystem.h"
#include "Engine/GameInstance.h"
#include "Engine/NetConnection.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

void AColdSteelPlayerState::TickWoodNetwork()
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!HasAuthority()||!PC||PC->IsLocalController()||!GuestWood)return;
    auto* Connection=PC->GetNetConnection();if(!Connection||!Connection->IsNetReady())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(WoodOutgoing.IsEmpty()&&Now>=WoodPublishAt&&(bWoodDirty||GuestWood->IsTickable()))
    {
        WoodPublishAt=Now+.5;
        if(GuestWood->NetworkOpen()&&!StationReach(TEXT("wood")))
            GuestWood->NetworkUnavailable(TEXT("已离开木工工作台或角色无法操作，本次加工已停止"));
        if(ColdSteelProfileTransfer::SaveToBlob(GuestWood->NetworkState(),WoodOutgoing))
        {WoodChunk=0;++WoodTransfer;WoodOutgoingAck=WoodAuthoritySequence;WoodOutgoingPawn=GetPawn();bWoodDirty=GuestWood->IsTickable();}
    }
    if(WoodOutgoing.IsEmpty()||!InventoryReplyOutgoing.IsEmpty())return;
    const double Rate=FMath::Min(8192.,double(Connection->CurrentNetSpeed)*.1);
    if(Rate<=0||Now<WoodSendAt)return;
    const int32 Total=FMath::DivideAndRoundUp(WoodOutgoing.Num(),1024),Offset=WoodChunk*1024;
    TArray<uint8> Bytes;Bytes.Append(WoodOutgoing.GetData()+Offset,FMath::Min(1024,WoodOutgoing.Num()-Offset));
    ClientWoodChunk(WoodTransfer,WoodOutgoingAck,WoodChunk,Total,Bytes,WoodOutgoingPawn.Get());WoodSendAt=Now+1280./Rate;
    if(++WoodChunk==Total)WoodOutgoing.Reset();
}

void AColdSteelPlayerState::ClientWoodChunk_Implementation(int32 Transfer,uint32 Ack,int32 Index,int32 Total,const TArray<uint8>& Bytes,APawn* SourcePawn)
{
    if(!SourcePawn||SourcePawn!=GetPawn())return;
    if(Total<=0||Total>ColdSteelProfileTransfer::MaxChunks||Index<0||Index>=Total||Bytes.IsEmpty()||Bytes.Num()>1024)return;
    if(Index==0){WoodReceiving=Transfer;WoodTotal=Total;WoodIncomingAck=Ack;WoodIncoming.Reset();}
    if(Transfer!=WoodReceiving||Total!=WoodTotal||Ack!=WoodIncomingAck||Index*1024!=WoodIncoming.Num())return;
    WoodIncoming.Append(Bytes);if(Index+1!=Total)return;
    // Keep in-flight prediction. A fresh response follows after the authority
    // consumes the newer inputs; old completion/close packets cannot undo them.
    if(Ack==WoodInputSerial)
    {
        auto* State=NewObject<UColdSteelWoodNetState>();
        if(ColdSteelProfileTransfer::BlobToSaveObject(WoodIncoming,State))
            GetGameInstance()->GetSubsystem<UWoodworkingSystem>()->ApplyNetworkState(State);
    }
    WoodIncoming.Reset();
}
