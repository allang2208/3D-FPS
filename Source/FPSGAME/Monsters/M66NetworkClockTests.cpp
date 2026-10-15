#if WITH_DEV_AUTOMATION_TESTS
#include "M66IncineratorMonster.h"
#include "M66BreathTiming.h"
#include "Animation/AnimSequence.h"
#include "../Combat/CombatStatusFormula.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "GameFramework/GameStateBase.h"
#include "Misc/AutomationTest.h"
#include "UObject/UnrealType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FM66NetworkClockTest,"FPSGAME.Monsters.M66.NetworkClockAndControl",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)

bool FM66NetworkClockTest::RunTest(const FString&)
{
    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(false)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("M66NetworkClock"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("isolated transient world"),World))return false;
    auto* Monster=World->SpawnActor<AM66IncineratorMonster>();
    auto* Clock=World->SpawnActor<AGameStateBase>();
    auto* Offset=FindFProperty<FFloatProperty>(AGameStateBase::StaticClass(),TEXT("ServerWorldTimeSecondsDelta"));
    auto* AttackProperty=FindFProperty<FStructProperty>(AM66IncineratorMonster::StaticClass(),TEXT("Sweep"));
    if(!TestNotNull(TEXT("real M66 actor"),Monster)||!TestNotNull(TEXT("game state clock"),Clock)
        ||!TestNotNull(TEXT("clock offset"),Offset)||!TestNotNull(TEXT("replicated attack record"),AttackProperty))
    {World->DestroyWorld(false);return false;}
    World->SetGameState(Clock);Offset->SetPropertyValue_InContainer(Clock,100.f);
    auto* Attack=AttackProperty->ContainerPtrToValuePtr<FM66SweepClock>(Monster);
    Attack->Active=true;Attack->Serial=1;Attack->Kind=EM66AttackKind::FurnaceBreath;Attack->StartedAt=98.2;
    Monster->SetReplicates(true);Monster->SwapRoles();
    TestFalse(TEXT("remote presentation role"),Monster->HasAuthority());
    TestTrue(TEXT("late client samples 1.8 s instead of restarting"),FMath::IsNearlyEqual(Monster->SweepAge(),1.8f,.001f));
    TestTrue(TEXT("release audio seeks through the pitch-scaled source"),FMath::IsNearlyEqual(M66BreathTiming::ReleaseSoundOffset(Monster->SweepAge()),.468f,.001f));
    TestEqual(TEXT("audio offset before release cannot be negative"),M66BreathTiming::ReleaseSoundOffset(.5f),0.f);
    const float Health=Monster->Health;
    TestEqual(TEXT("remote damage calls do not mutate health"),Monster->TakeDamage(100.f,FDamageEvent(),nullptr,nullptr),0.f);
    TestEqual(TEXT("remote health remains authoritative"),Monster->Health,Health);
    Monster->CancelAttack();
    TestTrue(TEXT("remote cancellation cannot write attack state"),Attack->Active);
    Attack->StartedAt=99.;
    TestTrue(TEXT("corrected timestamp resamples without a new serial"),FMath::IsNearlyEqual(Monster->SweepAge(),1.f,.001f));
    Attack->StartedAt=101.;TestEqual(TEXT("future timestamp is clamped"),Monster->SweepAge(),0.f);
    Monster->SwapRoles();Attack->StartedAt=99.;
    Monster->Status->AddChill(20,2.f,.05f);
    TestFalse(TEXT("freeze immediately cancels outstanding damage inside callback"),Attack->Active);
    TestTrue(TEXT("freeze publishes a controlled reaction"),Monster->Controlled());
    const uint32 FrozenSerial=Monster->SweepSerial();
    Monster->CancelAttack();TestEqual(TEXT("cancel is idempotent"),Monster->SweepSerial(),FrozenSerial);
    Attack->Active=true;++Attack->Serial;
    Monster->Status->AddPetrify(2.f,1.f);
    TestFalse(TEXT("petrify immediately cancels outstanding damage inside callback"),Attack->Active);
    auto* ReactionProperty=FindFProperty<FStructProperty>(AM66IncineratorMonster::StaticClass(),TEXT("Reaction"));
    if(TestNotNull(TEXT("replicated reaction record"),ReactionProperty))
    {
        auto* Reaction=ReactionProperty->ContainerPtrToValuePtr<FM66ReactionState>(Monster);
        Monster->LandClip=NewObject<UAnimSequence>(Monster);
        Monster->DeathClip=NewObject<UAnimSequence>(Monster);
        Monster->SwapRoles();
        Reaction->Phase=EM66Reaction::Dying;Reaction->bFromKnockdown=true;Reaction->DeathLead=0.f;
        float Seconds=0.f;bool Loop=false;
        TestTrue(TEXT("client holds existing knockdown death until the corpse packet"),Monster->HoldKnockdownDeathPose());
        TestEqual(TEXT("late client without history uses downed fallback, never standing death"),Monster->ReactionClip(Seconds,Loop),Monster->LandClip.Get());
        Reaction->bFromKnockdown=false;
        TestFalse(TEXT("standing death retains normal lead-in"),Monster->HoldKnockdownDeathPose());
        TestEqual(TEXT("standing death clip is preserved"),Monster->ReactionClip(Seconds,Loop),Monster->DeathClip.Get());
        Monster->SwapRoles();
    }
    World->DestroyWorld(false);
    return true;
}
#endif
