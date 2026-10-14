#include "ColdSteelPlayerState.h"
#include "ColdSteelNetWorldSubsystem.h"
#include "ColdSteelNetSessionSubsystem.h"
#include "Engine/World.h"
#include "ColdSteelProfileTransfer.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/WoodworkingSystem.h"
#include "../Building/ForgingSystem.h"
#include "../Building/GunAssemblySystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelShopModel.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"

bool AColdSteelPlayerState::RequestCampfire(AColdSteelCampfire* Fire,uint8 Action,FName Recipe,int64 Batch)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    auto* M=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!PC||!PC->IsLocalController()||!IsValid(Fire)||!M||bCampfirePending||bInventoryRequestPending||Action>2)return false;
    if(TeamTravelId.IsValid()){CampfireResultText=TEXT("队伍正在保存档案，请稍候");return false;}
    if(!Fire->CanOperate(PC)){CampfireResultText=TEXT("请靠近篝火后操作");return false;}
    ++CampfireRequestId;CampfireResultRevision=-1;
    if(HasAuthority())
    {ServerCampfireRequest_Implementation(Fire,CampfireRequestId,Action,Recipe,Batch,M->Snapshot().CampfireInventoryRevision,PC->GetPawn());return true;}
    M->SyncRuntime();M->SetCampfireInventoryPending(true);
    bCampfirePending=true;bCampfireWaitingUpload=true;PendingCampfire=Fire;
    PendingCampfirePawn=PC->GetPawn();
    PendingCampfireAction=Action;PendingCampfireRecipe=Recipe;PendingCampfireBatch=Batch;
    CampfireResultText=TEXT("正在同步篝火操作…");
    // A fresh, frozen inventory precedes the intent on this same reliable actor channel.
    // Cancel an older partially sent upload; the new upload id replaces its server assembly.
    if(!ScratchSave)ScratchSave=NewObject<UColdSteelProfileSave>();
    ScratchSave->Profile=M->Snapshot();PendingUpload.Reset();
    const bool Encoded=ColdSteelProfileTransfer::SaveToBlob(ScratchSave,PendingUpload);
    PendingNormBlob=PendingUpload;PendingUploadId=++UploadCounter;NextChunkIndex=0;
    PendingSuper90Revision=Super90AppliedRevision;PendingUploadPawn=PC->GetPawn();
    PendingTotalChunks=FMath::DivideAndRoundUp(PendingUpload.Num(),ProfileChunkSize);
    if(!Encoded||PendingTotalChunks<=0||PendingTotalChunks>ColdSteelProfileTransfer::MaxChunks)
    {
        PendingUpload.Reset();bCampfirePending=bCampfireWaitingUpload=false;M->SetCampfireInventoryPending(false);
        CampfireResultText=TEXT("档案超过现有联机上传容量，篝火操作未发送");return false;
    }
    return true;
}
void AColdSteelPlayerState::DispatchCampfireAfterUpload()
{
    if(!bCampfireWaitingUpload)return;
    bCampfireWaitingUpload=false;
    const auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    ServerCampfireRequest(PendingCampfire.Get(),CampfireRequestId,PendingCampfireAction,
        PendingCampfireRecipe,PendingCampfireBatch,M?M->Snapshot().CampfireInventoryRevision:0,PendingCampfirePawn.Get());
}
void AColdSteelPlayerState::ServerCampfireRequest_Implementation(AColdSteelCampfire* Fire,int32 RequestId,
    uint8 Action,FName Recipe,int64 Batch,int64 InventoryRevision,APawn* RequestPawn)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!HasAuthority()||!PC||PC->PlayerState!=this)return;
    if(RequestId<=LastCampfireRequestId)return; // Same request never consumes twice.
    InvalidateTeamTravelReady();
    LastCampfireRequestId=RequestId;
    auto* M=PC->IsLocalController()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():ShadowModel.Get();
    FString Reason;AVoxelBuildWorld* W=nullptr;FIntVector Cell;
    const double Now=GetWorld()->GetTimeSeconds();
    if(!RequestPawn||RequestPawn!=PC->GetPawn())Reason=TEXT("角色已变化，请重新操作篝火");
    else if(!M)Reason=TEXT("操作者档案尚未同步");
    else if(M->HasUnconfirmedTransactionSave())Reason=TEXT("交易保存结果待恢复，当前不能继续操作");
    else if(Action>2||Batch<1||Batch>5)Reason=TEXT("篝火请求无效");
    else if(Now-LastCampfireRequestAt<.15)Reason=TEXT("操作过快，请稍候");
    else if(!IsValid(Fire)||Fire->GetWorld()!=GetWorld()||!Fire->CanOperate(PC)||!Fire->ResolveStation(W,Cell))
        Reason=TEXT("篝火已移除、不可达或距离过远");
    else if(InventoryRevision!=M->Snapshot().CampfireInventoryRevision)Reason=TEXT("库存已更新，请同步后重试");
    else if(auto* System=GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>())
    {
        LastCampfireRequestAt=Now;
        System->ExecuteCampfire(W,Cell,M,PC->IsLocalController()?nullptr:this,Action,Recipe,Batch,Reason);
        Fire->PublishSharedState(true);
    }
    if(ShadowModel){ShadowMirrorTimer=3.f;TickShadowMirror(0.f);ForceNetUpdate();}
    const int64 Revision=M?M->Snapshot().CampfireInventoryRevision:InventoryRevision;
    if(PC->IsLocalController())CampfireResultText=Reason;
    else ClientCampfireResult(RequestId,Revision,Reason);
}
void AColdSteelPlayerState::ClientCampfireResult_Implementation(int32 RequestId,int64 InventoryRevision,const FString& Reason)
{
    if(!bCampfirePending||RequestId!=CampfireRequestId)return;
    CampfireResultRevision=InventoryRevision;CampfireResultText=Reason;FinishCampfireReceipt();
}
void AColdSteelPlayerState::FinishCampfireReceipt()
{
    if(!bCampfirePending||CampfireResultRevision<0)return;
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!M||M->Snapshot().CampfireInventoryRevision<CampfireResultRevision)return;
    bCampfirePending=bCampfireWaitingUpload=false;PendingCampfire.Reset();PendingCampfirePawn.Reset();
    M->SetCampfireInventoryPending(false);
    // Persist the receipt locally too; the host slot remains authoritative if this fails.
    M->CommitState(M->Snapshot());bHasLastSent=false;HeartbeatTimer=0;
}
void AColdSteelPlayerState::PrepareForDisconnect()
{
    if(!HasAuthority()||bDisconnectPrepared)return;
    if(auto* Session=GetWorld()->GetSubsystem<UColdSteelNetWorldSubsystem>())Session->RememberGuestKeys(BoundProfileId,SessionDoorKeys);
    CancelPendingNetworkCast();
    const bool Closed=CloseStationSessions();
    // Preserve unfinished paid jobs too when closing cannot complete (e.g. pawn already gone).
    const bool Saved=!ShadowModel||SaveShadowToHostDisk();
    if(auto* Session=GetGameInstance()->GetSubsystem<UColdSteelNetSessionSubsystem>())
        Session->RememberGuestProfile(GetWorld(),BoundProfileId,ShadowModel);
    bDisconnectPrepared=Closed&&Saved;
}
void AColdSteelPlayerState::EndPlay(const EEndPlayReason::Type Reason)
{
    if(HasAuthority()&&!TeamDestination.IsEmpty()&&Reason==EEndPlayReason::Destroyed)
        AbortTeamTravel(TEXT("换图发起者已离开，请重新发起"));
    PrepareForDisconnect();
    const auto* OwningPlayer=Cast<APlayerController>(GetOwner());
    if(bWasLocalOwner||(OwningPlayer&&OwningPlayer->IsLocalController())||(!OwningPlayer&&GetNetMode()==NM_Client&&(bCampfirePending||bInventoryRequestPending)))
    {
        if(auto* Wood=GetGameInstance()?GetGameInstance()->GetSubsystem<UWoodworkingSystem>():nullptr)Wood->NetworkSessionEnded();
        if(auto* Forge=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>():nullptr)Forge->NetworkSessionEnded();
        if(auto* Assembly=GetGameInstance()?GetGameInstance()->GetSubsystem<UGunAssemblySystem>():nullptr)Assembly->NetworkSessionEnded();
        if(auto* Shop=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelShopModel>():nullptr)Shop->EndSession();
        if(auto* M=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
        {
            M->SetCampfireInventoryPending(false);
            M->bWarehouseOpen=false;
            M->EndStorageSession();
        }
    }
    bCampfirePending=bCampfireWaitingUpload=bInventoryRequestPending=bInventoryWaitingUpload=false;
    PendingUpload.Reset();InventoryReplyIncoming.Reset();InventoryRequestPawn.Reset();
    Super::EndPlay(Reason);
}
