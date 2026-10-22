#include "MeteorGround.h"
#include "BlizzardEnvironment.h"
#include "GameFramework/Pawn.h"

bool MeteorGround::Validate(APawn* Caster,float Range,FVector& Point,FVector& Normal,bool bRequireSight,FString& Failure)
{
    if(!Caster||Point.ContainsNaN()||Normal.ContainsNaN()||Normal.Z<.45f)
    {Failure=TEXT("落点无效");return false;}
    // Only centimetre quantization tolerance; never a percentage range bonus.
    constexpr float NetTolerance=2.f;
    if(FVector::Dist2D(Caster->GetActorLocation(),Point)>Range+NetTolerance)
    {Failure=TEXT("超出施法距离");return false;}
    if(bRequireSight)
    {
        FVector Axis=FVector::ForwardVector;
        return BlizzardEnvironment::Validate(Caster,Range+NetTolerance,Point,Normal,Axis,Failure);
    }
    FHitResult Floor;
    if(!BlizzardEnvironment::Floor(Caster,Point,24.f,24.f,Floor)
        ||FVector::DistSquared(Floor.ImpactPoint,Point)>FMath::Square(20.f))
    {Failure=TEXT("未找到可施法地面");return false;}
    Point=Floor.ImpactPoint;Normal=Floor.ImpactNormal.GetSafeNormal();
    return true;
}
