#include "ChapelDialogueComponent.h"
#include "ChapelNun.h"
#include "ResidentConversation.h"
#include "VillageArtisanMerchant.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelNpcDialogue.h"
#include "../UI/ColdSteelDialogueViewport.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../WorldGeneration/TemperateHillsChapel.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "TimerManager.h"

UChapelDialogueComponent::UChapelDialogueComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=false;
}
bool UChapelDialogueComponent::InReach(const AActor* Speaker) const
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    return PC && ResidentConversation::CanReach(PC->GetPawn(),Speaker);
}
AActor* UChapelDialogueComponent::LocalSpeaker() const
{
    if(auto* Merchant=LocalMerchant.Get())return Merchant;
    return LocalNun.Get();
}
void UChapelDialogueComponent::SetLocalFacing(APlayerController* Player)
{
    if(auto* Artisan=Cast<AVillageArtisanMerchant>(LocalMerchant.Get()))Artisan->SetLocalConversation(Player);
    else if(auto* Nun=LocalNun.Get())Nun->SetLocalConversation(Player);
}
void UChapelDialogueComponent::Open(AChapelNun* Nun)
{
    auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner());
    if(!PC||!PC->CanOpenGameMenu()||Screen||bPending||!InReach(Nun))return;
    auto* Village = Cast<ATemperateHillsWorld>(Nun->GetParentActor());
    if (TemperateHillsChapel::FindNun(Village) != Nun) return;
    Hills=Village;ConversationPawn=PC->GetPawn();LocalNun=Nun;Message.Reset();bPending=true;
    ServerOpen(++LocalSession,Village,ConversationPawn.Get());
}
bool UChapelDialogueComponent::IsBlacksmith() const
{
    const auto* Artisan=Cast<AVillageArtisanMerchant>(LocalMerchant.Get());
    return Artisan && !Artisan->IsCarpenterMerchant();
}
bool UChapelDialogueComponent::IsCarpenter() const
{
    const auto* Artisan=Cast<AVillageArtisanMerchant>(LocalMerchant.Get());
    return Artisan && Artisan->IsCarpenterMerchant();
}
void UChapelDialogueComponent::OpenArtisan(AVillageArtisanMerchant* Artisan)
{
    OpenMerchant(Artisan);
}
void UChapelDialogueComponent::OpenMerchant(AActor* Merchant)
{
    auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner());
    if(!PC||!PC->CanOpenGameMenu()||Screen||bPending||!InReach(Merchant))return;
    ConversationPawn=PC->GetPawn();LocalMerchant=Merchant;Message.Reset();bPending=true;
    ServerOpenMerchant(++LocalSession,Merchant,ConversationPawn.Get());
}
void UChapelDialogueComponent::ServerOpenMerchant_Implementation(uint32 Session,AActor* Merchant,APawn* Initiator)
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    const bool IsMerchant=IsValid(Merchant) && Merchant->IsA<AVillageArtisanMerchant>();
    const bool Accepted=Session!=0 && PC && PC->GetPawn()==Initiator && IsMerchant && InReach(Merchant);
    AuthorityNun.Reset();
    AuthorityMerchant=Accepted?Merchant:nullptr;
    AuthorityConversationPawn=Accepted?Initiator:nullptr;
    AuthoritySession=Accepted?Session:0;
    ClientOpened(Session,Accepted,Accepted?FString():TEXT("请靠近对方后再交谈。"));
}
void UChapelDialogueComponent::ServerOpen_Implementation(uint32 Session,ATemperateHillsWorld* Village,APawn* Initiator)
{
    // The nun is assembled locally by the replicated village on each peer.
    auto* Nun = TemperateHillsChapel::FindNun(Village);
    const auto* PC=Cast<APlayerController>(GetOwner());
    const bool Accepted = Session != 0 && PC && PC->GetPawn()==Initiator && InReach(Nun);
    AuthorityMerchant.Reset();
    AuthorityNun=Accepted?Nun:nullptr;
    AuthorityConversationPawn=Accepted?Initiator:nullptr;
    AuthoritySession=Accepted?Session:0;
    ClientOpened(Session,Accepted,Accepted?FString():TEXT("请靠近修女后再交谈。"));
}
void UChapelDialogueComponent::TradeWithArtisan()
{
    if(Cast<AVillageArtisanMerchant>(LocalMerchant.Get()))TradeWithMerchant();
}
void UChapelDialogueComponent::TradeWithMerchant()
{
    auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner());
    auto* Seller=LocalMerchant.Get();
    if(!Screen||!Seller||!PC||!PC->IsLocalController())return;
    if(PC->GetPawn()!=ConversationPawn.Get()||!InReach(Seller)){Close();return;}
    auto* HUD=PC->GetColdSteelHUD();
    if(!HUD)return;
    // The shop lives in the normal HUD layer and owns its inventory input mode.
    Close();
    if(auto* Artisan=Cast<AVillageArtisanMerchant>(Seller))HUD->OpenArtisanShop(Artisan);
}
void UChapelDialogueComponent::ClientOpened_Implementation(uint32 Session,bool Accepted,const FString& Reason)
{
    if(Session!=LocalSession||!bPending)return;
    bPending=false;Message=Reason;
    auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner());
    if(!Accepted||!PC||PC->GetPawn()!=ConversationPawn.Get()||!PC->CanOpenGameMenu()||!InReach(LocalSpeaker())||!Present(*PC)){Close();return;}
    SetLocalFacing(PC);
}
bool UChapelDialogueComponent::Present(AFPSGAMEPlayerController& PC)
{
    Screen=CreateWidget<UColdSteelNpcDialogue>(&PC);
    if(!Screen)return false;
    Screen->Configure(this);
    auto* Layer=PC.GetGameInstance()->GetSubsystem<UColdSteelDialogueViewport>();
    if(!Layer||!Layer->Show(Screen))return false;
    if(auto* Pawn=Cast<AFPSGAMECharacter>(PC.GetPawn()))Pawn->PrepareForPanelInput();
    bReturnCursor=PC.bShowMouseCursor;bOwnsInput=true;
    PC.SetIgnoreMoveInput(true);PC.SetIgnoreLookInput(true);PC.bShowMouseCursor=true;
    FInputModeUIOnly Mode;Mode.SetWidgetToFocus(Screen->TakeWidget());Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);PC.SetInputMode(Mode);
    Screen->SetUserFocus(&PC);
    PreviousState=INDEX_NONE;GetWorld()->GetTimerManager().SetTimer(WatchTimer,this,&UChapelDialogueComponent::Watch,.25f,true);
    return true;
}
void UChapelDialogueComponent::ReleaseLocal()
{
    GetWorld()->GetTimerManager().ClearTimer(WatchTimer);
    if(bOwnsInput)SetLocalFacing(nullptr);
    ConversationPawn.Reset();
    LocalNun.Reset();
    LocalMerchant.Reset();
    Hills.Reset();
    LastNunAction=NAME_None;
    if(Screen)
    {
        if(auto* Instance=Screen->GetGameInstance())
            if(auto* Layer=Instance->GetSubsystem<UColdSteelDialogueViewport>())Layer->Hide(Screen);
        Screen=nullptr;
    }
    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner());PC&&PC->IsLocalController())
    {
        if(bOwnsInput)
        {
            PC->SetIgnoreMoveInput(false);
            PC->SetIgnoreLookInput(false);
            PC->FlushPressedKeys();
            const auto* Loading=PC->GetGameInstance()?PC->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>():nullptr;
            if(!Loading||!Loading->OwnsPlayerCursor())
            {
                PC->bShowMouseCursor=bReturnCursor;
                if(bReturnCursor)
                {
                    FInputModeGameAndUI Mode;
                    Mode.SetHideCursorDuringCapture(false);
                    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
                    PC->SetInputMode(Mode);
                }
                else PC->SetInputMode(FInputModeGameOnly());
            }
        }
    }
    bOwnsInput=false;bPending=false;
}
void UChapelDialogueComponent::Close()
{
    const bool bNotifyServer=!LocalNun.IsExplicitlyNull()||!LocalMerchant.IsExplicitlyNull();
    const uint32 Closing=LocalSession++;
    ReleaseLocal();
    if(bNotifyServer)ServerClose(Closing);
}
void UChapelDialogueComponent::ServerClose_Implementation(uint32 Session)
{
    if(Session!=AuthoritySession)return;
    AuthorityNun.Reset();AuthorityMerchant.Reset();AuthorityConversationPawn.Reset();AuthoritySession=0;
}
void UChapelDialogueComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(auto* Tracking=GetWorld()->GetSubsystem<UTaskTrackingSubsystem>())Tracking->UnregisterSource(this);
    ReleaseLocal();
    Super::EndPlay(Reason);
}
bool UChapelDialogueComponent::PlanUnlocked(FName Plan) const{return Hills.IsValid()&&Hills->IsVillagePlanUnlocked(Plan);}
bool UChapelDialogueComponent::BuildingRepaired(FName Plan) const
{
    if(!Hills.IsValid())return false;
    if(Plan==TEXT("wall"))return Hills->IsVillageWallRepaired();
    if(Plan==TEXT("blacksmith"))return Hills->IsVillageBlacksmithRepaired();
    if(Plan==TEXT("carpenter"))return Hills->IsVillageCarpenterRepaired();
    return Plan==TEXT("tavern")&&Hills->IsTavernRepaired();
}
bool UChapelDialogueComponent::HolyLightLearned() const
{const auto* M=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();return M&&M->IsSkillLearned(TEXT("holyLight"));}
bool UChapelDialogueComponent::CanLearnHolyLight(FString& Reason) const
{
    const auto* M=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!M){Reason=TEXT("角色档案尚未就绪");return false;}
    if(M->IsSkillLearned(TEXT("holyLight"))){Reason=TEXT("已习得圣光");return false;}
    const auto* Node=ColdSteelSkillTree::Get().Find(TEXT("holyLight"));
    if(!Node){Reason=TEXT("圣光资料尚未就绪");return false;}
    const auto& P=M->ProfileView();for(const auto& R:Node->Requires)if(!ColdSteelSkillTree::RequirementMet(P,R)){Reason=TEXT("需要角色达到 Lv15");return false;}
    Reason=TEXT("由修女传授，无需消耗技能点");return true;
}
void UChapelDialogueComponent::Watch()
{
    if(!Screen)return;
    const auto* PC=Cast<APlayerController>(GetOwner());
    auto* Instance=GetWorld()->GetGameInstance();
    auto* M=Instance->GetSubsystem<UColdSteelStatusModel>();
    const auto* Loading=Instance->GetSubsystem<UTransitLoadingSubsystem>();
    if(!PC||PC->GetPawn()!=ConversationPawn.Get()||!InReach(LocalSpeaker())||(M&&M->ProfileView().Health<=0)||(Loading&&Loading->OwnsPlayerCursor())){Close();return;}
    if(LocalMerchant.IsValid())
    {
        const uint8 Stage=static_cast<uint8>(IsCarpenter()?CarpenterTrainingStage():SmithTrainingStage());
        const uint8 State=Stage|(CanCollectTrainingSupplies()?8:0);
        if(PreviousState!=State){PreviousState=State;OnChanged.Broadcast();}
        return;
    }
    const uint8 State=(PlanUnlocked(TEXT("wall"))?1:0)|(PlanUnlocked(TEXT("blacksmith"))?2:0)|(HolyLightLearned()?4:0)
        |(BuildingRepaired(TEXT("wall"))?8:0)|(BuildingRepaired(TEXT("blacksmith"))?16:0)
        |(BuildingRepaired(TEXT("carpenter"))?32:0)|(BuildingRepaired(TEXT("tavern"))?64:0);
    const int32 PlayerLevel=M?M->ProfileView().Level:0;
    if(State!=PreviousState || PlayerLevel!=PreviousPlayerLevel)
    {
        // A world reset can revoke a repair while this player's tree is open.
        // Discard its old receipt when rebuilding the actionable detail card.
        constexpr uint8 RepairStates = 8 | 16 | 32 | 64;
        if (PreviousState != INDEX_NONE && !bPending && (PreviousState & ~State & RepairStates))
            Message.Reset();
        PreviousPlayerLevel=PlayerLevel;PreviousState=State;OnChanged.Broadcast();
    }
}
void UChapelDialogueComponent::RequestAction(FName Action)
{
    if(!Screen||!LocalNun.IsValid()||bPending)return;
    bPending=true;
    LastNunAction=Action;
    Message=TEXT("正在确认…");
    OnChanged.Broadcast();
    ServerAction(LocalSession,Action);
}
const FString& UChapelDialogueComponent::NunActionMessage(FName Action) const
{
    static const FString Empty;
    return LastNunAction==Action ? Message : Empty;
}
void UChapelDialogueComponent::ServerAction_Implementation(uint32 Session,FName Action)
{
    if(Action==TEXT("smith.training")||Action==TEXT("carpenter.training")){AcceptArtisanTraining(Session,Action);return;}
    auto* PC = Cast<APlayerController>(GetOwner());
    auto* Nun = AuthorityNun.Get();
    if(!Session||Session!=AuthoritySession||!PC||PC->GetPawn()!=AuthorityConversationPawn.Get()||!InReach(Nun))
    {ClientResult(Session,false,TEXT("交谈已结束，请重新与修女交谈。"));return;}
    bool Success=false;FString Result;
    if(Action==TEXT("wall")||Action==TEXT("blacksmith")||Action==TEXT("carpenter")||Action==TEXT("tavern"))
    {
        auto* Village=Cast<ATemperateHillsWorld>(Nun->GetParentActor());
        FText Error;Success=IsValid(Village)&&Village->UnlockVillagePlan(Action,Error);
        if(!Success)Result=Error.IsEmpty()?TEXT("村庄尚未准备好，请稍后重试。"):Error.ToString();
        else if(Action==TEXT("wall"))Result=TEXT("围墙已整体修复，村庄建设进度已保存。");
        else if(Action==TEXT("blacksmith"))Result=TEXT("铁匠铺已修复并恢复使用，村庄建设进度已保存。");
        else if(Action==TEXT("carpenter"))Result=TEXT("木工工坊已修复，可以使用一楼的木工工作台了。");
        else Result=TEXT("酒馆已修复，村庄建设进度已保存。");
    }
    else if(Action==TEXT("holyLight"))
    {
        auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();
        auto* Model=PC->IsLocalController()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():PS?PS->GetShadowModel():nullptr;
        if(Model && Model->RuntimePawn()==PC->GetPawn()){Success=Model->LearnHolyLightFromTrainer(Nun);Result=Success?TEXT("你已习得圣光。可在技能树中查看，并拖入快捷栏使用。"):Model->ResultMessage();}
        else Result=TEXT("角色档案正在同步，请稍后重试。");
    }
    else Result=TEXT("未知的交谈选项。");
    ClientResult(Session,Success,Result);
}
void UChapelDialogueComponent::ClientResult_Implementation(uint32 Session,bool Success,const FString& Result)
{if(Session!=LocalSession)return;bPending=false;Message=Result;OnChanged.Broadcast();}
