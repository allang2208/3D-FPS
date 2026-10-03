#include "M10Mawcrawler.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DamageEvents.h"

bool AM10Mawcrawler::IsWeakpointHit(const FHitResult& Hit) const
{
    if(Dead()||Hit.GetActor()!=this||Hit.GetComponent()!=GetMesh()||Hit.BoneName!=TEXT("head"))return false;
    const FTransform Head=GetMesh()->GetSocketTransform(TEXT("head"));
    const FVector Ray=Hit.TraceEnd-Hit.TraceStart;
    for(const FTransform& Local:EyeWeakpointFrames)
    {
        const FTransform Eye=Local*Head;
        const FVector Point=Eye.InverseTransformPosition(Hit.ImpactPoint);
        if(Ray.IsNearlyZero())
        {
            if(FMath::Abs(Point.X)<=.5&&FMath::Square(Point.Y)+FMath::Square(Point.Z)<=1.)return true;
            continue;
        }
        // Only a front-facing, actual head contact may reach the iris. The
        // narrow projected ellipse compensates for the existing convex head's
        // shallow padding; it cannot turn rear/shell hits into headshots.
        if(FVector::DotProduct(Ray.GetSafeNormal(),Eye.GetUnitAxis(EAxis::X))>=-.2)continue;
        if(Point.X<-.35||Point.X>2.)continue;
        const FVector Direction=Eye.InverseTransformVector(Ray);
        if(FMath::Abs(Direction.X)<SMALL_NUMBER)continue;
        const FVector Iris=Point-Direction*(Point.X/Direction.X);
        if(FMath::Square(Iris.Y)+FMath::Square(Iris.Z)<=1.)return true;
    }
    return false;
}
float AM10Mawcrawler::DamageSurfaceMultiplier(const FDamageEvent& Event) const
{
    const UDamageType* Type=Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr;
    const bool Magic=CombatFormulaRuntime::IsMagic(Type);
    const auto* Weapon=CombatFormulaRuntime::ActiveWeaponHit;
    const bool WeaponContact=Weapon&&Weapon->Target==this&&!Weapon->bResolved&&!Magic;
    // Attack delivery, not shooter distance or the equipped item, defines ranged.
    // The mixed elemental portions of a real melee weapon remain melee as well.
    if(WeaponContact&&Weapon->bMelee)return 1.f;
    if(Type&&(Type->IsA<UEnemyMeleeDamage>()||Type->IsA<UCombatDirectDamage>()||Type->IsA<UStatusMagicDamage>()))return 1.f;
    const bool Ranged=WeaponContact||Magic||(Type&&Type->IsA<UEnemyRangedDamage>())||
        Event.IsOfType(FPointDamageEvent::ClassID)||Event.IsOfType(FRadialDamageEvent::ClassID);
    if(!Ranged)return 1.f;
    const bool Eye=Event.IsOfType(FPointDamageEvent::ClassID)&&IsWeakpointHit(static_cast<const FPointDamageEvent&>(Event).HitInfo);
    // Fireball settles direct contact and splash in one transaction. Its
    // per-victim context carries the real iris hit only for the direct victim.
    const bool DirectSpellEye=Magic&&CombatFormulaRuntime::ActiveMagicHit&&CombatFormulaRuntime::ActiveMagicHit->bWeakpoint;
    return Eye||DirectSpellEye?1.f:FMath::Clamp(RangedBodyDamageMultiplier,0.f,1.f);
}
