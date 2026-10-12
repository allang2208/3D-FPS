#include "BellowSacProjectile.h"
#include "FPSCombatHealthComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

bool ABellowSacProjectile::IsWarningSceneSurface(const FHitResult& Hit)
{
    const UPrimitiveComponent* Component = Hit.GetComponent();
    if (!Component || Hit.bStartPenetrating || Cast<USkinnedMeshComponent>(Component)
        || Component->GetCollisionResponseToChannel(ECC_Visibility) != ECR_Block) return false;
    // Also exclude equipment, child actors and detached corpses carrying health.
    const auto IsUnit = [](const AActor* Actor)
    { return Actor && (Actor->IsA<APawn>() || Actor->FindComponentByClass<UFPSCombatHealthComponent>()); };
    const AActor* Actor = Component->GetOwner();
    for (int32 Depth = 0; Actor && Depth < 8; ++Depth, Actor = Actor->GetOwner())
        if (IsUnit(Actor)) return false;
    Actor = Component->GetOwner();
    for (int32 Depth = 0; Actor && Depth < 8; ++Depth, Actor = Actor->GetAttachParentActor())
        if (IsUnit(Actor)) return false;
    return true;
}

void ABellowSacProjectile::BuildWarningSurface()
{
    using namespace UE::Geometry;
    bWarningSurfaceBuilt = true;
    constexpr int32 Segments = 64, Count = Segments * 2;
    constexpr float LiftCM = .6f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BellowWarningSurface), true, this);
    if (GetOwner()) Query.AddIgnoredActor(GetOwner());
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    TArray<FHitResult> Hits;
    const auto TraceScene = [&](const FVector& Start, const FVector& End, FHitResult& Out)
    {
        Hits.Reset();
        GetWorld()->LineTraceMultiByObjectType(Hits, Start, End, Objects, Query);
        bool Found = false;
        for (const FHitResult& Hit : Hits)
            if (IsWarningSceneSurface(Hit) && (!Found || Hit.Time < Out.Time))
            { Out = Hit; Found = true; }
        return Found;
    };

    // A unit's capsule normal must never orient the environmental warning.
    // For scene contact, refine the sweep's simple collision against geometry.
    FHitResult Anchor;
    const FVector ImpactNormal = SurfaceNormal.GetSafeNormal();
    bool Found = bSceneContact && TraceScene(ContactPoint + ImpactNormal * 12.f,
        ContactPoint - ImpactNormal * 32.f, Anchor);
    if (!Found)
        Found = TraceScene(GetActorLocation() + FVector(0, 0, 8.f),
            GetActorLocation() - FVector(0, 0, BlastRadius), Anchor);
    if (!Found) return; // No affected scenery: the existing HUD warning remains.

    const FVector Normal = Anchor.ImpactNormal.GetSafeNormal();
    const FVector Explosion = GetActorLocation();
    const float Height = FVector::DotProduct(Explosion - Anchor.ImpactPoint, Normal);
    if (FMath::Abs(Height) >= BlastRadius) return;
    const FVector Center = Explosion - Normal * Height;
    const float Radius = FMath::Sqrt(FMath::Square(BlastRadius) - FMath::Square(Height));
    const float InnerRadius = FMath::Max(0.f, Radius - FMath::Max(1.4f, Radius * .01f));
    const float Reach = FMath::Min(45.f, BlastRadius * .35f);
    FVector Tangent, Bitangent;
    Normal.FindBestAxisVectors(Tangent, Bitangent);

    // Fixed work once per fuse: at most 130 scene traces and 128 triangles.
    // Cache in world space so capsule rotation, scale and replication cannot tilt it.
    FDynamicMesh3 Mesh;
    Mesh.EnableAttributes();
    FVector Points[Count], Normals[Count];
    bool Valid[Count]{};
    for (int32 I = 0; I < Segments; ++I)
    {
        const float Angle = 2.f * PI * I / Segments;
        const FVector Radial = Tangent * FMath::Cos(Angle) + Bitangent * FMath::Sin(Angle);
        for (int32 Edge = 0; Edge < 2; ++Edge)
        {
            const int32 Index = I * 2 + Edge;
            const FVector Sample = Center + Radial * (Edge ? Radius : InnerRadius);
            FHitResult Hit;
            Valid[Index] = TraceScene(Sample + Normal * Reach, Sample - Normal * Reach, Hit)
                && FVector::DotProduct(Hit.ImpactNormal, Normal) > .5f
                && FVector::DistSquared(Hit.ImpactPoint, Explosion) <= FMath::Square(BlastRadius + 2.f);
            Points[Index] = Valid[Index] ? Hit.ImpactPoint : Sample;
            Normals[Index] = Valid[Index] ? Hit.ImpactNormal.GetSafeNormal() : Normal;
            Mesh.AppendVertex(FVector3d(Points[Index] + Normals[Index] * LiftCM - Center));
            Mesh.Attributes()->PrimaryNormals()->AppendElement(FVector3f(Normals[Index]));
            Mesh.Attributes()->PrimaryUV()->AppendElement(FVector2f(float(I) / Segments, float(Edge)));
        }
    }
    const auto Connected = [&](int32 A, int32 B)
    {
        const FVector Delta = Points[B] - Points[A];
        const FVector N = (Normals[A] + Normals[B]).GetSafeNormal();
        // Break at ledges and stairs; never bridge floors with a vertical ribbon.
        return FVector::DotProduct(Normals[A], Normals[B]) > .65f
            && FMath::Abs(FVector::DotProduct(Delta, N)) < 3.f;
    };
    const auto Triangle = [&](int32 A, int32 B, int32 C)
    {
        if (!Valid[A] || !Valid[B] || !Valid[C] || !Connected(A, B) || !Connected(B, C) || !Connected(C, A)) return;
        const int32 T = Mesh.AppendTriangle(A, B, C);
        if (T < 0) return;
        const FIndex3i Indices(A, B, C);
        Mesh.Attributes()->PrimaryNormals()->SetTriangle(T, Indices);
        Mesh.Attributes()->PrimaryUV()->SetTriangle(T, Indices);
    };
    for (int32 I = 0; I < Segments; ++I)
    {
        const int32 A = I * 2, B = ((I + 1) % Segments) * 2;
        Triangle(A, B, B + 1);
        Triangle(A, B + 1, A + 1);
    }
    const bool HasSurface = Mesh.TriangleCount() > 0;
    WarningRing->SetWorldTransform(FTransform(FQuat::Identity, Center, FVector::OneVector));
    WarningRing->SetMesh(MoveTemp(Mesh));
    WarningRing->SetVisibility(HasSurface);
}
