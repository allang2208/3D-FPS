#include "ProductionToolComponent.h"
#include "RuneboundHammerTuning.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/MagicOcclusion.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

bool RuneboundHammer::HasStarOath(const FColdSteelItem& Item)
{
    if(Item.Definition!=Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Head;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
        (*Parts)->TryGetStringField(TEXT("hammer_heads"),Head)&&Head==StarOathHead;
}

double RuneboundHammer::AttackMultiplier(const FColdSteelItem& Item)
{return HasStarOath(Item)?StarOathAttackMultiplier:1.;}

double RuneboundHammer::AttackMultiplier(const FColdSteelProfile& State)
{
    const auto* Item=State.Items.FindByPredicate([&](const FColdSteelItem& I)
        {return I.Place==1&&I.Cell==State.ActiveWeaponSlot;});
    return Item?AttackMultiplier(*Item):1.;
}

void UProductionToolComponent::QueueRuneboundDetonation(const FHitResult& Hit,const FColdSteelSkillShot& Shot)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Profile=Pawn?ColdSteelAuthority::ForPawn(Pawn):nullptr;
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Pawn||!Pawn->HasAuthority()||!Item||!RuneboundHammer::HasStarOath(*Item))return;
    const float Damage=Profile->Derived(TEXT("matk"))*RuneboundHammer::DetonationMagicAttackScale*
        (RuneboundHammer::HasDestructionRune(*Item)?RuneboundHammer::DestructionAwakeningMultiplier:1.);
    const FVector Origin=Hit.ImpactPoint;
    const TWeakObjectPtr<AActor> Direct=Hit.GetActor();
    const float Penetration=Shot.MagicPenetration;
    const float MagicBonus=FMath::Max(0.,(1.+Profile->SetEffect(TEXT("magicDamage")))*
        ColdSteelMelee::EquippedModifiers(Profile).MagicDamage)-1.;
    // The impact commits one independent magic hit per victim. Defer until the
    // original weapon transaction has unwound, so it cannot train, charge, crit
    // or trigger another enchant through that contact's thread-local scope.
    GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(this,
        [this,Origin,Direct,Damage,Penetration,MagicBonus]()
    {
        auto* Source=Cast<AFPSGAMECharacter>(GetOwner());
        if(!Source||!Source->HasAuthority()||!GetWorld())return;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(StarOathTargets),false,Source);
        TArray<FOverlapResult> Overlaps;
        GetWorld()->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,
            FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(RuneboundHammer::DetonationRadiusCM),Query);
        TArray<AActor*,TInlineAllocator<16>> Targets;
        if(Direct.IsValid())Targets.AddUnique(Direct.Get());
        for(const auto& Contact:Overlaps)if(auto* Target=Contact.GetActor())
            if(UFPSMeleeLightningComponent::IsEnemy(Target,Source))Targets.AddUnique(Target);
        FCollisionQueryParams Sight(SCENE_QUERY_STAT(StarOathExposure),true,Source);
        for(auto* Target:Targets)Sight.AddIgnoredActor(Target);
        CombatFormulaRuntime::MagicHit Context;Context.Penetration=Penetration;Context.DamageBonus=MagicBonus;
        TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
        for(auto* Target:Targets)
        {
            if(!UFPSMeleeLightningComponent::IsEnemy(Target,Source))continue;
            if(Target!=Direct.Get()&&!MagicOcclusion::HasExposure(GetWorld(),Target,Origin,Sight,Source))continue;
            auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
            FHitResult MagicHit(Target,Cast<UPrimitiveComponent>(Target->GetRootComponent()),Target->GetActorLocation(),FVector::UpVector);
            MagicHit.ImpactPoint=Target->GetActorLocation();MagicHit.TraceStart=Origin;MagicHit.bBlockingHit=true;
            const FVector Direction=(MagicHit.ImpactPoint-Origin).GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector);
            auto Apply=[&](){return UGameplayStatics::ApplyPointDamage(Target,Damage,Direction,MagicHit,
                Source->GetController(),Source,UStatusMagicDamage::StaticClass());};
            if(Combat)Combat->ApplyHitWithToughnessScale(0.f,Apply);else Apply();
        }
    }));
}
