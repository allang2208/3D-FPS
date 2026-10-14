#include "TaskTrackingContractCommandlet.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "../Dungeons/DungeonSharedProgress.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

void UTaskTrackingContractCommandlet::AppendTrackedTasks(const APawn*, TArray<FTrackedTaskView>& Out)
{
    Out.Append(Fixture);
}

int32 UTaskTrackingContractCommandlet::Main(const FString&)
{
    int32 Checks = 0, Failures = 0;
    auto Require = [&Checks, &Failures](bool Pass, const TCHAR* Case)
    {
        ++Checks;
        if (!Pass) { ++Failures; UE_LOG(LogTemp, Error, TEXT("[TaskTrackingContract] FAIL: %s"), Case); }
    };
    FTrackedTaskView First;
    First.Id = TEXT("audit.first"); First.InstanceId = TEXT("instance.1"); First.Title = FText::FromString(TEXT("同名任务"));
    FTrackedObjectiveView A;
    A.Id = TEXT("elite"); A.Text = FText::FromString(TEXT("击杀精英")); A.Current = 1; A.Target = 1;
    auto B = A; B.Id = TEXT("second.elite"); B.Current = 0;
    First.Objectives = {A, B};
    auto Second = First;
    Second.Id = TEXT("audit.second"); Second.Priority = 100;
    Fixture = {First, Second};

    // Empty transient world is only a subsystem outer. It is never initialized or played.
    UWorld* World = UWorld::CreateWorld(EWorldType::None, false);
    auto* Registry = NewObject<UTaskTrackingSubsystem>(World);
    const APawn* Viewer = GetDefault<APawn>();
    TArray<FTrackedTaskView> Views;
    Registry->RegisterSource(this);
    Registry->RegisterSource(this);
    Registry->CollectTasks(Viewer, Views);
    Require(Views.Num() == 2, TEXT("registering a source twice does not duplicate tasks"));
    Require(Views.Num() == 2 && Views[0].Id == Second.Id, TEXT("priority determines task order"));
    Require(Views.Num() == 2 && Views[0].Title.EqualTo(Views[1].Title), TEXT("distinct IDs preserve identical task titles"));
    Require(Views.Num() == 2 && Views[1].Objectives.Num() == 2, TEXT("identical objective text does not merge goals"));
    Require(Views.Num() == 2 && Views[1].Objectives[0].State == ETrackedObjectiveState::Active,
        TEXT("display counts do not complete authoritative gameplay"));
    Fixture[0].Objectives.Swap(0, 1);
    Fixture[0].Objectives[1].Text = FText::FromString(TEXT("重新命名的目标"));
    Registry->CollectTasks(Viewer, Views);
    Require(Views.Num() == 2 && Views[1].Objectives[1].Id == TEXT("elite"), TEXT("renaming and reordering preserve objective identity"));
    Fixture[0].InstanceId = TEXT("instance.2");
    Registry->CollectTasks(Viewer, Views);
    Require(Views.Num() == 2 && Views[1].InstanceId == TEXT("instance.2"), TEXT("new run instance reaches the display"));
    Fixture.SetNum(1);
    Registry->CollectTasks(Viewer, Views);
    Require(Views.Num() == 1, TEXT("removed tasks do not linger"));
    Registry->UnregisterSource(this);
    Registry->CollectTasks(Viewer, Views);
    Require(Views.IsEmpty(), TEXT("unregister removes a source's tasks"));
    Fixture = {First};
    auto* OtherSource = NewObject<UTaskTrackingContractCommandlet>();
    OtherSource->Fixture = {Second};
    Registry->RegisterSource(this);
    Registry->RegisterSource(OtherSource);
    Registry->CollectTasks(Viewer, Views);
    Require(Views.Num() == 2, TEXT("independent gameplay sources share the same display list"));
    Registry->UnregisterSource(this);
    Registry->CollectTasks(Viewer, Views);
    Require(Views.Num() == 1 && Views[0].Id == Second.Id, TEXT("removing one source preserves another source's task"));
    Registry->UnregisterSource(OtherSource);
    using E = ETrackedObjectiveState;
    Require(TaskTracking::InitialStrike(true, E::Active, E::Completed) == 0.f, TEXT("live completion starts the stroke"));
    Require(TaskTracking::InitialStrike(false, E::Active, E::Completed) == 1.f, TEXT("restored completion does not replay"));
    Require(TaskTracking::InitialStrike(false, E::Completed, E::Active) == 0.f, TEXT("new task does not inherit a completed stroke"));
    Require(TaskTracking::InitialStrike(true, E::Completed, E::Failed) == 0.f, TEXT("failure is not displayed as completion"));

    // Exercise the same replicated payload and client merge used by the dungeon source.
    FDungeonSharedProgress Authority;
    Authority.RunId=TEXT("shared.run.1");Authority.Revision=1;
    FDungeonSharedProgress HostView,GuestView,LateGuest;
    Require(HostView.ApplyNewer(Authority,Authority.RunId)&&GuestView.ApplyNewer(Authority,Authority.RunId),
        TEXT("host and guest start with one shared run state"));
    const auto BeforeKill=Authority;
    ++Authority.Revision;Authority.bWelcomeEliteDefeated=true;
    Authority.Cleared.Add(TEXT("shared.room"));Authority.Explored.Add(TEXT("shared.room"));
    TArray<uint8> Bytes;
    {FMemoryWriter Writer(Bytes);FObjectAndNameAsStringProxyArchive Archive(Writer,false);
        FDungeonSharedProgress::StaticStruct()->SerializeItem(Archive,&Authority,nullptr);}
    FDungeonSharedProgress Received;
    {FMemoryReader Reader(Bytes);FObjectAndNameAsStringProxyArchive Archive(Reader,false);
        FDungeonSharedProgress::StaticStruct()->SerializeItem(Archive,&Received,nullptr);}
    Require(HostView.ApplyNewer(Authority,Authority.RunId)&&GuestView.ApplyNewer(Received,Authority.RunId)
        &&HostView.bWelcomeEliteDefeated&&GuestView.bWelcomeEliteDefeated
        &&HostView.Cleared==GuestView.Cleared&&HostView.Explored==GuestView.Explored,
        TEXT("one authoritative completion survives serialization and completes both player mirrors"));
    Require(!GuestView.ApplyNewer(BeforeKill,Authority.RunId)&&GuestView.bWelcomeEliteDefeated,
        TEXT("late pre-kill progress cannot undo team completion"));
    Require(!GuestView.ApplyNewer(Received,Authority.RunId),TEXT("duplicate completion is idempotent"));
    Require(!LateGuest.ApplyNewer(Received,FString())&&LateGuest.ApplyNewer(Received,Authority.RunId)
        &&LateGuest.bWelcomeEliteDefeated,TEXT("progress received before layout readiness applies after binding"));
    Require(!GuestView.ApplyNewer(Received,TEXT("shared.run.2")),TEXT("old run packets cannot complete a new run"));
    FDungeonSharedProgress NewRun;NewRun.RunId=TEXT("shared.run.2");NewRun.Revision=1;
    Require(GuestView.ApplyNewer(NewRun,NewRun.RunId)&&!GuestView.bWelcomeEliteDefeated&&GuestView.Cleared.IsEmpty(),
        TEXT("new run clears completion even when its revision starts at one"));
    ++Authority.Revision;Authority.bCompleted=true;
    Require(HostView.ApplyNewer(Authority,Authority.RunId)&&LateGuest.ApplyNewer(Authority,Authority.RunId)
        &&HostView.bCompleted&&LateGuest.bCompleted,TEXT("run completion is shared with late participants"));
    Registry->Deinitialize();
    World->DestroyWorld(false);
    Fixture.Reset();
    UE_LOG(LogTemp, Display, TEXT("[TaskTrackingContract] checks=%d failures=%d"), Checks, Failures);
    return Failures == 0 ? 0 : 1;
}
