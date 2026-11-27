#include "FPSFrostSurfaceMesh.h"
#include "BlizzardEnvironment.h"
#include "MagicOcclusion.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/Pawn.h"

namespace FrostSurfaceMesh
{
namespace
{
bool TraceSurface(UWorld* World, APawn* Caster, AActor* Owner, const FVector& Start, const FVector& End, FHitResult& Hit, bool bAreaSight)
{
    if (Caster) return BlizzardEnvironment::Trace(Caster, Start, End, Hit, bAreaSight);
    if (!World) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FrostSurfaceTrace), true, Owner);
    while (bAreaSight
        ? MagicOcclusion::TraceBlocker(World, Start, End, Query, Hit, nullptr)
        : World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Query))
    {
        auto* Actor = Hit.GetActor();
        auto* Component = Hit.GetComponent();
        if (Actor && (Actor->IsA<APawn>() || Actor->FindComponentByClass<UMonsterCombatComponent>()))
        { Query.AddIgnoredActor(Actor); continue; }
        if (Component && Component->ComponentHasTag(TEXT("BlizzardNonBlocking")))
        { Query.AddIgnoredComponent(Component); continue; }
        return true;
    }
    return false;
}
}

UDynamicMeshComponent* BuildConformingDisc(
    AActor* Owner,
    USceneComponent* AttachParent,
    APawn* Caster,
    const FVector& Center,
    const FVector& AxisXIn,
    float RadiusX,
    float RadiusY,
    UMaterialInterface* Material,
    TObjectPtr<UMaterialInstanceDynamic>& OutMID,
    int32 NumAngles,
    int32 NumRings,
    bool bWallOcclude,
    float LiftCM)
{
    OutMID = nullptr;
    if (!Owner || !AttachParent || !Material || RadiusX < 10.f || RadiusY < 10.f)
        return nullptr;

    NumAngles = FMath::Clamp(NumAngles, 16, 72);
    NumRings = FMath::Clamp(NumRings, 3, 20);

    FVector AxisX = FVector::VectorPlaneProject(AxisXIn, FVector::UpVector).GetSafeNormal();
    if (AxisX.IsNearlyZero()) AxisX = FVector::ForwardVector;
    const FVector AxisY = FVector::CrossProduct(FVector::UpVector, AxisX).GetSafeNormal();

    // Resolve exact center ground point & normal so ring 0 seats cleanly on slopes and stairs.
    UWorld* World = Owner->GetWorld();
    FVector Origin = Center;
    FVector OriginNormal = FVector::UpVector;
    if (Caster || World)
    {
        FHitResult CenterHit;
        if (TraceSurface(World, Caster, Owner, Center + FVector(0, 0, 50), Center - FVector(0, 0, 160), CenterHit, false)
            && !CenterHit.bStartPenetrating && CenterHit.ImpactNormal.Z >= .30f)
        {
            Origin = CenterHit.ImpactPoint;
            OriginNormal = CenterHit.ImpactNormal.GetSafeNormal();
        }
    }

    UE::Geometry::FDynamicMesh3 Mesh;
    Mesh.EnableAttributes();
    Mesh.Attributes()->EnablePrimaryColors();
    auto* Normals = Mesh.Attributes()->PrimaryNormals();
    auto* UVs = Mesh.Attributes()->PrimaryUV();
    auto* Colors = Mesh.Attributes()->PrimaryColors();

    // Vertex 0: center hub in local space relative to Origin.
    const FVector CenterLocal = OriginNormal * LiftCM + FVector(0, 0, 1.f);
    Mesh.AppendVertex(FVector3d(CenterLocal.X, CenterLocal.Y, CenterLocal.Z));
    Normals->AppendElement(FVector3f(OriginNormal));
    UVs->AppendElement(FVector2f(.5f, .5f));
    Colors->AppendElement(FVector4f(0.f, .75f, 1.f, 1.f));

    // Per-spoke running state so outward rings inherit continuous floor Z and clamp against solid walls.
    TArray<double> SpokePrevZ;
    SpokePrevZ.Init(Origin.Z, NumAngles);
    TArray<FVector> SpokePrevPos;
    SpokePrevPos.Init(Origin, NumAngles);
    TArray<bool> SpokeBlocked;
    SpokeBlocked.Init(false, NumAngles);
    TArray<float> SpokeMaxFrac;
    SpokeMaxFrac.Init(1.f, NumAngles);

    // Build concentric polar rings outward from Origin.
    for (int32 Ring = 1; Ring <= NumRings; ++Ring)
    {
        const float RawFrac = float(Ring) / float(NumRings);
        const float PrevRawFrac = float(Ring - 1) / float(NumRings);

        for (int32 A = 0; A < NumAngles; ++A)
        {
            const float Theta = (2.f * PI * float(A)) / float(NumAngles);
            const float CosA = FMath::Cos(Theta);
            const float SinA = FMath::Sin(Theta);
            const FVector RadialVec = AxisX * (CosA * RadiusX) + AxisY * (SinA * RadiusY);
            const float RadialLen = FMath::Max(1.f, float(RadialVec.Size()));

            float EffectiveFrac = FMath::Min(RawFrac, SpokeMaxFrac[A]);
            FVector TargetXY = Origin + RadialVec * EffectiveFrac;

            // Stepwise horizontal wall occlusion along the spoke: frost stops cleanly at walls/doors
            // instead of bleeding into adjacent rooms or deleting a giant 6m square cell.
            if (bWallOcclude && (Caster || World) && !SpokeBlocked[A])
            {
                const FVector RayStart(SpokePrevPos[A].X, SpokePrevPos[A].Y, SpokePrevZ[A] + 55.f);
                const FVector RayEnd(TargetXY.X, TargetXY.Y, SpokePrevZ[A] + 55.f);
                FHitResult WallHit;
                if (TraceSurface(World, Caster, Owner, RayStart, RayEnd, WallHit, true) && !WallHit.bStartPenetrating)
                {
                    SpokeBlocked[A] = true;
                    const float ClampedFrac = FMath::Lerp(PrevRawFrac, RawFrac, FMath::Clamp(WallHit.Time, 0.f, 1.f));
                    SpokeMaxFrac[A] = FMath::Max(PrevRawFrac, ClampedFrac - 4.f / RadialLen);
                    EffectiveFrac = SpokeMaxFrac[A];
                    TargetXY = Origin + RadialVec * EffectiveFrac;
                }
            }

            // Continuous ground draping over EVERY colliding surface (terrain, roads, cobbles, wood, stairs, rocks).
            FVector LocalPos(TargetXY.X - Origin.X, TargetXY.Y - Origin.Y, float(SpokePrevZ[A] - Origin.Z) + LiftCM);
            FVector SurfaceNormal = FVector::UpVector;
            float ValidAlpha = 1.f;

            if (Caster || World)
            {
                FHitResult FloorHit;
                const FVector DownStart(TargetXY.X, TargetXY.Y, SpokePrevZ[A] + 175.f);
                const FVector DownEnd(TargetXY.X, TargetXY.Y, SpokePrevZ[A] - 260.f);
                const bool bHit = TraceSurface(World, Caster, Owner, DownStart, DownEnd, FloorHit, false);
                if (bHit && !FloorHit.bStartPenetrating && FloorHit.ImpactNormal.Z >= .30f)
                {
                    const double DeltaZ = FMath::Abs(FloorHit.ImpactPoint.Z - SpokePrevZ[A]);
                    if (DeltaZ <= 140.0)
                    {
                        SurfaceNormal = FloorHit.ImpactNormal.GetSafeNormal();
                        const FVector Lifted = FloorHit.ImpactPoint + SurfaceNormal * LiftCM + FVector(0, 0, 1.f);
                        LocalPos = Lifted - Origin;
                        SpokePrevZ[A] = FloorHit.ImpactPoint.Z;
                        SpokePrevPos[A] = FloorHit.ImpactPoint;
                        ValidAlpha = 1.f;
                    }
                    else
                    {
                        // Sheer cliff or multi-story drop: fade alpha smoothly to 0 instead of stretching a vertical curtain.
                        ValidAlpha = 0.f;
                    }
                }
                else
                {
                    ValidAlpha = 0.f;
                }
            }

            // Multi-harmonic organic frost rim modulation packed in VertexColor.G.
            const float EdgeNoise = FMath::Clamp(.52f + .28f * FMath::Sin(Theta * 7.f + .45f) + .20f * FMath::Sin(Theta * 13.f + 1.9f), 0.f, 1.f);
            const FVector2f UV(.5f + .5f * EffectiveFrac * CosA, .5f + .5f * EffectiveFrac * SinA);

            Mesh.AppendVertex(FVector3d(LocalPos.X, LocalPos.Y, LocalPos.Z));
            Normals->AppendElement(FVector3f(SurfaceNormal));
            UVs->AppendElement(UV);
            Colors->AppendElement(FVector4f(EffectiveFrac, EdgeNoise, 1.f, ValidAlpha));
        }
    }

    auto AddTri = [&](int32 I0, int32 I1, int32 I2)
    {
        const int32 TID = Mesh.AppendTriangle(I0, I1, I2);
        if (TID >= 0)
        {
            const UE::Geometry::FIndex3i Idx(I0, I1, I2);
            Normals->SetTriangle(TID, Idx);
            UVs->SetTriangle(TID, Idx);
            Colors->SetTriangle(TID, Idx);
        }
    };

    // Inner hub fan (ring 1) — CCW around +Z so normals face upward.
    for (int32 A = 0; A < NumAngles; ++A)
    {
        const int32 Next = (A + 1) % NumAngles;
        AddTri(0, 1 + A, 1 + Next);
    }

    // Concentric quads for rings 2..NumRings.
    for (int32 Ring = 2; Ring <= NumRings; ++Ring)
    {
        const int32 InnerStart = 1 + (Ring - 2) * NumAngles;
        const int32 OuterStart = 1 + (Ring - 1) * NumAngles;
        for (int32 A = 0; A < NumAngles; ++A)
        {
            const int32 Next = (A + 1) % NumAngles;
            const int32 I0 = InnerStart + A;
            const int32 I1 = InnerStart + Next;
            const int32 O0 = OuterStart + A;
            const int32 O1 = OuterStart + Next;
            AddTri(I0, O0, O1);
            AddTri(I0, O1, I1);
        }
    }

    auto* Comp = NewObject<UDynamicMeshComponent>(Owner);
    Owner->AddInstanceComponent(Comp);
    Comp->SetupAttachment(AttachParent);
    Comp->SetWorldLocationAndRotation(Origin, FRotator::ZeroRotator);
    Comp->SetMobility(EComponentMobility::Movable);
    Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Comp->SetGenerateOverlapEvents(false);
    Comp->SetCanEverAffectNavigation(false);
    Comp->SetCastShadow(false);
    Comp->SetReceivesDecals(false);
    Comp->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
    Comp->SetMesh(MoveTemp(Mesh));
    OutMID = UMaterialInstanceDynamic::Create(Material, Comp);
    Comp->SetMaterial(0, OutMID ? static_cast<UMaterialInterface*>(OutMID) : Material);
    Comp->RegisterComponent();
    return Comp;
}

