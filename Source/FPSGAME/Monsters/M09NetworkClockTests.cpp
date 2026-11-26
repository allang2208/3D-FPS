#if WITH_DEV_AUTOMATION_TESTS
#include "HangingBellM09.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Misc/AutomationTest.h"
#include "UObject/UnrealType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FM09NetworkClockTest,"FPSGAME.PowerNetwork.HangingBellClock",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)

bool FM09NetworkClockTest::RunTest(const FString&)
{
    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(false)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("M09NetworkClock"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("isolated transient world"),World))return false;
    auto* Bell=World->SpawnActor<AHangingBellM09>();
    auto* Clock=World->SpawnActor<AGameStateBase>();
    auto* Offset=FindFProperty<FFloatProperty>(AGameStateBase::StaticClass(),TEXT("ServerWorldTimeSecondsDelta"));
    if(!TestNotNull(TEXT("real hanging bell actor"),Bell)||!TestNotNull(TEXT("replicated game clock"),Clock)
        ||!TestNotNull(TEXT("server clock offset property"),Offset))
    {World->DestroyWorld(false);return false;}
    Bell->SetReplicates(true);
    Bell->SwapRoles();
    TestFalse(TEXT("test actor uses the remote presentation path"),Bell->HasAuthority());
    Bell->State=EM09State::Claw;Bell->StateStartedAt=99.;Bell->StateSeconds=0.f;
    World->SetGameState(Clock);
    Offset->SetPropertyValue_InContainer(Clock,100.f);
    Bell->Tick(.1f);
    TestTrue(TEXT("late joining attack catches up to server time"),FMath::IsNearlyEqual(Bell->StateSeconds,1.f,.001f));
    Bell->StateStartedAt=99.6; // The timestamp arrives without another state notification.
    Bell->Tick(.1f);
    TestTrue(TEXT("timestamp arriving after state corrects animation age"),FMath::IsNearlyEqual(Bell->StateSeconds,.4f,.001f));
    Offset->SetPropertyValue_InContainer(Clock,100.2f);
    Bell->Tick(.8f);
    TestTrue(TEXT("server clock correction wins over local frame accumulation"),FMath::IsNearlyEqual(Bell->StateSeconds,.6f,.001f));
    World->SetGameState(nullptr);Bell->StateSeconds=0.f;
    Bell->Tick(.1f);
    World->SetGameState(Clock);Offset->SetPropertyValue_InContainer(Clock,101.f);
    Bell->Tick(.1f);
    TestTrue(TEXT("clock becoming available catches up without a state transition"),FMath::IsNearlyEqual(Bell->StateSeconds,1.4f,.001f));
    Bell->StateStartedAt=102.;Bell->Tick(.1f);
    TestEqual(TEXT("future timestamp never produces negative animation time"),Bell->StateSeconds,0.f);
    World->DestroyWorld(false);
    return true;
}
#endif
