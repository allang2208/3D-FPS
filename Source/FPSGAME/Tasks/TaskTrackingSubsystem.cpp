#include "TaskTrackingSubsystem.h"
#include "GameFramework/Pawn.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/ConfigCacheIni.h"

namespace
{
constexpr TCHAR SelectionSection[] = TEXT("FPSGAME.TaskJournal.Tracking");
}

void UTaskTrackingSubsystem::RegisterSource(UObject* Source)
{
    if (IsValid(Source) && Cast<ITaskTrackingSource>(Source)) Sources.AddUnique(Source);
}

void UTaskTrackingSubsystem::UnregisterSource(UObject* Source)
{
    Sources.RemoveAll([Source](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Source; });
}

void UTaskTrackingSubsystem::CollectTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out, ETaskViewPurpose Purpose)
{
    Out.Reset();
    Sources.RemoveAll([](const auto& Entry) { return !Entry.IsValid(); });
    if (!IsValid(Viewer)) return;
    for (const auto& Entry : Sources)
        if (auto* Source = Cast<ITaskTrackingSource>(Entry.Get()))
        {
            if (Purpose == ETaskViewPurpose::Journal) Source->AppendJournalTasks(Viewer, Out);
            else Source->AppendTrackedTasks(Viewer, Out);
        }
    TaskTracking::NormalizeTasks(Out);
}

FTaskJournalDetails UTaskTrackingSubsystem::JournalDetails(const APawn* Viewer, const FTrackedTaskView& Task) const
{
    FTaskJournalDetails Details;
    for (const auto& Entry : Sources)
        if (const auto* Source = Cast<ITaskTrackingSource>(Entry.Get()))
            if (Source->ReadJournalDetails(Viewer, Task, Details)) return Details;
    Details.Steps = Task.Objectives;
    return Details;
}

FName UTaskTrackingSubsystem::SelectedTask()
{
    const auto* Game = GetWorld()->GetGameInstance();
    const auto* Model = Game ? Game->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    const FGuid ProfileId = Model ? Model->ProfileView().NetworkProfileId : FGuid();
    if (ProfileId != SelectionProfile)
    {
        SelectionProfile = ProfileId;
        FString SavedId;
        if (ProfileId.IsValid())
            GConfig->GetString(SelectionSection, *ProfileId.ToString(), SavedId, GGameUserSettingsIni);
        SelectedId = FName(*SavedId);
    }
    return SelectedId;
}

void UTaskTrackingSubsystem::ToggleTask(FName TaskId)
{
    const FName Previous = SelectedTask();
    if (TaskId.IsNone() || !SelectionProfile.IsValid()) return;
    SelectedId = Previous == TaskId ? NAME_None : TaskId;
    const FString Key = SelectionProfile.ToString();
    if (SelectedId.IsNone())
        GConfig->RemoveKey(SelectionSection, *Key, GGameUserSettingsIni);
    else
        GConfig->SetString(SelectionSection, *Key, *SelectedId.ToString(), GGameUserSettingsIni);
    GConfig->Flush(false, GGameUserSettingsIni);
    OnSelectionChanged.Broadcast();
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
