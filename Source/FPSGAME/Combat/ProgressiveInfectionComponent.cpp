#include "ProgressiveInfectionComponent.h"
#include "CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/WolfMonster.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

namespace
{
float InfectionRatio(const FVector& Values, EInfectionStage Stage)
{
    const float Value = Stage == EInfectionStage::Early ? Values.X : Stage == EInfectionStage::Middle ? Values.Y : Values.Z;
    return Stage == EInfectionStage::None ? 0.f : FMath::Clamp(Value, 0.f, 1.f);
}
bool InfectionVitals(const AActor* Owner, float& Health, float& Maximum)
{
    if (const auto* H = Owner->FindComponentByClass<UFPSCombatHealthComponent>()) { Health=H->Health; Maximum=H->MaxHealth; }
    else if (const auto* W=Cast<AWolfMonster>(Owner)) { Health=W->Health; Maximum=W->MaxHealth; }
    else if (const auto* N=Cast<ANurseZombie>(Owner)) { Health=N->Health; Maximum=N->MaxHealth; }
    else if (const auto* HB=Cast<AHandBrainMonster>(Owner)) { Health=HB->Health; Maximum=HB->MaxHealth; }
    else if (const auto* M=Cast<APoisonMaggotMonster>(Owner)) { Health=M->Health; Maximum=M->MaxHealth; }
    else return false;
    return Health>0.f && Maximum>0.f;
}
}

EInfectionStage FInfectionState::Stage() const
{
    if (!bActive) return EInfectionStage::None;
    const float Middle=FMath::Max(1.f,Tuning.MiddleAtSeconds);
    const float Late=FMath::Max(Middle+1.f,Tuning.LateAtSeconds);
    return ElapsedSeconds>=Late ? EInfectionStage::Late : ElapsedSeconds>=Middle ? EInfectionStage::Middle : EInfectionStage::Early;
}
float FInfectionState::AttributeMultiplier() const { return 1.f-InfectionRatio(Tuning.AttributeReduction,Stage()); }
float FInfectionState::HealthLossRatio() const { return InfectionRatio(Tuning.MaxHealthLossPerSecond,Stage()); }

UProgressiveInfectionComponent::UProgressiveInfectionComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
}
UProgressiveInfectionComponent* UProgressiveInfectionComponent::GetOrAdd(AActor* Target)
{
    if (!IsValid(Target)) return nullptr;
    auto* Component=Target->FindComponentByClass<UProgressiveInfectionComponent>();
    if (!Component)
    {
        Component=NewObject<UProgressiveInfectionComponent>(Target);
        Target->AddInstanceComponent(Component); Component->RegisterComponent();
    }
    return Component;
}
float UProgressiveInfectionComponent::AttributeMultiplier(const AActor* Target)
{
    const auto* Component=Target ? Target->FindComponentByClass<UProgressiveInfectionComponent>() : nullptr;
    return Component ? Component->State.AttributeMultiplier() : 1.f;
}
bool UProgressiveInfectionComponent::Infect(AActor* Source, const FInfectionTuning& Tuning)
{
    if (!GetOwner()->HasAuthority()) return false;
    if (const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>(); Status && Status->IsImmune()) return false;
    float Health=0,Maximum=0;
    if (!InfectionVitals(GetOwner(),Health,Maximum)) return false;
    if (State.bActive) return true;
    State.bActive=true; State.ElapsedSeconds=0.f; State.Tuning=Tuning;
    InfectionSource=Source; UCombatStatusFormula::GetOrAdd(GetOwner());
    SetComponentTickEnabled(true); Publish(true);
    return true;
}
void UProgressiveInfectionComponent::Cure()
{
    if (!State.bActive) return;
    State=FInfectionState{}; InfectionSource.Reset(); SetComponentTickEnabled(false); Publish(true);
}
void UProgressiveInfectionComponent::Restore(const FInfectionState& SavedState)
{
    State=SavedState;
    State.ElapsedSeconds=FMath::IsFinite(State.ElapsedSeconds)?FMath::Max(0.f,State.ElapsedSeconds):0.f;
    InfectionSource.Reset();
    if(State.bActive)UCombatStatusFormula::GetOrAdd(GetOwner());
    SetComponentTickEnabled(State.bActive); Publish(true);
}
void UProgressiveInfectionComponent::Publish(bool bStageChanged)
{
    if (auto* Player=Cast<AFPSGAMECharacter>(GetOwner()); Player && Player->IsPlayerControlled())
        if (auto* Model=Player->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Model->SetInfectionState(State,bStageChanged);
    if (bStageChanged) UStatusEffectsComponent::Notify(GetOwner());
}
void UProgressiveInfectionComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,Type,Function);
    if (!State.bActive || !GetOwner()->HasAuthority() || Delta<=0.f) return;
    float Health=0,Maximum=0;
    if (!InfectionVitals(GetOwner(),Health,Maximum)) { Cure(); return; }
    const float End=State.ElapsedSeconds+Delta;
    float NextTick=FMath::FloorToFloat(State.ElapsedSeconds)+1.f;
    // Resolve each elapsed whole second at its own stage, including a hitch that
    // crosses a progression boundary. There is no damage on initial infection.
    while (State.bActive && NextTick<=End)
    {
        const auto Previous=State.Stage(); State.ElapsedSeconds=NextTick;
        Publish(State.Stage()!=Previous);
        if (!InfectionVitals(GetOwner(),Health,Maximum)) { Cure(); return; }
        const float Damage=Maximum*State.HealthLossRatio();
        AActor* Source=InfectionSource.Get();
        const auto* Pawn=Cast<APawn>(Source);
        auto Deal=[&](){ return UGameplayStatics::ApplyDamage(GetOwner(),Damage,Pawn?Pawn->GetController():nullptr,Source,UCombatDirectDamage::StaticClass()); };
        if (auto* Combat=GetOwner()->FindComponentByClass<UMonsterCombatComponent>()) Combat->ApplyHitWithReactionScale(0.f,Deal);
        else Deal();
        // Death/revive/cleanse may synchronously cure from inside the damage call.
        if (!State.bActive) return;
        if (!InfectionVitals(GetOwner(),Health,Maximum)) { Cure(); return; }
        NextTick+=1.f;
    }
    const auto Previous=State.Stage(); State.ElapsedSeconds=End;
    Publish(State.Stage()!=Previous);
}
