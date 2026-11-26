#include "UnknownSpellCombat.h"
#include "MonsterTargeting.h"
#include "UnknownHumanoid.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Controller.h"
thread_local const UnknownSpell::FWeaponSnapshot* UnknownSpell::ActiveWeapon=nullptr;

bool UnknownSpell::IsCaster(const AActor* Actor) { return IsValid(Actor) && Actor->IsA<AUnknownHumanoid>(); }
UColdSteelStatusModel* UnknownSpell::Model(APawn* Pawn)
{ const auto* Monster=Cast<AUnknownHumanoid>(Pawn); return Monster?Monster->EquipmentModel():nullptr; }
bool UnknownSpell::IsTarget(const AActor* Caster,const AActor* Target)
{
    const auto* Source=Cast<AUnknownHumanoid>(Caster);
    const auto* Player=Cast<APawn>(Target);
    // Streaming EndPlay can leave a UObject alive until GC. Neither that old
    // caster nor a detached player pawn belongs to the current combat life.
    if(!IsValid(Source) || !Source->HasActorBegunPlay() || Source->Dead() ||
        !IsValid(Player) || !Player->HasActorBegunPlay() || Source->GetWorld()!=Player->GetWorld()) return false;
    if (MonsterTargeting::IsActiveArtisan(Player)) return true;
    if (!Player->IsPlayerControlled() || !Player->GetController() || Player->GetController()->GetPawn()!=Player) return false;
    const auto* HP=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    return HP && !HP->IsDead();
}
bool UnknownSpell::Hit(APawn* Caster,AActor* Target,float Amount,float Chance,float Bonus,float DamageBonus,float Penetration,
    TSubclassOf<UDamageType> Type,bool Weak)
{
    if(!IsTarget(Caster,Target) || !Caster->HasAuthority())return false;
    auto* Pawn=Cast<APawn>(Target);
    auto* Defender=Pawn->IsPlayerControlled()?ColdSteelAuthority::ForPawn(Pawn):nullptr;
    const float Resistance=Defender?Defender->Derived(TEXT("critRes")):0.f;
    Amount*=1.f+DamageBonus;
    if(Weak || FMath::FRand()*100.f<CoreCombatFormula::CriticalChance(Chance,Resistance))
        Amount=CoreCombatFormula::CriticalDamage(Amount,Bonus);
    const CombatFormulaRuntime::MagicHit Stats{Chance,Bonus,Penetration,DamageBonus};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> Scope(CombatFormulaRuntime::ActiveMagicHit,&Stats);
    return UGameplayStatics::ApplyDamage(Target,FMath::FloorToFloat(Amount),Caster->GetController(),Caster,Type)>0.f;
}
