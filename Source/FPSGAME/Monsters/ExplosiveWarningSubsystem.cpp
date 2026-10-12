#include "ExplosiveWarningSubsystem.h"
#include "BellowSacProjectile.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"

bool UExplosiveWarningSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{ return Type == EWorldType::Game || Type == EWorldType::PIE; }

void UExplosiveWarningSubsystem::Register(ABellowSacProjectile* Projectile)
{
    if (GetWorld()->GetNetMode() == NM_DedicatedServer) return;
    Projectiles.AddUnique(Projectile); UntilRefresh = 0.f;
}
void UExplosiveWarningSubsystem::Unregister(ABellowSacProjectile* Projectile)
{
    Projectiles.Remove(Projectile); UntilRefresh = 0.f;
    if (Projectiles.IsEmpty()) Views.Reset();
}
const TArray<FExplosiveWarning>& UExplosiveWarningSubsystem::ForPlayer(const APlayerController* Player) const
{
    static const TArray<FExplosiveWarning> Empty;
    const auto* Found = Views.Find(TWeakObjectPtr<const APlayerController>(Player));
    return Found ? *Found : Empty;
}
void UExplosiveWarningSubsystem::Tick(float DeltaTime)
{
    UntilRefresh -= DeltaTime;
    if (UntilRefresh > 0.f) return;
    UntilRefresh = .10f;
    Projectiles.RemoveAll([](const auto& P) { return !P.IsValid(); });
    for (auto It = Views.CreateIterator(); It; ++It)
        if (!It.Key().IsValid()) It.RemoveCurrent();
    for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = It->Get();
        if (!PC || !PC->IsLocalController()) continue;
        auto& Warnings = Views.FindOrAdd(PC); Warnings.Reset();
        APawn* Player = PC->GetPawn();
        if (!Player) continue;
        for (const auto& Weak : Projectiles)
        {
            auto* Projectile = Weak.Get();
            if (!Projectile || Projectile->IsSpent() ||
                FVector::DistSquared(Player->GetActorLocation(), Projectile->GetActorLocation()) > FMath::Square(750.f)) continue;
            float Distance = 0.f;
            const bool Exposed = Projectile->ExposureTo(Player, Distance);
            if (Distance <= 600.f) Warnings.Add({Projectile, Distance, Exposed});
        }
        Warnings.Sort([](const FExplosiveWarning& A, const FExplosiveWarning& B)
        {
            const auto* PA=A.Projectile.Get(); const auto* PB=B.Projectile.Get();
            const bool DA=PA && A.bExposed && A.Distance<=PA->GetBlastRadius();
            const bool DB=PB && B.bExposed && B.Distance<=PB->GetBlastRadius();
            if (DA!=DB) return DA;
            const float TA=PA && PA->IsArmed()?PA->FuseRemaining():10.f;
            const float TB=PB && PB->IsArmed()?PB->FuseRemaining():10.f;
            return FMath::IsNearlyEqual(TA,TB)?A.Distance<B.Distance:TA<TB;
        });
    }
}
TStatId UExplosiveWarningSubsystem::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UExplosiveWarningSubsystem, STATGROUP_Tickables); }
void UExplosiveWarningSubsystem::Deinitialize()
{ Projectiles.Reset(); Views.Reset(); Super::Deinitialize(); }
