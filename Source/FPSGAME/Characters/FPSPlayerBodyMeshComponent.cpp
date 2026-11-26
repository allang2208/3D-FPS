#include "FPSPlayerBodyMeshComponent.h"
#include "../WorldGeneration/VillageOilCarry.h"
#include "../Movement/HorseRiderComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "RenderingThread.h"
#include "SkeletalRenderPublic.h"

void UFPSPlayerBodyMeshComponent::FinalizeBoneTransform()
{
    if(bNeedToFlipSpaceBaseBuffers&&GetOwner())
        if(auto* Ride=GetOwner()->FindComponentByClass<UHorseRiderComponent>();Ride&&Ride->Active())
            Ride->ApplyPose(*this,GetEditableComponentSpaceTransforms());
    if(bNeedToFlipSpaceBaseBuffers && GetOwner())
        if(const auto* Oil=GetOwner()->FindComponentByClass<UVillageOilCarry>();Oil && Oil->Occupied())
            Oil->PoseWorldArms(*this,GetEditableComponentSpaceTransforms());
    Super::FinalizeBoneTransform();
}

bool UFPSPlayerBodyMeshComponent::IsModularPoseOnly() const
{
    return ReplacedMesh.IsValid() && ReplacedMesh.Get() == GetSkeletalMeshAsset();
}

void UFPSPlayerBodyMeshComponent::RestoreSourceRendering()
{
    if (!ReplacedMesh.IsValid()) return;
    ReplacedMesh.Reset();
    MarkRenderStateDirty();
}

void UFPSPlayerBodyMeshComponent::UpdateModularRenderOwnership()
{
    auto* Asset = GetSkeletalMeshAsset();
    // These systems can consume the source's render resources independently of
    // visible sections. Only the ordinary body-pose driver is eligible.
    if (!Asset || Asset->IsCompiling() || !GetMeshDeformerInstances().DeformerInstances.IsEmpty()
        || !GetClothingSimulationInstances().IsEmpty()
        || bCastCapsuleDirectShadow || bCastCapsuleIndirectShadow)
    { RestoreSourceRendering(); return; }
    const auto* Data = Asset->GetResourceForRendering();
    if (!Data || !Data->IsLODDataReady()) { RestoreSourceRendering(); return; }
    bool HasSections = false;
    for (int32 LOD = 0; LOD < Data->LODRenderData.Num(); ++LOD)
    {
        const auto* Info=Asset->GetLODInfo(LOD);
        const auto& Sections=Data->LODRenderData[LOD].RenderSections;
        for (int32 Index=0;Index<Sections.Num();++Index)
        {
            HasSections = true;
            int32 Material=Sections[Index].MaterialIndex;
            if(Info&&Info->LODMaterialMap.IsValidIndex(Index)&&Asset->IsValidMaterialIndex(Info->LODMaterialMap[Index]))
                Material=Info->LODMaterialMap[Index];
            if (IsMaterialSectionShown(Material, LOD))
            { RestoreSourceRendering(); return; }
        }
    }
    if (!HasSections) { RestoreSourceRendering(); return; }
    if (IsModularPoseOnly()) return;
    ReplacedMesh = Asset;
    MarkRenderStateDirty();
}

void UFPSPlayerBodyMeshComponent::CreateRenderState_Concurrent(FRegisterComponentContext* Context)
{
    if (!IsModularPoseOnly()) { Super::CreateRenderState_Concurrent(Context); return; }
    // SkinnedMesh destruction preserves this during a proxy recreation. There
    // is deliberately no replacement GPU mesh here, so retire the old buffers.
    if (PreviousMeshObject)
    {
        PreviousMeshObject->ReleaseResources();
        BeginCleanup(PreviousMeshObject);
        PreviousMeshObject = nullptr;
    }
    // Keep a valid component render-state lifecycle with a null scene proxy.
    // Bone evaluation, collision, sockets and follower poses stay registered.
    UPrimitiveComponent::CreateRenderState_Concurrent(Context);
}

FPrimitiveSceneProxy* UFPSPlayerBodyMeshComponent::CreateSceneProxy()
{
    return IsModularPoseOnly() ? nullptr : Super::CreateSceneProxy();
}
