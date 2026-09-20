#include "M4GunsmithWidget.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Components/MeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInterface.h"

void UM4GunsmithWidget::UpdatePreviewStreaming(float Delta)
{
    PreviewStreamingAccumulator+=Delta;
    if(bPreviewStreamingDirty||PreviewStreamingAccumulator>=1.f)
    {
        PreviewStreamingAccumulator=0.f;bPreviewStreamingDirty=false;
        PreviewStreamedTextures.Reset();
        if(StandaloneMelee)
        {
            for(auto* Part:ColdSteelModularSword::Components(StandaloneMelee))
            {
                TArray<UTexture*> Textures;Part->GetUsedTextures(Textures,GetCurrentMaterialQualityLevelChecked());
                for(auto* Texture:Textures)if(auto* Texture2D=Cast<UTexture2D>(Texture))PreviewStreamedTextures.AddUnique(Texture2D);
            }
        }
        for(const auto& Pair:StudioCopies)if(Pair.Key.IsValid()&&Pair.Value&&Pair.Value->IsVisible())
        {
            TArray<UTexture*> Textures;
            Pair.Value->GetUsedTextures(Textures,GetCurrentMaterialQualityLevelChecked());
            for(auto* Texture:Textures)if(auto* Texture2D=Cast<UTexture2D>(Texture))PreviewStreamedTextures.AddUnique(Texture2D);
        }
        // Renew a short lease for this assembly only. It expires after closing or
        // changing parts, without clearing another preview's residency request.
        for(const auto& Weak:PreviewStreamedTextures)if(auto* Texture=Weak.Get())Texture->SetForceMipLevelsToBeResident(3.f);
    }
    bPreviewStreamingPending=false;
    for(const auto& Weak:PreviewStreamedTextures)if(auto* Texture=Weak.Get())bPreviewStreamingPending|=Texture->HasPendingInitOrStreaming();
}

void UM4GunsmithWidget::CapturePreview()
{
    UpdatePreviewStreaming(0.f);
    PreviewCoverageCapture->ShowOnlyComponents=Capture->ShowOnlyComponents;
    PreviewCoverageCapture->SetWorldTransform(Capture->GetComponentTransform());
    PreviewCoverageCapture->ProjectionType=Capture->ProjectionType;
    PreviewCoverageCapture->FOVAngle=Capture->FOVAngle;
    PreviewCoverageCapture->OrthoWidth=Capture->OrthoWidth;
    PreviewCoverageCapture->bAutoCalculateOrthoPlanes=Capture->bAutoCalculateOrthoPlanes;
    PreviewCoverageCapture->bUseCustomProjectionMatrix=Capture->bUseCustomProjectionMatrix;
    PreviewCoverageCapture->CustomProjectionMatrix=Capture->CustomProjectionMatrix;
    PreviewCoverageCapture->CaptureScene();
    Capture->CaptureScene();
}