UDynamicMeshComponent* BuildShockRing(
    AActor* Owner,
    USceneComponent* AttachParent,
    const FVector& Origin,
    UMaterialInterface* Material,
    TObjectPtr<UMaterialInstanceDynamic>& OutMID,
    int32 NumAngles)
{
    OutMID = nullptr;
    if (!Owner || !AttachParent || !Material)
        return nullptr;

    NumAngles = FMath::Clamp(NumAngles, 24, 96);

    // 5-ring swept 3D blast-wave profile (unit outer radius = 100 cm):
    //   v=0.00 : trailing ground frost wake (r=48 cm, z=4 cm)
    //   v=0.38 : rising frozen surge slope (r=72 cm, z=20 cm)
    //   v=0.72 : sharp uplifted cryo shock crest (r=92 cm, z=56 cm)
    //   v=0.86 : forward overhanging blast lip (r=100 cm, z=36 cm)
    //   v=1.00 : leading ground edge (r=106 cm, z=4 cm)
    struct FProfile { float R; float Z; float V; float Alpha; };
    static const FProfile Profile[5] = {
        { 48.f,  4.f, 0.00f, 0.00f },
        { 72.f, 20.f, 0.38f, 0.78f },
        { 92.f, 56.f, 0.72f, 1.00f },
        {100.f, 36.f, 0.86f, 0.92f },
        {106.f,  4.f, 1.00f, 0.00f },
    };

    UE::Geometry::FDynamicMesh3 Mesh;
    Mesh.EnableAttributes();
    Mesh.Attributes()->EnablePrimaryColors();
    auto* Normals = Mesh.Attributes()->PrimaryNormals();
    auto* UVs = Mesh.Attributes()->PrimaryUV();
    auto* Colors = Mesh.Attributes()->PrimaryColors();

    for (int32 P = 0; P < 5; ++P)
    {
        for (int32 A = 0; A <= NumAngles; ++A)
        {
            const float U = float(A) / float(NumAngles);
            const float Theta = 2.f * PI * U;
            const float CosA = FMath::Cos(Theta);
            const float SinA = FMath::Sin(Theta);
            const float Ripple = 1.f + .035f * FMath::Sin(Theta * 9.f) + .022f * FMath::Cos(Theta * 17.f + .8f);
            const float R = Profile[P].R * Ripple;
            const float Z = Profile[P].Z * (.88f + .24f * FMath::Abs(FMath::Sin(Theta * 6.f + .5f)));
            const FVector Pos(CosA * R, SinA * R, Z);
            const FVector Nrm = FVector(CosA * .45f, SinA * .45f, .90f).GetSafeNormal();

            Mesh.AppendVertex(FVector3d(Pos.X, Pos.Y, Pos.Z));
            Normals->AppendElement(FVector3f(Nrm));
            UVs->AppendElement(FVector2f(U * 6.f, Profile[P].V));
            Colors->AppendElement(FVector4f(Profile[P].V, 1.f, 1.f, Profile[P].Alpha));
        }
    }

    const int32 Stride = NumAngles + 1;
    auto AddTri = [&](int32 I0, int32 I1, int32 I2)
    {
        const int32 TID = Mesh.AppendTriangle(I0, I1, I2);
        if (TID >= 0)
        {
            const UE::Geometry::FIndex3i Idx(I0, I1, I2);
            Normals->SetTriangle(TID, Idx);
            UVs->SetTriangle(TID, Idx);
            Colors->SetTriangle(TID, Idx);
        }
    };

    for (int32 P = 0; P < 4; ++P)
    {
        const int32 R0 = P * Stride;
        const int32 R1 = (P + 1) * Stride;
        for (int32 A = 0; A < NumAngles; ++A)
        {
            AddTri(R0 + A, R1 + A, R1 + A + 1);
            AddTri(R0 + A, R1 + A + 1, R0 + A + 1);
        }
    }

    auto* Comp = NewObject<UDynamicMeshComponent>(Owner);
    Owner->AddInstanceComponent(Comp);
    Comp->SetupAttachment(AttachParent);
    Comp->SetWorldLocationAndRotation(Origin, FRotator::ZeroRotator);
    Comp->SetMobility(EComponentMobility::Movable);
    Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Comp->SetGenerateOverlapEvents(false);
    Comp->SetCanEverAffectNavigation(false);
    Comp->SetCastShadow(false);
    Comp->SetReceivesDecals(false);
    Comp->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
    Comp->SetMesh(MoveTemp(Mesh));
    OutMID = UMaterialInstanceDynamic::Create(Material, Comp);
    Comp->SetMaterial(0, OutMID ? static_cast<UMaterialInterface*>(OutMID) : Material);
    Comp->RegisterComponent();
    return Comp;
}
}
