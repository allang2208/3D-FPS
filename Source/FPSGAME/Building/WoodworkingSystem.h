#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "CraftingSystem.h"
#include "WoodworkingMask.h"
#include "WoodworkingSaw.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "WoodworkingSystem.generated.h"

struct FWoodworkingPattern
{
    FName Id,CraftRecipe;
    FString Name,Description,Instructions,Difficulty;
    TArray<FVector2D> Outline,Connections;
    double Seconds=90,RequiredClearance=.98,MaximumDamage=.12;
};
enum class EWoodworkingPhase : uint8 {Preview,Running,Complete,Failed,Delivered,Abandoned};
// Keep legacy wire values; only Craft can start a new session.
enum class EWoodworkingMode : uint8 {Practice,Challenge,Craft};

/** Owns cutting and one paid workpiece. Inventory settlement is saved atomically. */
UCLASS()
class FPSGAME_API UWoodworkingSystem : public UGameInstanceSubsystem,public FTickableGameObject
{
    GENERATED_BODY()
public:
    UWoodworkingSystem* CreateNetworkSession(class UColdSteelStatusModel* Model);
    void NetworkDelivered(bool Success);
    void NetworkTransactionFinished(const FString& Operation,bool Success,const FString& Reason);
    void NetworkSessionEnded();
    const FColdSteelWoodworkingJob& Job() const;
    bool HasPendingJob() const {return !Job().Id.IsEmpty();}
    bool TransactionPending() const {return bClaiming;}
    bool GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const;
    bool Discard();
    bool Settle();
    bool CanResume() const;
    bool Resume();
    bool Suspend();
    class UColdSteelWoodNetState* NetworkState();
    bool ApplyNetworkState(const UColdSteelWoodNetState* State);
    bool NetworkOpen() const {return bOpen;}
    void NetworkUnavailable(const FString& Reason);
    virtual void Initialize(FSubsystemCollectionBase&) override;
    virtual void Deinitialize() override;
    virtual void Tick(float) override;
    virtual bool IsTickable() const override {return !IsTemplate()&&Phase==EWoodworkingPhase::Running;}
    virtual bool IsTickableWhenPaused() const override {return true;}
    virtual UWorld* GetTickableGameObjectWorld() const override {return GetWorld();}
    virtual TStatId GetStatId() const override {RETURN_QUICK_DECLARE_CYCLE_STAT(UWoodworkingSystem,STATGROUP_Tickables);}
    bool Open(bool PracticeOnly);
    bool Close();
    bool Select(FName Id);
    bool CanStart(bool Practice,FString& Reason) const;
    bool Start(bool Practice);
    bool CanStartMode(EWoodworkingMode Mode,FString& Reason) const;
    bool StartMode(EWoodworkingMode Mode);
    bool Restart();
    bool IsTimed() const {return SessionMode!=EWoodworkingMode::Practice;}
    EWoodworkingMode Mode() const {return SessionMode;}
    FString RecipeSummary() const;
    FString ResultSummary() const;
    bool BeginFeed();
    bool MoveBoard(FVector2D WorkDelta);
    bool RotateBoard(int32 Direction,bool Fine=false);
    bool ToggleMotor();
    bool MotorRunning() const {return Phase==EWoodworkingPhase::Running&&bMotorOn;}
    bool IsAdjusting() const {return (Phase==EWoodworkingPhase::Preview||Phase==EWoodworkingPhase::Running)&&!bMotorOn;}
    bool Feeding() const {return bFeeding;}
    const ColdSteelWoodworking::FSawSettings& SawSettings() const {return SawRules;}
    const ColdSteelWoodworking::FBoardPose& Pose() const {return BoardPose;}
    FVector2D BoardToWork(FVector2D Point) const {return BoardPose.ToWork(Point,BoardCenter());}
    FVector2D WorkToBoard(FVector2D Point) const {return BoardPose.ToBoard(Point,BoardCenter());}
    void EndStroke();
    bool Undo();
    bool Finish();
    bool Claim();
    void Abandon();
    const TArray<FWoodworkingPattern>& Patterns() const {return Catalog;}
    const FWoodworkingPattern* Pattern() const;
    const ColdSteelWoodworking::FSettings& Settings() const {return Rules;}
    const ColdSteelWoodworking::FMask& Mask() const {return Board;}
    EWoodworkingPhase State() const {return Phase;}
    const FString& Message() const {return Notice;}
    bool IsPractice() const {return bPractice;}
    bool CanSelect() const {return bOpen&&!HasPendingJob()&&!bClaiming&&Phase!=EWoodworkingPhase::Running;}
    double Elapsed() const;
    double Remaining() const;
    double Quality() const;
private:
    class UColdSteelStatusModel* Model() const;
    bool PayForJob();
    bool SaveResult();
    bool RestoreJob();
    bool SaveCheckpoint();
    void WriteCheckpoint(TArray<uint8>& Bytes);
    bool ReadCheckpoint(const TArray<uint8>& Bytes);
    void BeginPaidRun();
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> NetworkModel;
    void Load();
    void AdvanceClock();
    void Evaluate(bool TimedOut);
    void CheckDamage();
    void ResetBoardPose();
    FVector2D BoardCenter() const {return FVector2D(Rules.Width,Rules.Height)*.5;}
    void SawInBoard(const ColdSteelWoodworking::FBoardPose& Pose,FVector2D& A,FVector2D& B) const;
    bool MoveBoardStep(FVector2D WorkDelta);
    ColdSteelWoodworking::FSettings Rules;
    ColdSteelWoodworking::FMask Board;
    TArray<FWoodworkingPattern> Catalog;
    FName Selected;
    FColdSteelCraftingRecipe AcceptedRecipe;
    EWoodworkingPhase Phase=EWoodworkingPhase::Abandoned;
    EWoodworkingMode SessionMode=EWoodworkingMode::Craft;
    ColdSteelWoodworking::FSawSettings SawRules;
    ColdSteelWoodworking::FBoardPose BoardPose,StrokePose,UndoPose;
    int32 StrokeRevision=0;
    bool bMotorOn=false,bFeeding=false,bUndoPose=false;
    double StartedAt=0,FrozenElapsed=0;
    double NextCheckpointAt=0;
    bool bCheckpointReady=false;
    bool bOpen=false,bPractice=false,bPracticeOnly=false,bClaiming=false;
    FString ConfigError,Notice;
};
