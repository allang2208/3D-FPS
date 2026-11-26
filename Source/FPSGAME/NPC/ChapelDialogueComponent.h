#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Tasks/TaskTrackingSubsystem.h"
#include "ChapelDialogueComponent.generated.h"

class AChapelNun;
namespace ArtisanVillageProbe { struct FRun; }
class APawn;
class APlayerController;
class AVillageArtisanMerchant;
class AVillageHerbalist;
class AVillageTavernKeeper;
class AFPSGAMEPlayerController;
class ATemperateHillsWorld;
class UColdSteelNpcDialogue;

/** Each owning controller has a separate conversation. The server validates reach and progression. */
UCLASS()
class FPSGAME_API UChapelDialogueComponent : public UActorComponent, public ITaskTrackingSource
{
    GENERATED_BODY()
public:
    UChapelDialogueComponent();
    void Open(AChapelNun* Nun);
    void OpenArtisan(AVillageArtisanMerchant* Artisan);
    void OpenHerbalist(AVillageHerbalist* Herbalist);
    void OpenTavernKeeper(AVillageTavernKeeper* Keeper);
    void OpenMerchant(AActor* Merchant);
    bool CanStartConversation(const AActor* Speaker) const;
    void BeginFirstAid(AVillageArtisanMerchant* Artisan);
    bool CanAidFocusedArtisan(const AVillageArtisanMerchant* Artisan) const;
    bool ReleaseFirstAid();
    TOptional<float> FirstAidProgress(const AActor* Target) const;
    void TradeWithArtisan();
    void TradeWithMerchant();
    void EndHerbalistTrade();
    void RequestSmithTraining();
    int32 SmithTrainingStage() const;
    void RequestCarpenterTraining();
    int32 CarpenterTrainingStage() const;
    bool CanCollectTrainingSupplies() const;
    bool CanAcceptArtisanTask(uint32 Session,const AVillageArtisanMerchant* Teacher) const;
    void FinishArtisanInventoryRequest(uint32 Session,bool Success,const FString& Reason);
    virtual void BeginPlay() override;
    virtual void AppendTrackedTasks(const APawn* Viewer,TArray<FTrackedTaskView>& Out) override;
    virtual bool ReadJournalDetails(const APawn* Viewer, const FTrackedTaskView& Task, FTaskJournalDetails& Out) const override;
    virtual void AppendJournalTasks(const APawn* Viewer,TArray<FTrackedTaskView>& Out) override;
    bool IsBlacksmith() const;
    bool IsCarpenter() const;
    bool IsHerbalist() const;
    bool IsMasterArtisan() const;
    uint16 WorkshopRanks() const;
    int64 WorkshopBalance() const;
    void BuySiegeUpgrade(int32 Index,int32 ExpectedRank);
    bool IsBaker() const;
    bool IsMillKeeper() const;
    bool IsTavernKeeper() const;
    void Close();
    bool IsOpen() const { return Screen!=nullptr; }
    void RequestAction(FName Action);
    bool PlanUnlocked(FName Plan) const;
    bool BuildingRepaired(FName Plan) const;
    bool HolyLightLearned() const;
    bool CanLearnHolyLight(FString& Reason) const;
    bool IsPending() const { return bPending; }
    FString Message;
    const FString& NunActionMessage(FName Action) const;
    FSimpleMulticastDelegate OnChanged;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend struct FSiegeDrawerReview;
    friend class AVillageNetworkAudit;
    friend struct ArtisanVillageProbe::FRun;
    UPROPERTY(Transient) TObjectPtr<UColdSteelNpcDialogue> Screen;
    TWeakObjectPtr<AChapelNun> LocalNun, AuthorityNun;
    TWeakObjectPtr<AActor> LocalMerchant, AuthorityMerchant;
    TWeakObjectPtr<APawn> AuthorityConversationPawn;
    TWeakObjectPtr<APawn> ConversationPawn;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    uint32 LocalSession=0, AuthoritySession=0;
    bool bPending=false,bReturnCursor=false,bOwnsInput=false;
    bool bTradingWithHerbalist=false;
    int32 PreviousState=INDEX_NONE;
    int64 PreviousWorkshopBalance=-1;
    uint16 ConfirmedWorkshopRanks=0;
    int64 ConfirmedWorkshopCredits=0, ConfirmedWorkshopDebits=0;
    int32 PreviousPlayerLevel=INDEX_NONE;
    FName LastNunAction;
    bool bLastNunActionSucceeded=false;
    FTimerHandle WatchTimer;
    FTimerHandle LocalAidTimer, AuthorityAidTimer;
    TWeakObjectPtr<AVillageArtisanMerchant> LocalAidTarget, AuthorityAidTarget;
    TWeakObjectPtr<APawn> LocalAidPawn, AuthorityAidPawn;
    uint32 LocalAidSerial=0, AuthorityAidSerial=0;
    double LocalAidStart=0., AuthorityAidStart=0.;
    bool bLocalAidConfirmed=false, bAuthorityAidConfirmed=false;
    void UpdateLocalFirstAid();
    void UpdateAuthorityFirstAid();
    void EndLocalFirstAid();
    void EndAuthorityFirstAid();
    UFUNCTION(Server,Reliable) void ServerBeginFirstAid(uint32 Serial,AVillageArtisanMerchant* Target);
    UFUNCTION(Server,Reliable) void ServerEndFirstAid(uint32 Serial,bool CompletedHold);
    UFUNCTION(Client,Reliable) void ClientEndFirstAid(uint32 Serial);
    void AppendLessons(const APawn* Viewer, TArray<FTrackedTaskView>& Out, ETaskViewPurpose Purpose);
    struct FLessonTrackerState
    {
        bool bWasActive=false;
        double ShowCompletionUntil=0.;
    };
    FString LastTrackerProfile;
    FLessonTrackerState SmithTracker, CarpenterTracker;
    void RequestArtisanTask();
    void AcceptArtisanTraining(uint32 Session,FName Action);
    void Watch();
    bool InReach(const AActor* Speaker) const;
    AActor* LocalSpeaker() const;
    void SetLocalFacing(APlayerController* Player);
    void SetAuthorityMerchant(AActor* Merchant);
    void EndAuthorityConversation();
    void WatchAuthorityHerbalist();
    FTimerHandle HerbalistWatchTimer;
    bool Present(AFPSGAMEPlayerController& PC);
    void DismissDialogueScreen();
    void ReleaseLocal();
    UFUNCTION(Server,Reliable) void ServerOpen(uint32 Session,ATemperateHillsWorld* Village,APawn* Initiator);
    UFUNCTION(Server,Reliable) void ServerOpenMerchant(uint32 Session,AActor* Merchant,APawn* Initiator);
    UFUNCTION(Server,Reliable) void ServerClose(uint32 Session);
    UFUNCTION(Client,Reliable) void ClientWorkshopResult(uint32 Session,bool Success,uint16 Ranks,int64 Credits,int64 Debits,const FString& Result);
    UFUNCTION(Server,Reliable) void ServerBuySiegeUpgrade(uint32 Session,int32 Index,int32 ExpectedRank);
    UFUNCTION(Server,Reliable) void ServerAction(uint32 Session,FName Action);
    UFUNCTION(Client,Reliable) void ClientOpened(uint32 Session,bool Accepted,const FString& Reason);
    UFUNCTION(Client,Reliable) void ClientEndHerbalistConversation(uint32 Session);
    UFUNCTION(Client,Reliable) void ClientResult(uint32 Session,bool Success,const FString& Result);
};
