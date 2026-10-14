#include "MagicOcclusion.h"
#include "../Combat/RangedAttackQuery.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"

bool MagicOcclusion::IsOpenBarrier(const UPrimitiveComponent* Component)
{
    if(!Component)return false;
    static const FName Permeable(TEXT("Magic.Permeable"));
    static const FName Guardrail(TEXT("Traversal.GuardrailDrop"));
    if(Component->ComponentHasTag(Permeable)||Component->ComponentHasTag(Guardrail))return true;
    // Authored dungeon railings are separate static-mesh actors. Never ignore
    // an entire stairs/building actor, which may also contain solid floors.
    const auto* MeshActor=Cast<AStaticMeshActor>(Component->GetOwner());
    return MeshActor&&MeshActor->GetStaticMeshComponent()==Component&&MeshActor->ActorHasTag(Guardrail);
}
void MagicOcclusion::BodySamples(const AActor* Target,const FVector& From,FBodySamples& Out)
{
    Out.Reset();
    const auto* Body=Cast<UPrimitiveComponent>(Target->GetRootComponent());
    if(!Body){Out.Add(Target->GetActorLocation());return;}
    FVector Center=Body->Bounds.Origin,Up=FVector::UpVector;
    float Height=Body->Bounds.BoxExtent.Z,Radius=FMath::Min(Body->Bounds.BoxExtent.X,Body->Bounds.BoxExtent.Y);
    if(const auto* Capsule=Cast<UCapsuleComponent>(Body))
    {
        Center=Capsule->GetComponentLocation();Up=Capsule->GetUpVector();
        Height=Capsule->GetScaledCapsuleHalfHeight();Radius=Capsule->GetScaledCapsuleRadius();
    }
    FVector Side=FVector::CrossProduct(Up,Center-From).GetSafeNormal();
    if(Side.IsNearlyZero())Side=Body->GetRightVector();
    // All probes remain inside the target's body. One bar covering its centre
    // must not hide exposed head/feet/shoulders; a full wall blocks every ray.
    Out.Add(Center);
    Out.Add(Center+Up*(Height*.65f));Out.Add(Center-Up*(Height*.65f));
    Out.Add(Center+Side*(Radius*.65f));Out.Add(Center-Side*(Radius*.65f));
}

bool MagicOcclusion::TraceBlocker(UWorld* World,const FVector& Start,const FVector& End,
    const FCollisionQueryParams& Query,FHitResult& Hit,const AActor* RangedSource)
{
    FCollisionQueryParams Sight=Query;
    Sight.bTraceComplex=true; // Honour actual holes instead of a coarse collision hull.
    for(int32 Pass=0;Pass<16;++Pass)
    {
        if(!RangedAttackQuery::LineTraceSingle(World,RangedSource,Hit,Start,End,ECC_Visibility,Sight))return false;
        if(!IsOpenBarrier(Hit.GetComponent()))return true;
        Sight.AddIgnoredComponent(Hit.GetComponent());
        // Trace the entire segment again: a wall behind the railing still blocks.
    }
    return true;
}

bool MagicOcclusion::HasExposure(UWorld* World,const AActor* Target,const FVector& From,
    const FCollisionQueryParams& Query,const AActor* RangedSource)
{
    FCollisionQueryParams Sight=Query;Sight.AddIgnoredActor(Target);
    FBodySamples Samples;BodySamples(Target,From,Samples);
    for(const FVector& Sample:Samples)
    {
        FHitResult Block;
        if(!TraceBlocker(World,From,Sample,Sight,Block,RangedSource))return true;
    }
    return false;
}
