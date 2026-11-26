#include "FPSExhaustionComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/AudioComponent.h"
#include "Components/PostProcessComponent.h"
#include "GameFramework/Pawn.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

UFPSExhaustionComponent::UFPSExhaustionComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    static ConstructorHelpers::FObjectFinder<USoundBase> Sound(
        TEXT("/Game/Player/Exhaustion/S_ExhaustionPanting.S_ExhaustionPanting"));
    PantingSound=Sound.Object;
}

void UFPSExhaustionComponent::ObserveStamina(float Stamina)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||(!Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()))return;
    const bool Depleted=Stamina<=0.f;
    const bool Enter=Depleted&&!bWasDepleted;
    bWasDepleted=Depleted;
    if(!Enter)return;
    // Some melee costs are owner-simulated; this RPC can only apply the fixed
    // self-penalty. Both server consumption and owner intent use the same gate.
    ServerEnterExhaustion();
}

void UFPSExhaustionComponent::ServerEnterExhaustion_Implementation()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Pawn||!Pawn->HasAuthority()||!Pawn->IsPlayerControlled()||(Health&&Health->IsDead()))return;
    if(auto* Status=UCombatStatusFormula::GetOrAdd(GetOwner()))Status->AddExhaustion();
}

void UFPSExhaustionComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const auto* Pawn=Cast<APawn>(GetOwner());
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    const bool LocalAlive=Pawn&&Pawn->IsLocallyControlled()&&(!Health||!Health->IsDead());
    const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
    const float Remaining=LocalAlive&&Status?Status->ExhaustionRemaining():0.f;
    const bool Active=Remaining>0.f;
    if(Active&&!Darkness)
    {
        Darkness=NewObject<UPostProcessComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Darkness);
        Darkness->bUnbound=true;Darkness->Priority=1400.f;Darkness->BlendWeight=0.f;
        // Full-frame grading darkens the centre and weapon as well as the edges.
        Darkness->Settings.bOverride_ColorGain=true;
        Darkness->Settings.ColorGain=FVector4(.45f,.45f,.45f,1.f);
        Darkness->RegisterComponent();
    }
    ViewWeight=LocalAlive?FMath::FInterpConstantTo(ViewWeight,Active?1.f:0.f,Delta,Active?4.f:3.f):0.f;
    if(Darkness)Darkness->BlendWeight=ViewWeight;
    if(Active&&!bWasActive&&PantingSound)
    {
        if(!Panting)
        {
            Panting=NewObject<UAudioComponent>(GetOwner());GetOwner()->AddInstanceComponent(Panting);
            Panting->bAutoActivate=false;Panting->bAutoDestroy=false;Panting->bAllowSpatialization=false;
            Panting->SetSound(PantingSound);Panting->RegisterComponent();
        }
        Panting->Stop();
        // SoundWave loops for as long as the debuff is active; only its exit stops playback.
        Panting->FadeIn(.12f,.65f);
    }
    else if(!Active&&bWasActive&&Panting)
    {
        if(LocalAlive)Panting->FadeOut(.2f,0.f);else Panting->Stop();
    }
    bWasActive=Active;
}

void UFPSExhaustionComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(Panting){Panting->Stop();Panting->DestroyComponent();}
    if(Darkness)Darkness->DestroyComponent();
    Super::EndPlay(Reason);
}
