#include "ChapelDialogueComponent.h"
#include "VillageMasterArtisan.h"
#include "ChapelNun.h"
#include "ResidentConversation.h"
#include "VillageArtisanMerchant.h"
#include "VillageBaker.h"
#include "VillageMillKeeper.h"
#include "VillageHerbalist.h"
#include "VillageTavernKeeper.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelNpcDialogue.h"
#include "../UI/ColdSteelDialogueViewport.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../WorldGeneration/TemperateHillsChapel.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
bool IsVillageSpeaker(const AActor* Speaker)
{
    return IsValid(Speaker) && (Speaker->IsA<AVillageArtisanMerchant>() ||
        Speaker->IsA<AVillageBaker>() || Speaker->IsA<AVillageTavernKeeper>() || Speaker->IsA<AVillageHerbalist>() ||
        Speaker->IsA<AVillageMillKeeper>() || Speaker->IsA<AVillageMasterArtisan>());
}
}

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
    ResidentConversation::SetLocalFacing(LocalSpeaker(),Player);
}
bool UChapelDialogueComponent::CanStartConversation(const AActor* Speaker) const
{
    const auto* PC = Cast<AFPSGAMEPlayerController>(GetOwner());
    if (!PC || Screen || bPending || bTradingWithHerbalist || !PC->CanOpenGameMenu() || !InReach(Speaker)) return false;
    if (const auto* Nun = Cast<AChapelNun>(Speaker))
        return TemperateHillsChapel::FindNun(Cast<ATemperateHillsWorld>(Nun->GetParentActor())) == Nun;
    return IsVillageSpeaker(Speaker);
}
void UChapelDialogueComponent::Open(AChapelNun* Nun)
{
    if(!CanStartConversation(Nun))return;
    auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    auto* Village = Cast<ATemperateHillsWorld>(Nun->GetParentActor());
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
bool UChapelDialogueComponent::IsHerbalist() const
{
    return Cast<AVillageHerbalist>(LocalMerchant.Get()) != nullptr;
}
void UChapelDialogueComponent::OpenHerbalist(AVillageHerbalist* Herbalist)
{
    OpenMerchant(Herbalist);
}
bool UChapelDialogueComponent::IsTavernKeeper() const
{
    return Cast<AVillageTavernKeeper>(LocalMerchant.Get()) != nullptr;
}
bool UChapelDialogueComponent::IsMasterArtisan() const
{
    return Cast<AVillageMasterArtisan>(LocalMerchant.Get())!=nullptr;
}
uint16 UChapelDialogueComponent::WorkshopRanks() const
{
    const auto* Master=Cast<AVillageMasterArtisan>(LocalMerchant.Get());
    const auto* Village=Master?Master->Village():nullptr;
    return FMath::Max(ConfirmedWorkshopRanks,Village?Village->GetSiegeRanks():uint16(0));
}
int64 UChapelDialogueComponent::WorkshopBalance() const
{
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model)return 0;
    const auto& Profile=Model->ProfileView();
    // The owner receipt can arrive before the normal replicated wallet mirror.
    return Model->SoulBalance()+FMath::Max<int64>(0,ConfirmedWorkshopCredits-Profile.ServerSoulCredits)
        -FMath::Max<int64>(0,ConfirmedWorkshopDebits-Profile.ServerSoulDebits);
}
void UChapelDialogueComponent::BuySiegeUpgrade(int32 Index,int32 ExpectedRank)
{
    if(!Screen || !IsMasterArtisan() || bPending)return;
    bPending=true;
    Message.Reset();
    OnChanged.Broadcast();
    ServerBuySiegeUpgrade(LocalSession,Index,ExpectedRank);
}
void UChapelDialogueComponent::ServerBuySiegeUpgrade_Implementation(uint32 Session,int32 Index,int32 ExpectedRank)
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    const auto* Master=Cast<AVillageMasterArtisan>(AuthorityMerchant.Get());
    auto* Village=Master?Master->Village():nullptr;
    if(!Session || Session!=AuthoritySession || !PC || PC->GetPawn()!=AuthorityConversationPawn.Get() || !Village || !InReach(Master))
    {ClientResult(Session,false,TEXT("请靠近工匠大师重新交谈。"));return;}
    FText Reason;
    const bool Bought=Village->PurchaseSiegeUpgrade(PC->GetPawn(),Index,ExpectedRank,Reason);
    const auto* Wallet=ColdSteelAuthority::ForPawn(PC->GetPawn());
    ClientWorkshopResult(Session,Bought,Village->GetSiegeRanks(),Wallet?Wallet->ProfileView().ServerSoulCredits:0,
        Wallet?Wallet->ProfileView().ServerSoulDebits:0,Bought?TEXT("升级完成，村庄内的同类机械已生效。"):Reason.ToString());
}
void UChapelDialogueComponent::ClientWorkshopResult_Implementation(uint32 Session,bool Success,uint16 Ranks,int64 Credits,int64 Debits,const FString& Result)
{
    if(Session!=LocalSession || !IsMasterArtisan())return;
    ConfirmedWorkshopRanks=Ranks;
    ConfirmedWorkshopCredits=Credits;
    ConfirmedWorkshopDebits=Debits;
    ClientResult_Implementation(Session,Success,Result);
}
bool UChapelDialogueComponent::IsBaker() const
{
    return Cast<AVillageBaker>(LocalMerchant.Get()) != nullptr;
}
bool UChapelDialogueComponent::IsMillKeeper() const
{
    return Cast<AVillageMillKeeper>(LocalMerchant.Get()) != nullptr;
}
void UChapelDialogueComponent::OpenTavernKeeper(AVillageTavernKeeper* Keeper)
{
    OpenMerchant(Keeper);
}
void UChapelDialogueComponent::OpenMerchant(AActor* Merchant)
{
    if(!CanStartConversation(Merchant))return;
    auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    ConfirmedWorkshopRanks=0;ConfirmedWorkshopCredits=0;ConfirmedWorkshopDebits=0;
    ConversationPawn=PC->GetPawn();LocalMerchant=Merchant;Message.Reset();bPending=true;
    ServerOpenMerchant(++LocalSession,Merchant,ConversationPawn.Get());
}
void UChapelDialogueComponent::ServerOpenMerchant_Implementation(uint32 Session,AActor* Merchant,APawn* Initiator)
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    const bool Accepted=Session!=0 && PC && PC->GetPawn()==Initiator && IsVillageSpeaker(Merchant) && InReach(Merchant);
    AuthorityNun.Reset();
    AuthorityConversationPawn=Accepted?Initiator:nullptr;
    AuthoritySession=Accepted?Session:0;
    SetAuthorityMerchant(Accepted ? Merchant : nullptr);
    ClientOpened(Session,Accepted,Accepted?FString():TEXT("请靠近对方后再交谈。"));
}
void UChapelDialogueComponent::ServerOpen_Implementation(uint32 Session,ATemperateHillsWorld* Village,APawn* Initiator)
{
    // The nun is assembled locally by the replicated village on each peer.
    auto* Nun = TemperateHillsChapel::FindNun(Village);
    const auto* PC=Cast<APlayerController>(GetOwner());
    const bool Accepted = Session != 0 && PC && PC->GetPawn()==Initiator && InReach(Nun);
    SetAuthorityMerchant(nullptr);
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
    if(!Screen||!Seller||!PC||!PC->IsLocalController()||IsMillKeeper())return;
    if(PC->GetPawn()!=ConversationPawn.Get()||!InReach(Seller)){Close();return;}
    auto* HUD=PC->GetColdSteelHUD();
    if(!HUD)return;
    if (auto* Herbalist = Cast<AVillageHerbalist>(Seller))
    {
        if (HUD->IsShopOpen()) return;
        // The HUD takes input, but the current buyer still holds her patrol in place.
        DismissDialogueScreen();
        bTradingWithHerbalist = true;
        if (!HUD->OpenHerbalistShop(Herbalist)) EndHerbalistTrade();
        return;
    }
    // The shop lives in the normal HUD layer and owns its inventory input mode.
    Close();
    if(auto* Baker=Cast<AVillageBaker>(Seller))HUD->OpenBakerShop(Baker);
    else if(auto* Keeper=Cast<AVillageTavernKeeper>(Seller))HUD->OpenTavernShop(Keeper);
    else if(auto* Artisan=Cast<AVillageArtisanMerchant>(Seller))HUD->OpenArtisanShop(Artisan);
}
void UChapelDialogueComponent::EndHerbalistTrade()
{
    if (bTradingWithHerbalist) Close();
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
void UChapelDialogueComponent::DismissDialogueScreen()
{
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
    bOwnsInput=false;
}
void UChapelDialogueComponent::ReleaseLocal()
{
    GetWorld()->GetTimerManager().ClearTimer(WatchTimer);
    if(bOwnsInput || bTradingWithHerbalist)SetLocalFacing(nullptr);
    ConversationPawn.Reset();
    LocalNun.Reset();
    LocalMerchant.Reset();
    Hills.Reset();
    LastNunAction=NAME_None;
    DismissDialogueScreen();
    bPending=false;
    if (bTradingWithHerbalist)
    {
        bTradingWithHerbalist = false;
        auto* PC = Cast<AFPSGAMEPlayerController>(GetOwner());
        if (auto* HUD = PC ? PC->GetColdSteelHUD() : nullptr; HUD && HUD->IsShopOpen()) HUD->ToggleShop();
    }
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
    EndAuthorityConversation();
}

void UChapelDialogueComponent::EndAuthorityConversation()
{
    SetAuthorityMerchant(nullptr);
    AuthorityNun.Reset();AuthorityConversationPawn.Reset();AuthoritySession=0;
}

void UChapelDialogueComponent::SetAuthorityMerchant(AActor* Merchant)
{
    auto* PC = Cast<APlayerController>(GetOwner());
    auto* Previous = Cast<AVillageHerbalist>(AuthorityMerchant.Get());
    auto* Next = Cast<AVillageHerbalist>(Merchant);
    AuthorityMerchant = Merchant;
    if (Previous && Previous != Next) Previous->SetConversationParticipant(PC, false);
    if (!Next)
    {
        GetWorld()->GetTimerManager().ClearTimer(HerbalistWatchTimer);
    }
    else if (Next != Previous)
    {
        Next->SetConversationParticipant(PC, true);
        GetWorld()->GetTimerManager().SetTimer(HerbalistWatchTimer, this,
            &UChapelDialogueComponent::WatchAuthorityHerbalist, .4f, true);
    }
}

void UChapelDialogueComponent::WatchAuthorityHerbalist()
{
    const auto* PC = Cast<APlayerController>(GetOwner());
    if (PC && PC->GetPawn() == AuthorityConversationPawn.Get() && InReach(AuthorityMerchant.Get())) return;
    const uint32 Ending = AuthoritySession;
    EndAuthorityConversation();
    ClientEndHerbalistConversation(Ending);
}

void UChapelDialogueComponent::ClientEndHerbalistConversation_Implementation(uint32 Session)
{
    if (Session == LocalSession) Close();
}
void UChapelDialogueComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    EndLocalFirstAid();
    EndAuthorityFirstAid();
    if (GetOwner() && GetOwner()->HasAuthority()) EndAuthorityConversation();
    if(auto* Tracking=GetWorld()->GetSubsystem<UTaskTrackingSubsystem>())Tracking->UnregisterSource(this);
    ReleaseLocal();
    Super::EndPlay(Reason);
}
bool UChapelDialogueComponent::PlanUnlocked(FName Plan) const{return Hills.IsValid()&&Hills->IsVillagePlanUnlocked(Plan);}
bool UChapelDialogueComponent::BuildingRepaired(FName Plan) const
{
    if(!Hills.IsValid())return false;
    if(Plan==TEXT("wall"))return Hills->IsVillageWallRepaired();
    if(Plan==TEXT("high_wall"))return Hills->HasVillageHighWall();
    if(Plan==TEXT("blacksmith"))return Hills->IsVillageBlacksmithRepaired();
    if(Plan==TEXT("carpenter"))return Hills->IsVillageCarpenterRepaired();
    if(Plan==TEXT("herbalist"))return Hills->IsHerbalistRepaired();
    if(Plan==TEXT("windmill"))return Hills->IsWindmillRepaired();
    if(Plan==TEXT("bakery"))return Hills->IsBakeryRepaired();
    if(Plan==TEXT("gunshop"))return Hills->IsGunshopRepaired();
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
    if(!Screen && !bTradingWithHerbalist)return;
    const auto* PC=Cast<AFPSGAMEPlayerController>(GetOwner());
    auto* Instance=GetWorld()->GetGameInstance();
    auto* M=Instance->GetSubsystem<UColdSteelStatusModel>();
    const auto* Loading=Instance->GetSubsystem<UTransitLoadingSubsystem>();
    // While shopping the HUD checks the seller's reach and closes the shop when it is lost.
    if(!PC||PC->GetPawn()!=ConversationPawn.Get()||(!bTradingWithHerbalist && !InReach(LocalSpeaker()))||
       (M&&M->ProfileView().Health<=0)||(Loading&&Loading->OwnsPlayerCursor())){Close();return;}
    if (bTradingWithHerbalist)
    {
        const auto* HUD = PC->GetColdSteelHUD();
        if (!HUD || !HUD->IsShopOpen()) EndHerbalistTrade();
        return;
    }
    if(LocalMerchant.IsValid())
    {
        if(IsMasterArtisan())
        {
            const int32 Ranks=WorkshopRanks();
            const int64 Balance=WorkshopBalance();
            if(PreviousState!=Ranks || PreviousWorkshopBalance!=Balance)
            {PreviousState=Ranks;PreviousWorkshopBalance=Balance;OnChanged.Broadcast();}
            return;
        }
        if (!LocalMerchant->IsA<AVillageArtisanMerchant>()) return;
        const uint8 Stage=static_cast<uint8>(IsCarpenter()?CarpenterTrainingStage():SmithTrainingStage());
        const uint8 State=Stage|(CanCollectTrainingSupplies()?8:0);
        if(PreviousState!=State){PreviousState=State;OnChanged.Broadcast();}
        return;
    }
    const int32 State=(PlanUnlocked(TEXT("wall"))?1:0)|(PlanUnlocked(TEXT("blacksmith"))?2:0)|(HolyLightLearned()?4:0)
        |(BuildingRepaired(TEXT("wall"))?8:0)|(BuildingRepaired(TEXT("blacksmith"))?16:0)
        |(BuildingRepaired(TEXT("carpenter"))?32:0)|(BuildingRepaired(TEXT("tavern"))?64:0)
        |(BuildingRepaired(TEXT("herbalist"))?128:0)|(PlanUnlocked(TEXT("village_construction"))?256:0)
        |(BuildingRepaired(TEXT("high_wall"))?512:0)|(BuildingRepaired(TEXT("windmill"))?1024:0)
        |(BuildingRepaired(TEXT("bakery"))?2048:0)|(BuildingRepaired(TEXT("gunshop"))?4096:0)
        |(PlanUnlocked(TEXT("garrison_mechanics"))?8192:0);
    const int32 PlayerLevel=M?M->ProfileView().Level:0;
    if(State!=PreviousState || PlayerLevel!=PreviousPlayerLevel)
    {
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
    if (LastNunAction!=Action) return Empty;
    if (!bPending && Action!=TEXT("holyLight"))
    {
        // The controller's reliable reply and the village's replicated state can arrive in either order.
        const bool bResearch=Action==TEXT("village_construction") || Action==TEXT("garrison_mechanics");
        const bool bComplete=bResearch ? PlanUnlocked(Action) : BuildingRepaired(Action);
        if (bLastNunActionSucceeded!=bComplete) return Empty;
    }
    return Message;
}
void UChapelDialogueComponent::ServerAction_Implementation(uint32 Session,FName Action)
{
    if(Action==TEXT("smith.training")||Action==TEXT("carpenter.training")){AcceptArtisanTraining(Session,Action);return;}
    auto* PC = Cast<APlayerController>(GetOwner());
    auto* Nun = AuthorityNun.Get();
    if(!Session||Session!=AuthoritySession||!PC||PC->GetPawn()!=AuthorityConversationPawn.Get()||!InReach(Nun))
    {ClientResult(Session,false,TEXT("交谈已结束，请重新与修女交谈。"));return;}
    bool Success=false;FString Result;
    if(Action==TEXT("wall")||Action==TEXT("blacksmith")||Action==TEXT("carpenter")||Action==TEXT("tavern")||
        Action==TEXT("herbalist")||Action==TEXT("village_construction")||Action==TEXT("high_wall")||Action==TEXT("windmill")||
        Action==TEXT("bakery")||Action==TEXT("gunshop")||Action==TEXT("garrison_mechanics"))
    {
        auto* Village=Cast<ATemperateHillsWorld>(Nun->GetParentActor());
        FText Error;Success=IsValid(Village)&&Village->UnlockVillagePlan(Action,Error);
        if(!Success)Result=Error.IsEmpty()?TEXT("村庄尚未准备好，请稍后重试。"):Error.ToString();
        else if(Action==TEXT("wall"))Result=TEXT("城墙已修复。按 B 打开「村庄建筑」，可建造矮墙和木质大门。");
        else if(Action==TEXT("high_wall"))Result=TEXT("高墙已升级，东西村门已换用升降铁闸。已解锁石砌高墙、石城门和登墙石阶建造。");
        else if(Action==TEXT("blacksmith"))Result=TEXT("铁匠铺已修复并恢复使用，村庄建设进度已保存。");
        else if(Action==TEXT("carpenter"))Result=TEXT("木工工坊已修复，可以使用一楼的木工工作台了。");
        else if(Action==TEXT("herbalist"))Result=TEXT("草药铺已修复，可以使用店内的炼药工作台了。");
        else if(Action==TEXT("windmill"))Result=TEXT("风车已修复，村庄建设进度已保存。");
        else if(Action==TEXT("bakery"))Result=TEXT("面包屋已修复，可以到柜台找面包师买面包了。");
        else if(Action==TEXT("gunshop"))Result=TEXT("枪店已修复，南侧长屋的一楼枪械工作台已开放。");
        else if(Action==TEXT("village_construction"))Result=TEXT("防御工事已解锁。村庄获赠工坊旁的一座高塔，现在也可以自行建塔。");
        else if(Action==TEXT("garrison_mechanics"))Result=TEXT("机械工坊已在东门马厩对面落成。按 B 打开「村庄建筑」，可建造弩炮、投石机和热油锅。");
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
{
    if(Session!=LocalSession)return;
    bPending=false;
    bLastNunActionSucceeded=Success;
    Message=Result;
    OnChanged.Broadcast();
}
