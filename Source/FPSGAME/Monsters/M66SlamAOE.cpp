#include "M66IncineratorMonster.h"
#include "M66SlamTiming.h"
#include "M66SlamWave.h"
#include "M66AudioComponent.h"
#include "MonsterCombatComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

bool AM66IncineratorMonster::FindSlamGround(FHitResult& Ground) const
{
    if(SlamFrames.IsEmpty())return false;
    const FM66SweepFrame* Contact=&SlamFrames[0];
    for(const auto& Frame:SlamFrames)
        if(FMath::Abs(Frame.Time-M66SlamTiming::Impact)<FMath::Abs(Contact->Time-M66SlamTiming::Impact))Contact=&Frame;
    if(Contact->Points.IsEmpty())return false;
    float Low=MAX_flt;
    for(const auto& Point:Contact->Points)Low=FMath::Min(Low,float(SweepPointWorld(Point,true).Z));
    FVector Centre=FVector::ZeroVector;int32 Count=0;
    for(const auto& Point:Contact->Points)
    {
        const FVector WorldPoint=SweepPointWorld(Point,true);
        if(WorldPoint.Z<=Low+SlamHitRadius){Centre+=WorldPoint;++Count;}
    }
    Centre/=FMath::Max(1,Count);
    const FVector From=Centre+FVector(0,0,80),To=Centre-FVector(0,0,180);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M66SlamFloor),false,this);
    // A victim standing at the landing point is not the ground surface.
    while(GetWorld()->LineTraceSingleByChannel(Ground,From,To,ECC_Visibility,Query))
    {
        const AActor* Actor=Ground.GetActor();
        if(Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>()))
        {Query.AddIgnoredActor(Actor);continue;}
        return Ground.ImpactNormal.Z>=.5f;
    }
    return false;
}
bool AM66IncineratorMonster::SlamAreaCanReach(const APawn* Victim) const
{
    FHitResult Ground;if(!Victim||!FindSlamGround(Ground))return false;
    float Radius=0,Half=0;Victim->GetSimpleCollisionCylinder(Radius,Half);
    const FVector Feet=Victim->GetActorLocation()-FVector(0,0,Half),Delta=Feet-Ground.ImpactPoint;
    const float Height=FVector::DotProduct(Delta,Ground.ImpactNormal);
    return FMath::Abs(Height)<=75.f&&(Delta-Ground.ImpactNormal*Height).SizeSquared()<=FMath::Square(SlamAreaRadius+Radius);
}
void AM66IncineratorMonster::ReleaseSlamWave()
{
    if(!HasAuthority()||!IsGroundSlamming())return;
    FHitResult Ground;if(!FindSlamGround(Ground))return;
    BodyAudio->Emit(TEXT("SlamImpact"),Ground.ImpactPoint,Sweep.StartedAt+M66SlamTiming::Impact);
    const FTransform Transform(FRotationMatrix::MakeFromZ(Ground.ImpactNormal).ToQuat(),Ground.ImpactPoint);
    auto* Wave=GetWorld()->SpawnActorDeferred<AM66SlamWave>(AM66SlamWave::StaticClass(),Transform,this,this,
        ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!Wave)return;
    Wave->Setup(SlamDamage,SlamAreaRadius,SlamWaveSeconds,SlamStunSeconds,SlamWaveMaterial,
        Sweep.StartedAt+M66SlamTiming::Impact);
    UGameplayStatics::FinishSpawningActor(Wave,Transform);
}
