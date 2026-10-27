#include "ColdSteelPlayerState.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelNetWorldSubsystem.h"
#include "ColdSteelNetSessionSubsystem.h"
#include "Engine/World.h"
#include "ColdSteelProfileTransfer.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/WoodworkingSystem.h"
#include "../Building/AlchemySystem.h"
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
    bCampfireResultSucceeded=false;
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
    // Reuse the inventory channel's acknowledged baseline. A matching inventory
    // already belongs to the server; no full profile upload is needed per log/meal.
    const auto Baseline=InventoryBaseline(M->Snapshot());
    const auto& Profile=M->Snapshot();
    const bool AppearanceReady=bHasUploadedAppearance&&Profile.PlayerHeadId==UploadedHeadId&&Profile.PlayerHairId==UploadedHairId;
    if(AppearanceReady&&!Baseline.IsEmpty()&&Baseline==AcknowledgedInventoryBaseline)
    {
        PendingUpload.Reset();PendingNormBlob.Reset();bCampfireWaitingUpload=false;
        ServerCampfireRequest(Fire,CampfireRequestId,Action,Recipe,Batch,Profile.CampfireInventoryRevision,PC->GetPawn());
        return true;
    }
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
    FString Reason;bool Success=false;AVoxelBuildWorld* W=nullptr;FIntVector Cell;
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
        Success=System->ExecuteCampfire(W,Cell,M,PC->IsLocalController()?nullptr:this,Action,Recipe,Batch,Reason);
        Fire->PublishSharedState(true);
    }
    if(ShadowModel){ShadowMirrorTimer=3.f;TickShadowMirror(0.f);ForceNetUpdate();}
    const int64 Revision=M?M->Snapshot().CampfireInventoryRevision:InventoryRevision;
    if(PC->IsLocalController()){CampfireResultText=Reason;bCampfireResultSucceeded=Success;}
    else ClientCampfireResult(RequestId,Revision,Success,Reason);
}
void AColdSteelPlayerState::ClientCampfireResult_Implementation(int32 RequestId,int64 InventoryRevision,bool Success,const FString& Reason)
{
    if(!bCampfirePending||RequestId!=CampfireRequestId)return;
    CampfireResultRevision=InventoryRevision;CampfireResultText=Reason;bCampfireResultSucceeded=Success;FinishCampfireReceipt();
}
void AColdSteelPlayerState::FinishCampfireReceipt()
{
    if(!bCampfirePending||CampfireResultRevision<0)return;
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!M||M->Snapshot().CampfireInventoryRevision<CampfireResultRevision)return;
    bCampfirePending=bCampfireWaitingUpload=false;PendingCampfire.Reset();PendingCampfirePawn.Reset();
    M->SetCampfireInventoryPending(false);
    // This revision was returned by the server and applied before releasing the
    // lock. Subsequent unchanged campfire operations can use the same baseline.
    if(bCampfireResultSucceeded&&M->Snapshot().CampfireInventoryRevision==CampfireResultRevision)
        AcknowledgedInventoryBaseline=InventoryBaseline(M->Snapshot());
    // Persist the receipt locally too; the host slot remains authoritative if this fails.
    M->CommitState(M->Snapshot());
    if(bCampfireResultSucceeded)AcknowledgeInventoryProfile();
    else {bHasLastSent=false;HeartbeatTimer=0;}
}
void AColdSteelPlayerState::PrepareForDisconnect()
{
    if(!HasAuthority()||bDisconnectPrepared)return;
    if(auto* Session=GetWorld()->GetSubsystem<UColdSteelNetWorldSubsystem>())Session->RememberGuestKeys(BoundProfileId,SessionDoorKeys);
    CancelPendingNetworkCast();
    // Settle confirmed hits before the guest profile is saved or remembered.
    APawn* CastPawn=GetPawn()?GetPawn():ShadowPawn.Get();
    if(CastPawn)if(auto* Fire=CastPawn->FindComponentByClass<UFPSFireMagicComponent>())Fire->FinishDragonBreathForRemoval();
    if(CastPawn)if(auto* Electric=CastPawn->FindComponentByClass<UFPSElectricMagicComponent>())Electric->FinishDomainForRemoval();
    if(CastPawn)if(auto* Blizzard=CastPawn->FindComponentByClass<UFPSBlizzardComponent>())Blizzard->FinishZonesForRemoval();
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
        if(auto* Alchemy=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>():nullptr)Alchemy->NetworkEnded();
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
