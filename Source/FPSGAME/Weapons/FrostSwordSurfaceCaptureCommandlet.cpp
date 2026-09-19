#include "FrostSwordSurfaceCaptureCommandlet.h"
#include "MeleeRuneVisual.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/TextureCube.h"
#include "Engine/World.h"
#include "ImageUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "RenderingThread.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Kismet/GameplayStatics.h"

int32 UFrostSwordSurfaceCaptureCommandlet::Main(const FString& Params)
{
    FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/FrostSwordSurfaceFix20260915/Before");
    FParse::Value(*Params,TEXT("Out="),Out);IFileManager::Get().MakeDirectory(*Out,true);
    FString Guard;FParse::Value(*Params,TEXT("Guard="),Guard);
    const bool Closeup=FParse::Param(*Params,TEXT("GuardCloseup"));
    const int32 Width=Closeup?1100:900,Height=Closeup?650:1100;
    FString AssetRoot=TEXT("/Game/Weapons/FrostCrystalSword20260915/");FParse::Value(*Params,TEXT("AssetRoot="),AssetRoot);
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* W=UWorld::CreateWorld(EWorldType::GamePreview,false,TEXT("FrostSurfaceReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* A=W->SpawnActor<AActor>();
    auto* Light=NewObject<UDirectionalLightComponent>(A);A->AddInstanceComponent(Light);Light->SetIntensity(3);
    Light->SetWorldRotation(FRotator(-35,-60,0));Light->RegisterComponent();
    auto* Fill=NewObject<UDirectionalLightComponent>(A);A->AddInstanceComponent(Fill);Fill->SetIntensity(1.3);
    Fill->SetWorldRotation(FRotator(10,120,0));Fill->RegisterComponent();
    auto* RT=NewObject<UTextureRenderTarget2D>();RT->RenderTargetFormat=RTF_RGBA8;RT->InitAutoFormat(Width,Height);RT->UpdateResourceImmediate(true);
    auto* C=NewObject<USceneCaptureComponent2D>(A);A->AddInstanceComponent(C);C->RegisterComponent();C->TextureTarget=RT;
    C->bCaptureEveryFrame=false;C->bCaptureOnMovement=false;C->ProjectionType=ECameraProjectionMode::Orthographic;
    C->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;C->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    C->PostProcessSettings.bOverride_AutoExposureMinBrightness=true;C->PostProcessSettings.AutoExposureMinBrightness=1;
    C->PostProcessSettings.bOverride_AutoExposureMaxBrightness=true;C->PostProcessSettings.AutoExposureMaxBrightness=1;
    C->PostProcessSettings.bOverride_BloomIntensity=true;C->PostProcessSettings.BloomIntensity=.4;
    if(Closeup)
    {
        C->PostProcessSettings.AmbientCubemap=LoadObject<UTextureCube>(nullptr,TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"));
        C->PostProcessSettings.bOverride_AmbientCubemapIntensity=true;C->PostProcessSettings.AmbientCubemapIntensity=1;
    }
    FString Report;
    for(const TCHAR* Slot:{TEXT("ColdSteelPlayer_A"),TEXT("ColdSteelPlayer_B")})
        if(const auto* Saved=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(Slot,0)))
            for(const auto& Item:Saved->Profile.Items)if(Item.Definition==TEXT("ue_frost_crystal_sword"))
                Report+=FString::Printf(TEXT("Saved %s place=%d cell=%d selectedRune=%s data=%s\n"),Slot,Item.Place,Item.Cell,*ColdSteelMeleeRune::Selected(Item),*Item.Data);
    for(bool Skinned:{false,true})
    {
        UMeshComponent* M;
        if(Skinned)
        {
            auto* S=NewObject<USkeletalMeshComponent>(A);M=S;A->AddInstanceComponent(S);S->RegisterComponent();
            const FString Path=Guard.IsEmpty()?AssetRoot+TEXT("SK_FrostCrystalSword_Manny"):AssetRoot+Guard+TEXT("/SK_FrostCrystalSword_")+Guard;
            S->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,*Path));
            auto* Anim=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle"));
            S->PlayAnimation(Anim,false);S->SetPosition(.5,false);S->TickAnimation(0,false);S->RefreshBoneTransforms();
        }
        else
        {
            auto* S=NewObject<UStaticMeshComponent>(A);M=S;A->AddInstanceComponent(S);
            const FString Path=Guard.IsEmpty()?AssetRoot+TEXT("SM_FrostCrystalSword"):AssetRoot+Guard+TEXT("/SM_FrostCrystalSword_")+Guard;
            S->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,*Path));S->RegisterComponent();
        }
        M->SetCastShadow(false);C->ShowOnlyComponents.Reset();C->ShowOnlyComponent(M);
        FVector Origin=FVector::ZeroVector,Axis=FVector::UpVector,Side=FVector(0,-1,0);
        if(auto* S=Cast<USkeletalMeshComponent>(M))
        {
            const auto Base=S->GetSocketTransform(TEXT("Blade_Base"));const auto Tip=S->GetSocketTransform(TEXT("Blade_Tip"));
            Axis=(Tip.GetLocation()-Base.GetLocation()).GetSafeNormal();Origin=Base.GetLocation()-Axis*3;
            // View from the local blade face, preserving the sampled game animation.
            const auto Ref=S->GetSkeletalMeshAsset()->GetRefSkeleton();
            FTransform Rest=FTransform::Identity;int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));
            for(;I>=0;I=Ref.GetParentIndex(I))Rest=Rest*Ref.GetRefBonePose()[I];
            const FTransform Current=S->GetSocketTransform(TEXT("WPN_root"));
            // Canonical static +Z follows Blade_Base->Blade_Tip; orient camera by a stable perpendicular.
            Side=FVector::CrossProduct(Axis,FVector::RightVector).GetSafeNormal();
            if(Side.IsNearlyZero())Side=FVector::CrossProduct(Axis,FVector::UpVector).GetSafeNormal();
            Report+=FString::Printf(TEXT("Skinned Base=%s Tip=%s Root=%s\n"),*Base.ToString(),*Tip.ToString(),*Current.ToString());
        }
        const FVector Center=Origin+Axis*(Closeup?2:42);
        C->SetWorldLocation(Center+Side*180);C->SetWorldRotation(FRotationMatrix::MakeFromXZ(-Side,Axis).Rotator());C->OrthoWidth=Closeup?38:94;
        for(const FString Rune:{FString(),FString(TEXT("resonance_rune")),FString(TEXT("erosion_rune")),FString(TEXT("conduction_rune"))})
        {
            if(Closeup&&!Rune.IsEmpty())continue;
            ColdSteelMeleeRune::Apply(M,Rune);ColdSteelMeleeRune::UpdatePose(M,1.0);
            for(int32 Slot=0;Slot<M->GetNumMaterials();++Slot)
            {
                auto* Overlay=M->GetOverlayMaterial(true,Slot);auto* Base=M->GetMaterial(Slot);
                Report+=FString::Printf(TEXT("%d %s slot=%d base=%s overlay=%s\n"),Skinned,*Rune,Slot,*GetNameSafe(Base),*GetNameSafe(Overlay));
                if(auto* D=Cast<UMaterialInstanceDynamic>(Overlay))Report+=FString::Printf(TEXT("  Origin=%s Axis=%s Dimensions=%s\n"),*D->K2_GetVectorParameterValue(TEXT("BladeOrigin")).ToString(),*D->K2_GetVectorParameterValue(TEXT("BladeAxis")).ToString(),*D->K2_GetVectorParameterValue(TEXT("Dimensions")).ToString());
            }
            FAssetCompilingManager::Get().FinishAllCompilation();W->SendAllEndOfFrameUpdates();FlushRenderingCommands();
            for(int32 Frame=0;Frame<8;++Frame){C->CaptureScene();FlushRenderingCommands();}
            TArray<FColor> Pixels;RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);
            TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(Width,Height,Pixels,PNG);
            FFileHelper::SaveArrayToFile(PNG,*(Out/FString::Printf(TEXT("%s_%s.png"),Skinned?TEXT("skinned"):TEXT("static"),Rune.IsEmpty()?TEXT("original"):*Rune)));
            if(Closeup)
            {
                for(int32 Face=0;Face<2;++Face)
                {
                    const FVector Direction=(Side*(Face==0?1:-1)+Axis*.28+FVector::CrossProduct(Side,Axis)*.2).GetSafeNormal();
                    C->SetWorldLocation(Center+Direction*180);C->SetWorldRotation(FRotationMatrix::MakeFromXZ(-Direction,Axis).Rotator());
                    for(int32 Frame=0;Frame<8;++Frame){C->CaptureScene();FlushRenderingCommands();}
                    Pixels.Reset();RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);PNG.Reset();FImageUtils::PNGCompressImageArray(Width,Height,Pixels,PNG);
                    FFileHelper::SaveArrayToFile(PNG,*(Out/FString::Printf(TEXT("%s_guard_%s.png"),Skinned?TEXT("skinned"):TEXT("static"),Face==0?TEXT("oblique"):TEXT("back"))));
                }
            }
            if(Skinned&&!Closeup)
            {
                const auto Camera=C->GetComponentTransform();M->SetWorldRotation(FRotator(0,90,0));
                C->ProjectionType=ECameraProjectionMode::Perspective;C->FOVAngle=90;C->SetWorldLocation(FVector::ZeroVector);C->SetWorldRotation(FRotator::ZeroRotator);
                W->SendAllEndOfFrameUpdates();for(int32 Frame=0;Frame<8;++Frame){C->CaptureScene();FlushRenderingCommands();}
                Pixels.Reset();RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);PNG.Reset();FImageUtils::PNGCompressImageArray(900,1100,Pixels,PNG);
                FFileHelper::SaveArrayToFile(PNG,*(Out/FString::Printf(TEXT("firstperson_%s.png"),Rune.IsEmpty()?TEXT("original"):*Rune)));
                C->ProjectionType=ECameraProjectionMode::Orthographic;C->SetWorldTransform(Camera);M->SetWorldRotation(FRotator::ZeroRotator);
            }
        }
        M->DestroyComponent();
    }
    FFileHelper::SaveStringToFile(Report,*(Out/TEXT("report.txt")));UE_LOG(LogTemp,Display,TEXT("FROST_SURFACE_CAPTURE_COMPLETE %s"),*Out);
    W->DestroyWorld(false);return 0;
}
