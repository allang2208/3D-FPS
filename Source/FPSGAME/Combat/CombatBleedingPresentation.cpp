#include "CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Multiplayer/FPSStatusReplicationComponent.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

void UCombatStatusFormula::AddBleedingHit(AActor* Source,int32 Stacks,const FHitResult& Hit)
{
    if(IsImmune()||Stacks<=0)return;
    BleedSurface.Reset();BleedBone=NAME_None;
    if(auto* Surface=Hit.GetComponent();Surface&&Surface->GetOwner()==GetOwner())
    {
        BleedSurface=Surface;
        BleedBone=Surface->DoesSocketExist(Hit.BoneName)?Hit.BoneName:NAME_None;
        const FTransform Frame=BleedBone.IsNone()?Surface->GetComponentTransform():Surface->GetSocketTransform(BleedBone);
        BleedLocalPoint=Frame.InverseTransformPosition(Hit.ImpactPoint);
        BleedLocalNormal=Frame.InverseTransformVectorNoScale(Hit.ImpactNormal.GetSafeNormal(SMALL_NUMBER,FVector::UpVector));
    }
    AddBleeding(Source,Stacks);
}

void UCombatStatusFormula::EmitBleedingBurst()
{
    auto* Owner=GetOwner();
    if(!Owner||!Owner->HasAuthority()||!GetWorld()||BleedStacks<=0)return;
    const auto* Combat=Owner->FindComponentByClass<UMonsterCombatComponent>();
    if(!Combat||Combat->IsDead())return;
    const double Now=GetWorld()->GetTimeSeconds();
    // Rapid hits still add every stack; their cosmetic pulses can coalesce.
    if(Now-LastBleedBurstAt<.12)return;
    FVector Origin,Extent;Owner->GetActorBounds(true,Origin,Extent);
    FVector Normal=BleedSource.IsValid()?(BleedSource->GetActorLocation()-Origin).GetSafeNormal():Owner->GetActorForwardVector();
    if(BleedSurface.IsValid())
    {
        const FTransform Frame=BleedBone.IsNone()?BleedSurface->GetComponentTransform():BleedSurface->GetSocketTransform(BleedBone);
        Origin=Frame.TransformPosition(BleedLocalPoint);
        Normal=Frame.TransformVectorNoScale(BleedLocalNormal).GetSafeNormal();
    }
    else Origin+=Normal*FMath::Min(float(Extent.GetMin()),22.f);
    Normal=Normal.GetSafeNormal(SMALL_NUMBER,FVector::ForwardVector);
    LastBleedBurstAt=Now;
    if(auto* Replica=Owner->FindComponentByClass<UFPSStatusReplicationComponent>())
        Replica->MulticastBleedingBurst(Origin,Normal,BleedStacks);
    else if(auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())FX->SpawnBleedingBurst(Origin,Normal,BleedStacks,Owner);
}
