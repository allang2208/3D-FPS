#include "PitViper2011SICompensator.h"
#include "PitViper2011WeaponAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

void PitViper2011SICompensator::ShowFactory(USkeletalMeshComponent* Host, bool bVisible)
{
    if (!PitViper2011WeaponAssets::Matches(Host)) return;
    const auto* Asset = Host->GetSkeletalMeshAsset();
    const auto* Render = Asset->GetResourceForRendering();
    if (!Render) return;
    for (int32 L = 0; L < Render->LODRenderData.Num(); ++L)
        for (int32 S = 0; S < Render->LODRenderData[L].RenderSections.Num(); ++S)
        {
            const int32 M = Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            if (Asset->GetMaterials().IsValidIndex(M)
                && Asset->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("FactoryCompensator")))
                Host->ShowMaterialSection(M, S, bVisible, L);
        }
}
