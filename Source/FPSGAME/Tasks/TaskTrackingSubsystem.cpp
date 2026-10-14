#include "TaskTrackingSubsystem.h"
#include "GameFramework/Pawn.h"

void UTaskTrackingSubsystem::RegisterSource(UObject* Source)
{
    if (IsValid(Source) && Cast<ITaskTrackingSource>(Source)) Sources.AddUnique(Source);
}

void UTaskTrackingSubsystem::UnregisterSource(UObject* Source)
{
    Sources.RemoveAll([Source](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Source; });
}

void UTaskTrackingSubsystem::CollectTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out)
{
    Out.Reset();
    Sources.RemoveAll([](const auto& Entry) { return !Entry.IsValid(); });
    if (!IsValid(Viewer)) return;
    for (const auto& Entry : Sources)
        if (auto* Source = Cast<ITaskTrackingSource>(Entry.Get())) Source->AppendTrackedTasks(Viewer, Out);
    TaskTracking::NormalizeTasks(Out);
}

void UTaskTrackingSubsystem::Deinitialize()
{
    Sources.Reset();
    Super::Deinitialize();
}

void TaskTracking::NormalizeTasks(TArray<FTrackedTaskView>& Tasks)
{
    TSet<FName> SeenTasks;
    Tasks.RemoveAll([&SeenTasks](FTrackedTaskView& Task)
    {
        if (!ensureMsgf(!Task.Id.IsNone() && !Task.InstanceId.IsEmpty() && !SeenTasks.Contains(Task.Id),
            TEXT("Tracked tasks require unique namespaced IDs and an instance ID."))) return true;
        SeenTasks.Add(Task.Id);
        TSet<FName> SeenObjectives;
        Task.Objectives.RemoveAll([&SeenObjectives](const FTrackedObjectiveView& Objective)
        {
            if (!ensureMsgf(!Objective.Id.IsNone() && !SeenObjectives.Contains(Objective.Id),
                TEXT("Tracked objective IDs must be unique within a task."))) return true;
            SeenObjectives.Add(Objective.Id);
            return false;
        });
        return false;
    });
    Tasks.StableSort([](const auto& A, const auto& B)
    { return A.Priority != B.Priority ? A.Priority > B.Priority : A.Id.LexicalLess(B.Id); });
}

float TaskTracking::InitialStrike(bool bSameObjective, ETrackedObjectiveState Before, ETrackedObjectiveState After)
{
    return After == ETrackedObjectiveState::Completed && (!bSameObjective || Before == ETrackedObjectiveState::Completed) ? 1.f : 0.f;
}
