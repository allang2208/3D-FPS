#include "FireMagicArea.h"
#include "../Combat/RangedAttackQuery.h"
#include "MagicOcclusion.h"
#include "HolyLightTargets.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"

bool FireMagic::TraceSurface(APawn* Shooter,const FVector& Start,const FVector& End,FHitResult& Hit,bool bAreaSight)
{
    if(!Shooter||!Shooter->GetWorld())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireMagicSurface),true,Shooter);
    while(bAreaSight?MagicOcclusion::TraceBlocker(Shooter->GetWorld(),Start,End,Query,Hit,Shooter):
        RangedAttackQuery::LineTraceSingle(Shooter->GetWorld(),Shooter,Hit,Start,End,ECC_Visibility,Query))
    {
        AActor* Actor=Hit.GetActor();
        if(!Actor||(!Actor->IsA<APawn>()&&!Actor->FindComponentByClass<UMonsterCombatComponent>()))return true;
        Query.AddIgnoredActor(Actor);
    }
    return false;
}

TArray<AActor*> FireMagic::GroundTargets(APawn* Shooter,const FVector& Center,const FVector& Normal,float Radius)
{
    TArray<AActor*> Targets;if(!Shooter||!Shooter->GetWorld())return Targets;
    for(TActorIterator<AActor> It(Shooter->GetWorld());It;++It)
    {
        AActor* Target=*It;auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(Target==Shooter||!Combat||Combat->IsDead()||RangedAttackQuery::IsFriendlyUnit(Shooter,Target))continue;
        FVector Origin,Extent;Target->GetActorBounds(true,Origin,Extent);
        FVector Feet=Origin-FVector(0,0,Extent.Z);float BodyRadius=FMath::Min(Extent.X,Extent.Y);
        if(const auto* Capsule=Target->FindComponentByClass<UCapsuleComponent>())
        {Feet=Capsule->GetComponentLocation()-FVector(0,0,Capsule->GetScaledCapsuleHalfHeight());BodyRadius=Capsule->GetScaledCapsuleRadius();}
        const FVector Offset=Feet-Center;const float Height=FVector::DotProduct(Offset,Normal);
        if(FMath::Abs(Height)>100.f||(Offset-Normal*Height).SizeSquared()>FMath::Square(Radius+BodyRadius))continue;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(FireMagicAreaSight),false,Shooter);Query.AddIgnoredActor(Target);
        if(!MagicOcclusion::HasExposure(Shooter->GetWorld(),Target,Center+Normal*35,Query,Shooter))continue;
        Targets.Add(Target);
    }
    return Targets;
}
