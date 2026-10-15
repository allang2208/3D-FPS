#include "ProductionToolComponent.h"
#include "../Weapons/RuneSwordWhirlwindFeel.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "SceneInterface.h"
#include "Engine/World.h"

void UProductionToolComponent::BeginBluntWhirlwindFocus()
{
    if(!Camera||!Viewmodel)return;
    bBluntWhirlwindFocusActive=true;
    auto& PP=Camera->PostProcessSettings;
    BluntWhirlwindSavedBlur=PP.MotionBlurAmount;bBluntWhirlwindSavedBlurOverride=PP.bOverride_MotionBlurAmount;
    PP.bOverride_MotionBlurAmount=true;PP.MotionBlurAmount=0.f;
    const FSoftObjectPath Path(TEXT("/Game/Skills/Whirlwind20260920/M_WhirlwindFocus.M_WhirlwindFocus"));
    if(!BluntWhirlwindFocus)
        if(auto* Material=Cast<UMaterialInterface>(Path.ResolveObject()))BluntWhirlwindFocus=UMaterialInstanceDynamic::Create(Material,this);
    TArray<USceneComponent*> Parts;Viewmodel->GetChildrenComponents(true,Parts);Parts.Add(Viewmodel);
    for(auto* Part:Parts)
        if(auto* Primitive=Cast<UPrimitiveComponent>(Part))
        {
            BluntWhirlwindDepth.Add({Primitive,bool(Primitive->bRenderCustomDepth),Primitive->CustomDepthStencilValue,uint8(Primitive->CustomDepthStencilWriteMask)});
            Primitive->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
            Primitive->SetCustomDepthStencilValue(231);Primitive->SetRenderCustomDepth(true);
        }
}

void UProductionToolComponent::UpdateBluntWhirlwindFocus()
{
    if(!Camera||!BluntWhirlwindFocus)return;
    const float Strength=BluntWhirlwindPause>0.f?0.f:BluntWhirlwindTuning.MotionBlur*WhirlwindFeel::Speed(BluntWhirlwindTime,BluntWhirlwindTuning);
    BluntWhirlwindFocus->SetScalarParameterValue(TEXT("Strength"),Strength);
    const auto* Resource=GetWorld()->Scene?BluntWhirlwindFocus->GetMaterialResource(GetWorld()->Scene->GetShaderPlatform()):nullptr;
    // Same background-only material and ready-shader gate as the sword; never
    // display the engine's coloured fallback around the screen border.
    if(Strength>UE_SMALL_NUMBER&&Resource&&Resource->GetGameThreadShaderMap()&&Resource->IsGameThreadShaderMapComplete())
        Camera->PostProcessSettings.AddBlendable(BluntWhirlwindFocus,1.f);
    else Camera->PostProcessSettings.RemoveBlendable(BluntWhirlwindFocus);
}

void UProductionToolComponent::EndBluntWhirlwindFocus()
{
    if(!bBluntWhirlwindFocusActive)return;bBluntWhirlwindFocusActive=false;
    if(Camera)
    {
        if(BluntWhirlwindFocus)Camera->PostProcessSettings.RemoveBlendable(BluntWhirlwindFocus);
        Camera->PostProcessSettings.MotionBlurAmount=BluntWhirlwindSavedBlur;
        Camera->PostProcessSettings.bOverride_MotionBlurAmount=bBluntWhirlwindSavedBlurOverride;
    }
    for(const auto& Saved:BluntWhirlwindDepth)
        if(auto* Part=Saved.Part.Get())
        {
            Part->SetRenderCustomDepth(Saved.Enabled);Part->SetCustomDepthStencilValue(Saved.Stencil);
            Part->SetCustomDepthStencilWriteMask(ERendererStencilMask(Saved.WriteMask));
        }
    BluntWhirlwindDepth.Reset();
}
