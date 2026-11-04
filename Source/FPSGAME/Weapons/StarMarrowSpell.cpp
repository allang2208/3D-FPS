#include "StarMarrowSpell.h"
#include "MeleeWeaponStats.h"
#include "FPSMeleeLightningComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "GameFramework/Pawn.h"
#include "../Monsters/MonsterCombatComponent.h"

void StarMarrow::CaptureSpell(AActor* Owner,FStarMarrowSpell& Receipt)
{
    if(!Owner||!Owner->HasAuthority()||Receipt.bReleased)return;
    Receipt.bReleased=true;
    auto* M=ColdSteelAuthority::ForPawn(Cast<APawn>(Owner));
    const auto* Item=M&&!M->ActiveProductionTool()?M->Equipped():nullptr;
    if(!Item||Item->Definition!=TEXT("ue_frost_crystal_sword"))return;
    const auto Stats=ColdSteelMelee::Evaluate(*Item,M);
    Receipt.HealthRatio=float(Stats.Modifiers.HitHealthReturnRatio);
    Receipt.ManaRatio=float(Stats.Modifiers.HitManaReturnRatio);
}
StarMarrow::FHitRecovery::FHitRecovery(AActor* Shooter,AActor* Victim,const FStarMarrowSpell& Receipt)
{
    if(!Shooter||!Shooter->HasAuthority()||!Receipt.bReleased||(Receipt.HealthRatio<=0&&Receipt.ManaRatio<=0)
        ||!UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))return;
    const auto* Combat=IsValid(Victim)?Victim->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Combat||Combat->IsDead())return;
    float Maximum=0;FText Name;Combat->GetVitals(Before,Maximum,Name);
    Source=Shooter;Target=Victim;HealthRatio=Receipt.HealthRatio;ManaRatio=Receipt.ManaRatio;
}
void StarMarrow::FHitRecovery::Finish(float Applied) const
{
    if(!Source||Applied<=0||Before<=0)return;
    float Remaining=0,Maximum=0;FText Name;
    if(IsValid(Target))if(const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>())Combat->GetVitals(Remaining,Maximum,Name);
    const float Effective=FMath::Min(Applied,FMath::Clamp(Before-Remaining,0.f,Before));
    if(auto* M=ColdSteelAuthority::ForPawn(Cast<APawn>(Source)))
        M->RestoreMagicCrystalResources(Source,Effective*HealthRatio,Effective*ManaRatio);
}
