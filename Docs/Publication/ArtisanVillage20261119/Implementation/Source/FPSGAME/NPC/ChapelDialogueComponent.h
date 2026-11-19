#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Tasks/TaskTrackingSubsystem.h"
#include "ChapelDialogueComponent.generated.h"

class AChapelNun;
class APawn;
class APlayerController;
class AVillageArtisanMerchant;
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
    void TradeWithArtisan();
    void TradeWithMerchant();
    void RequestSmithTraining();
    int32 SmithTrainingStage() const;
    void RequestCarpenterTraining();
    int32 CarpenterTrainingStage() const;
    bool CanCollectTrainingSupplies() const;
    bool CanAcceptArtisanTask(uint32 Session,const AVillageArtisanMerchant* Teacher) const;
    void FinishArtisanInventoryRequest(uint32 Session,bool Success,const FString& Reason);
    virtual void BeginPlay() override;
    virtual void AppendTrackedTasks(const APawn* Viewer,TArray<FTrackedTaskView>& Out) override;
    bool IsBlacksmith() const;
    bool IsCarpenter() const;
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
    friend class AVillageNetworkAudit;
    UPROPERTY(Transient) TObjectPtr<UColdSteelNpcDialogue> Screen;
    TWeakObjectPtr<AChapelNun> LocalNun, AuthorityNun;
    TWeakObjectPtr<AActor> LocalMerchant, AuthorityMerchant;
    TWeakObjectPtr<APawn> AuthorityConversationPawn;
    TWeakObjectPtr<APawn> ConversationPawn;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    uint32 LocalSession=0, AuthoritySession=0;
    bool bPending=false,bReturnCursor=false,bOwnsInput=false;
    int32 PreviousState=INDEX_NONE;
    int32 PreviousPlayerLevel=INDEX_NONE;
    FName LastNunAction;
    FTimerHandle WatchTimer;
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
    void OpenMerchant(AActor* Merchant);
    bool Present(AFPSGAMEPlayerController& PC);
    void ReleaseLocal();
    UFUNCTION(Server,Reliable) void ServerOpen(uint32 Session,ATemperateHillsWorld* Village,APawn* Initiator);
    UFUNCTION(Server,Reliable) void ServerOpenMerchant(uint32 Session,AActor* Merchant,APawn* Initiator);
    UFUNCTION(Server,Reliable) void ServerClose(uint32 Session);
    UFUNCTION(Server,Reliable) void ServerAction(uint32 Session,FName Action);
    UFUNCTION(Client,Reliable) void ClientOpened(uint32 Session,bool Accepted,const FString& Reason);
    UFUNCTION(Client,Reliable) void ClientResult(uint32 Session,bool Success,const FString& Result);
};
