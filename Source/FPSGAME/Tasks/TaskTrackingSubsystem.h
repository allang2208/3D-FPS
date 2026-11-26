#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/Interface.h"
#include "TaskTrackingSubsystem.generated.h"

class APawn;

enum class ETaskViewPurpose : uint8 { Tracker, Journal };
enum class ETrackedTaskState : uint8 { NotStarted, InProgress, Completed };

enum class ETrackedObjectiveState : uint8 { Active, Completed, Failed, Pending, Skipped };

/** Presentation only. Gameplay owns counts, completion, side effects and persistence. */
struct FTrackedObjectiveView
{
    FName Id;
    FText Text;
    FText Hint;
    int32 Current = 0;
    int32 Target = 0; // Zero hides the counter; completion is always explicit.
    ETrackedObjectiveState State = ETrackedObjectiveState::Active;
};

struct FTrackedTaskView
{
    FName Id; // Globally namespaced definition, e.g. dungeon.exploration.
    FString InstanceId; // Run/quest instance; changes when that task is restarted.
    FText Title;
    FText Area;
    FText Stage;
    FText Hint;
    int32 Priority = 0; // Larger first; Id breaks ties deterministically.
    TArray<FTrackedObjectiveView> Objectives;
    ETrackedTaskState State = ETrackedTaskState::InProgress;
};

struct FTaskJournalDetails
{
    FText Introduction;
    FText Reward;
    TArray<FTrackedObjectiveView> Steps;
};

UINTERFACE(MinimalAPI, meta=(CannotImplementInterfaceInBlueprint))
class UTaskTrackingSource : public UInterface
{
    GENERATED_BODY()
};

/** Sources append player-specific snapshots. Never award/complete gameplay from this query. */
class FPSGAME_API ITaskTrackingSource
{
    GENERATED_BODY()
public:
    virtual void AppendTrackedTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out) = 0;
    virtual bool ReadJournalDetails(const APawn* Viewer, const FTrackedTaskView& Task, FTaskJournalDetails& Out) const { return false; }
    virtual void AppendJournalTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out) { AppendTrackedTasks(Viewer, Out); }
};

/** Shared display-source registry for dungeon and future non-dungeon tasks. */
UCLASS()
class FPSGAME_API UTaskTrackingSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void RegisterSource(UObject* Source);
    void UnregisterSource(UObject* Source);
    void CollectTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out, ETaskViewPurpose Purpose = ETaskViewPurpose::Tracker);
    FTaskJournalDetails JournalDetails(const APawn* Viewer, const FTrackedTaskView& Task) const;
    // Personal HUD preference. Gameplay sources continue publishing the full task list.
    FName SelectedTask();
    void ToggleTask(FName TaskId);
    FSimpleMulticastDelegate OnSelectionChanged;
    virtual void Deinitialize() override;
private:
    TArray<TWeakObjectPtr<UObject>> Sources;
    FGuid SelectionProfile;
    FName SelectedId;
};

namespace TaskTracking
{
    /** Stable-ID normalization shared with the isolated contract audit. No text-based identity. */
    FPSGAME_API void NormalizeTasks(TArray<FTrackedTaskView>& Tasks);
    /** First display / restored completion is instant; only a visible transition animates. */
    FPSGAME_API float InitialStrike(bool bSameObjective, ETrackedObjectiveState Before, ETrackedObjectiveState After);
}
