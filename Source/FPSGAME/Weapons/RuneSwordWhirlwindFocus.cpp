#include "RuneSwordComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "Engine/World.h"
#include "SceneInterface.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/IConsoleManager.h"

namespace
{
TSharedPtr<FJsonObject> ForegroundMaterials()
{
    const auto* Enabled=IConsoleManager::Get().FindConsoleVariable(TEXT("r.Velocity.TemporalResponsiveness.Supported"));
    if(!Enabled||Enabled->GetInt()==0)return nullptr;
    FString Json;TSharedPtr<FJsonObject> Root;
    FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/whirlwind-temporal-materials.json")));
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root);
    return Root;
}
UMaterialInterface* ResponsiveMaterial(UMaterialInterface* Source,const TSharedPtr<FJsonObject>& Map,UObject* Owner)
{
    if(!Source||!Map)return Source;
    UMaterialInterface* Asset=Source;
    while(auto* Dynamic=Cast<UMaterialInstanceDynamic>(Asset))Asset=Dynamic->Parent;
    FString Path;
    if(!Asset||!Map->TryGetStringField(Asset->GetPathName(),Path))return Source;
    auto* Responsive=LoadObject<UMaterialInterface>(nullptr,*Path);
    if(!Responsive)return Source;
    // The duplicate keeps static switches; copy uniforms to preserve equipped
    // finishes, textures and animated rune parameters from the live material.
    auto* Instance=UMaterialInstanceDynamic::Create(Responsive,Owner);
    Instance->CopyMaterialUniformParameters(Source);
    return Instance;
}
}

void URuneSwordComponent::BeginWhirlwindFocus()
{
    if(!WhirlwindFocusMaterial)
    {
        auto* Source=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/Whirlwind20260920/M_WhirlwindFocus.M_WhirlwindFocus"));
        if(Source)WhirlwindFocusMaterial=UMaterialInstanceDynamic::Create(Source,this);
    }
    // Screen-space background blur owns this effect. Ordinary full-frame motion
    // blur would smear the already masked foreground before this pass runs.
    Camera->PostProcessSettings.bOverride_MotionBlurAmount=true;
    Camera->PostProcessSettings.MotionBlurAmount=0.f;
    const auto Materials=ForegroundMaterials();
    TArray<USceneComponent*> Parts;Viewmodel->GetChildrenComponents(true,Parts);
    Parts.Add(Viewmodel);
    WhirlwindDepthStates.Empty();
    for(auto* Part:Parts)
    {
        auto* Primitive=Cast<UPrimitiveComponent>(Part);if(!Primitive)continue;
        FWhirlwindDepthState Saved;
        Saved.Primitive=Primitive;Saved.bRenderCustomDepth=Primitive->bRenderCustomDepth;
        Saved.Stencil=Primitive->CustomDepthStencilValue;Saved.WriteMask=uint8(Primitive->CustomDepthStencilWriteMask);
        if(Materials)
            if(auto* Mesh=Cast<UMeshComponent>(Primitive))
                for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
                {
                    auto* Original=Mesh->GetMaterial(Slot);
                    auto* Overlay=Mesh->GetOverlayMaterial(true,Slot);
                    Saved.Materials.Emplace(Original);Saved.OverlayMaterials.Emplace(Overlay);
                    Mesh->SetMaterial(Slot,ResponsiveMaterial(Original,Materials,this));
                    Mesh->SetOverlayMaterial(ResponsiveMaterial(Overlay,Materials,this),true,Slot);
                }
        WhirlwindDepthStates.Add(MoveTemp(Saved));
        Primitive->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
        Primitive->SetCustomDepthStencilValue(231);
        Primitive->SetRenderCustomDepth(true);
    }
    if(WhirlwindFocusMaterial)
    {
        WhirlwindFocusMaterial->SetScalarParameterValue(TEXT("Strength"),0.f);
        Camera->PostProcessSettings.RemoveBlendable(WhirlwindFocusMaterial);
    }
}

void URuneSwordComponent::SetWhirlwindFocus(float Strength)
{
    Camera->PostProcessSettings.MotionBlurAmount=0.f;
    if(!WhirlwindFocusMaterial)return;
    WhirlwindFocusMaterial->SetScalarParameterValue(TEXT("Strength"),Strength);
    const auto* World=GetWorld();
    const auto* Resource=World&&World->Scene
        ?WhirlwindFocusMaterial->GetMaterialResource(World->Scene->GetShaderPlatform()):nullptr;
    // UE's default post-process fallback draws a brown/yellow screen rim.
    // A zero Strength parameter cannot hide it: that shader does not use ours.
    // Only attach the actual blur once its shaders are ready, and remove it
    // during windup, hitstop and recovery when no blur is requested.
    if(Strength>UE_SMALL_NUMBER&&Resource&&Resource->GetGameThreadShaderMap()&&Resource->IsGameThreadShaderMapComplete())
        Camera->PostProcessSettings.AddBlendable(WhirlwindFocusMaterial,1.f);
    else
        Camera->PostProcessSettings.RemoveBlendable(WhirlwindFocusMaterial);
}

void URuneSwordComponent::EndWhirlwindFocus()
{
    if(Camera&&WhirlwindFocusMaterial)Camera->PostProcessSettings.RemoveBlendable(WhirlwindFocusMaterial);
    for(const auto& Saved:WhirlwindDepthStates)
        if(auto* Primitive=Saved.Primitive.Get())
        {
            Primitive->SetRenderCustomDepth(Saved.bRenderCustomDepth);
            Primitive->SetCustomDepthStencilValue(Saved.Stencil);
            Primitive->SetCustomDepthStencilWriteMask(ERendererStencilMask(Saved.WriteMask));
            if(auto* Mesh=Cast<UMeshComponent>(Primitive))
                for(int32 Slot=0;Slot<Saved.Materials.Num();++Slot)
                {
                    Mesh->SetMaterial(Slot,Saved.Materials[Slot].Get());
                    Mesh->SetOverlayMaterial(Saved.OverlayMaterials[Slot].Get(),true,Slot);
                }
        }
    WhirlwindDepthStates.Reset();
}
