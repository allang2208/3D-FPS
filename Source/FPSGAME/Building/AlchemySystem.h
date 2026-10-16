#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "AlchemyTypes.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "AlchemySystem.generated.h"

class UColdSteelStatusModel;
class AVoxelBuildPrefabActor;

/** Server-owned brewing rules and paid batch. The UI never grants items. */
UCLASS()
class FPSGAME_API UColdSteelAlchemySystem : public UGameInstanceSubsystem,public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override {return !IsTemplate()&&(bActive||bSaveRetry||bHasDeferredState);}
    virtual UWorld* GetTickableGameObjectWorld() const override {return GetWorld();}
    virtual TStatId GetStatId() const override {RETURN_QUICK_DECLARE_CYCLE_STAT(UColdSteelAlchemySystem,STATGROUP_Tickables);}
    UColdSteelAlchemySystem* CreateNetworkSession(UColdSteelStatusModel* Model,const FString& GuestSaveSlot);
    const TArray<FAlchemyRecipe>& Recipes() const {return Catalog;}
    const FAlchemyRecipe* Find(FName Id) const;
    const FAlchemyRecipe* Recipe() const;
    const FColdSteelAlchemyJob& Job() const;
    UColdSteelStatusModel* Model() const;
    bool HasJob() const {return !Job().Id.IsEmpty();}
    bool Active() const {return bActive;}
    bool Pending() const {return bPending;}
    bool Saving() const;
    bool Bottling() const {return bBottling;}
    bool TimerRunning() const {return bTimerRunning;}
    bool ToolBusy() const;
    int32 Heat() const {return HeatLevel;}
    int32 StepIndex() const;
    bool CanGrind(int32 Ingredient) const;
    float Infusion() const;
    FString Observation() const;
    const FString& Message() const {return Notice;}
    bool CanStart(FName Id,FString& Reason) const;
    bool CanResume(FString& Reason) const;
    bool Open(AActor* Station,APawn* Pawn);
    bool Transaction(const FString& Operation,FName Id,AActor* Station,APawn* Pawn,FString& Reason);
    void AuthorityTransactionFinished(bool Committed,const FString& Reason);
    bool Start(FName Id);
    bool Resume();
    bool Suspend();
    bool Claim();
    TArray<FColdSteelItem> DiscardRefund() const;
    bool Discard();
    bool Bottle();
    bool Input(EAlchemyOp Op,int32 Index=0,float Value=0);
    bool Reachable() const;
    AVoxelBuildPrefabActor* Workbench() const {return Bench.Get();}
    void NetworkFinished(const FString& Operation,bool Success,const FString& Reason);
    void ApplyNetworkState(const FColdSteelAlchemyNetState& State);
    FColdSteelAlchemyNetState NetworkState() const;
    void NetworkEnded();
    static bool DecodeRecipe(const FString& Json,FAlchemyRecipe& Result);
private:
    friend class AAlchemyManualNetAuditGameMode;
    bool LoadJob();
    bool Pay(FName Id);
    bool Acquire();
    void Release();
    bool Save();
    bool ProcessInput(EAlchemyOp Op,int32 Index,float Value);
    void Advance(float Delta);
    void Fault(const FString& Text,float Penalty);
    void Publish();
    int64 Reserved(const FString& Item) const;
    void OpenUnits(const FString& Item,int32 Count);
    bool Finish();
    bool Request(const FString& Operation,FName Id=NAME_None);
    void ApplyDeferredState();
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> NetworkModel;
    TArray<FAlchemyRecipe> Catalog;
    FAlchemyRecipe Accepted;
    FColdSteelAlchemyJob Working;
    FColdSteelAlchemyJob TransactionBefore;
    TWeakObjectPtr<AVoxelBuildPrefabActor> Bench;
    TWeakObjectPtr<APawn> WorkingPawn;
    TWeakObjectPtr<APawn> RequestPawn;
    FColdSteelAlchemyNetState DeferredState;
    bool bHasDeferredState=false;
    FString Notice,RestoredId,NetworkSaveSlot;
    bool bActive=false,bPending=false,bSaveRetry=false;
    bool bBottling=false,bTimerRunning=false,bHourglassInverted=false;
    bool bAuthorityTransactionPrepared=false;
    int32 HeatLevel=0,ToolIndex=0,Serial=0,BookPage=0;
    EAlchemyOp HeldTool=EAlchemyOp::Stop;
    double InputUntil=0,NextActionAt=0,NextSaveAt=0,NextPublishAt=0,TimerStartsAt=0;
    uint64 NetworkStateSerial=0,RequestStateSerial=0;
    int64 LastNetworkInventoryRevision=-1,RequestInventoryRevision=-1;
    float StirDirection=0,StirPhase=0,ActionAt=0,TimerFraction=0,TimerElapsed=0;
};
