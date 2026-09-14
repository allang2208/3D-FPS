#include "FPSGAMECharacter.h"
#include "Monsters/MonsterCombatComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void AFPSGAMECharacter::NotifyConfirmedWeaponHit(AActor* Target, float AppliedDamage)
{
    if (Target == this || !Cast<APawn>(Target) || AppliedDamage <= 0.f || !GetWorld()) return;
    LastConfirmedWeaponHitTime = GetWorld()->GetTimeSeconds();
    LastMonsterHit = FMonsterHitFeedback();
    const auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>();
    if (!Combat || !Combat->GetVitals(LastMonsterHit.Health, LastMonsterHit.MaxHealth, LastMonsterHit.Name)) return;
    LastMonsterHit.Target = Target;
    LastMonsterHit.Damage = AppliedDamage;
    LastMonsterHit.bKilled = Combat->IsDead();
    if (IsLocallyControlled() && ConfirmedMonsterHitSound)
        UGameplayStatics::PlaySound2D(this, ConfirmedMonsterHitSound, 1.f, 1.f);
}

float AFPSGAMECharacter::GetHitMarkerOpacity() const
{
    if (!GetWorld()) return 0.f;
    const double Age = GetWorld()->GetTimeSeconds() - LastConfirmedWeaponHitTime;
    // Hold for 60 ms, then fade over 180 ms. Repeated hits refresh the same marker.
    return .65f * FMath::Clamp(static_cast<float>((.24 - Age) / .18), 0.f, 1.f);
}

bool AFPSGAMECharacter::GetMonsterHitFeedback(FMonsterHitFeedback& Out) const
{
    if (!GetWorld() || LastMonsterHit.MaxHealth <= 0.f) return false;
    const double Age = GetWorld()->GetTimeSeconds() - LastConfirmedWeaponHitTime;
    if (Age >= 4.) return false;
    Out = LastMonsterHit;
    Out.Opacity = FMath::Clamp(static_cast<float>((4. - Age) / .5), 0.f, 1.f);
    if (const auto* Target = Out.Target.Get())
        if (const auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>())
        {
            Combat->GetVitals(Out.Health, Out.MaxHealth, Out.Name);
            Out.bKilled = Combat->IsDead();
        }
    return true;
}
