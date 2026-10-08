#include "M4GunsmithWidget.h"
#include "GunsmithPreviewLighting.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/Bow/BowAssembly.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "Components/MeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "../Weapons/LMG201WeaponAssets.h"
#include "../Weapons/PitViper2011WeaponAssets.h"
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
            TArray<UMeshComponent*> Parts;
            if(ColdSteelBowAssembly::IsBowRoot(StandaloneMelee))Parts=ColdSteelBowAssembly::Components(StandaloneMelee);
            else if(IsStaffWorkbench()){for(auto* Part:ColdSteelStaffAssembly::Components(StandaloneMelee))Parts.Add(Part);}
            else for(auto* Part:ColdSteelModularSword::Components(StandaloneMelee))Parts.Add(Part);
            for(auto* Part:Parts)
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
    // Gun framing excludes hidden arms and includes every fitted attachment.
    // Static workbench assemblies and ADS instead use their visible components.
    FBox LightBounds=(!StandaloneMelee&&!bAimPreview)?PreviewFramingBounds:FBox(ForceInit);
    if(!LightBounds.IsValid)
    {
        const FTransform ToView=Capture->GetComponentTransform().Inverse();
        for(const auto& Weak:Capture->ShowOnlyComponents)
            if(auto* Part=Weak.Get();Part&&Part->IsVisible())LightBounds+=Part->Bounds.GetBox().TransformBy(ToView);
    }
    bool bGraphite201=false,bPitViper2011=false;
    for(const auto& Pair:StudioCopies)
        if(Pair.Key.IsValid()&&Pair.Value&&Pair.Value->IsVisible())
            if(auto* Skinned=Cast<USkeletalMeshComponent>(Pair.Value))
            {
                bGraphite201|=LMG201WeaponAssets::Matches(Skinned);
                bPitViper2011|=PitViper2011WeaponAssets::Matches(Skinned);
            }
    // Recalculate family-specific levels when the same widget changes weapons.
    // A restrained Pit Viper fill preserves contrast between its WS black
    // coating, copper barrel and polymer grip in the compact studio framing.
    const float KeyLevel=bPitViper2011?2.2f:bGraphite201?2.5f:6.f;
    const float FillLevel=bPitViper2011?.5f:bGraphite201?.65f:3.f;
    const float SkyLevel=bPitViper2011?.25f:bGraphite201?.28f:1.f;
    if(!FMath::IsNearlyEqual(Studio->DirectionalLight->Intensity,KeyLevel))Studio->SetLightBrightness(KeyLevel);
    if(StudioFill&&!FMath::IsNearlyEqual(StudioFill->Intensity,FillLevel))StudioFill->SetIntensity(FillLevel);
    if(!FMath::IsNearlyEqual(Studio->SkyLight->Intensity,SkyLevel))Studio->SetSkyBrightness(SkyLevel);
    // The broad XuanChi blade and pale silk highlights clip under the default
    // studio softboxes. Preserve the authored PBR colors with a lower light flux.
    const bool bXuanChi=StandaloneMelee&&StandaloneKey.Contains(TEXT("|ue_xuanchi_zhenyue|"));
    GunsmithPreviewLighting::Update(*Capture,LightBounds,bGraphite201||bPitViper2011,bXuanChi?.025f:1.f);
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
