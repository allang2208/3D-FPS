#include "MonsterCorpseMeshComponent.h"
#include "Engine/World.h"
#include "Materials/MaterialRelevance.h"

namespace
{
bool CanCacheFrozenShadow(const USkinnedMeshComponent& Mesh)
{
    if (!Mesh.GetWorld() || !Mesh.GetWorld()->IsGameWorld() || Mesh.GetNetMode() == NM_DedicatedServer
        || Mesh.IsComponentTickEnabled() || Mesh.IsSimulatingPhysics() || !Mesh.CastShadow
        || Mesh.GetOverlayMaterial() || Mesh.GetMeshDeformerInstance()) return false;
    TArray<TObjectPtr<UMaterialInterface>> Overlays;
    Mesh.GetMaterialSlotsOverlayMaterial(Overlays);
    for (const auto& Material : Overlays) if (Material) return false;
    if (const auto* Skeletal = Cast<USkeletalMeshComponent>(&Mesh))
        if (!Skeletal->GetClothingSimulationInstances().IsEmpty() && !Skeletal->IsClothingSimulationSuspended()) return false;
    // A held skeleton can still have animated opacity or shader geometry.
    const FMaterialRelevance R = Mesh.GetMaterialRelevance(GShaderPlatformForFeatureLevel[Mesh.GetWorld()->GetFeatureLevel()]);
    return R.bOpaque && !R.bMasked && !R.bNormalTranslucency && !R.bSeparateTranslucency
        && !R.bPostMotionBlurTranslucency && !R.bUsesWorldPositionOffset
        && !R.bUsesDisplacement && !R.bUsesPixelDepthOffset;
}

void BeginCaching(USkinnedMeshComponent& Mesh, bool& Managed)
{
    if (Managed || Mesh.ShadowCacheInvalidationBehavior != EShadowCacheInvalidationBehavior::Auto
        || !CanCacheFrozenShadow(Mesh)) return;
    Managed = true;
    // Keep transform, light and reveal invalidations; only stop unconditional
    // deformable-shadow invalidation while this exact corpse pose is held.
    Mesh.ShadowCacheInvalidationBehavior = EShadowCacheInvalidationBehavior::Rigid;
    Mesh.MarkRenderStateDirty();
}

void EndCaching(USkinnedMeshComponent& Mesh, bool& Managed, bool RecreatingProxy)
{
    if (!Managed) return;
    Managed = false;
    if (Mesh.ShadowCacheInvalidationBehavior == EShadowCacheInvalidationBehavior::Rigid)
    {
        Mesh.ShadowCacheInvalidationBehavior = EShadowCacheInvalidationBehavior::Auto;
        if (!RecreatingProxy) Mesh.MarkRenderStateDirty();
    }
}
}

void UMonsterCorpseMeshComponent::BeginFrozenShadowCaching()
{ BeginCaching(*this, bFrozenShadowCacheManaged); }

void UMonsterCorpseMeshComponent::FinalizeBoneTransform()
{
    // LOD changes and reactivation must invalidate the old silhouette before
    // the new pose is dispatched. The frozen LOD owner can cache it again.
    EndCaching(*this, bFrozenShadowCacheManaged, false);
    Super::FinalizeBoneTransform();
}

FPrimitiveSceneProxy* UMonsterCorpseMeshComponent::CreateSceneProxy()
{
    if (bFrozenShadowCacheManaged && !CanCacheFrozenShadow(*this))
        EndCaching(*this, bFrozenShadowCacheManaged, true);
    return Super::CreateSceneProxy();
}

void UMonsterCorpsePoseableMeshComponent::BeginFrozenShadowCaching()
{
    bFrozenPose = true;
    BeginCaching(*this, bFrozenShadowCacheManaged);
}

void UMonsterCorpsePoseableMeshComponent::FinalizeBoneTransform()
{
    EndCaching(*this, bFrozenShadowCacheManaged, false);
    Super::FinalizeBoneTransform();
    // The shared LOD timer may refresh the held soft-body pose. It owns no
    // animation/physics clock, and can cache the refreshed silhouette again.
    if (bFrozenPose) BeginCaching(*this, bFrozenShadowCacheManaged);
}

FPrimitiveSceneProxy* UMonsterCorpsePoseableMeshComponent::CreateSceneProxy()
{
    if (bFrozenShadowCacheManaged && !CanCacheFrozenShadow(*this))
        EndCaching(*this, bFrozenShadowCacheManaged, true);
    return Super::CreateSceneProxy();
}
