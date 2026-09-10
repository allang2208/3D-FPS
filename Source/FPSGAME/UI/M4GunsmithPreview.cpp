#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/TextureCube.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Framework/Application/SlateApplication.h"

void UM4GunsmithWidget::InitializePreview()
{
    if(Capture||!GetOwningPlayerPawn())return;
    PreviewTarget=NewObject<UTextureRenderTarget2D>(this);
    PreviewTarget->RenderTargetFormat=RTF_RGBA16f;PreviewTarget->ClearColor=FLinearColor(0,0,0,1);
    PreviewTarget->InitAutoFormat(1200,800);PreviewTarget->UpdateResourceImmediate(true);
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/M_WeaponPreview.M_WeaponPreview"));
    if(!Material)return;
    PreviewMaterial=UMaterialInstanceDynamic::Create(Material,this);PreviewMaterial->SetTextureParameterValue(TEXT("PreviewTexture"),PreviewTarget);
    PreviewBrush.SetResourceObject(PreviewMaterial);PreviewBrush.ImageSize=FVector2D(1200,800);PreviewBrush.DrawAs=ESlateBrushDrawType::Image;
    Studio=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(false).SetLightBrightness(6.f).SetSkyBrightness(1.f));
    Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment")));
    StudioFill=NewObject<UDirectionalLightComponent>(GetTransientPackage(),NAME_None,RF_Transient);
    StudioFill->SetIntensity(3.f);StudioFill->SetLightColor(FLinearColor(.82f,.91f,1.f));StudioFill->SetCastShadows(false);
    Studio->AddComponent(StudioFill,FTransform(FRotator(-15,150,0)));
    Studio->UpdateCaptureContents();
    Capture=NewObject<USceneCaptureComponent2D>(GetTransientPackage(),NAME_None,RF_Transient);
    Capture->TextureTarget=PreviewTarget;Capture->CaptureSource=SCS_SceneColorHDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetBloom(false);
    Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Studio->AddComponent(Capture,FTransform::Identity);
}
void UM4GunsmithWidget::SyncStudioPreview()
{
    // Copy only presentation geometry. Original mesh assets, materials, pose and section visibility remain authoritative.
    const auto Sources=Capture->ShowOnlyComponents;Capture->ShowOnlyComponents.Reset();
    const FTransform ViewTransform=Capture->GetComponentTransform();
    FQuat AssemblyRotation=FQuat::Identity;FVector Pivot=FVector::ZeroVector,Target=FVector::ZeroVector;
    if(!bAimPreview)
        for(const auto& Weak:Sources)
            if(auto* Rifle=Cast<USkeletalMeshComponent>(Weak.Get());Rifle&&Rifle->DoesSocketExist(TEXT("WPN_SOCKET_Muzzle")))
            {
                Pivot=Rifle->GetSocketLocation(TEXT("WPN_SOCKET_Magazine"));
                const FVector Barrel=Rifle->GetSocketQuaternion(TEXT("WPN_SOCKET_Muzzle")).GetAxisY();
                const FQuat Align=FQuat::FindBetweenNormals(Barrel.GetSafeNormal(),-ViewTransform.GetRotation().GetRightVector());
                const FQuat LayFlat(ViewTransform.GetRotation().GetRightVector(),FMath::DegreesToRadians(-45.f+PreviewOrbit.Y));
                const FQuat Turn(ViewTransform.GetRotation().GetUpVector(),FMath::DegreesToRadians(PreviewOrbit.X));
                AssemblyRotation=Turn*LayFlat*Align;
                Target=ViewTransform.TransformPosition(FVector(75.f,0.f,0.f));break;
            }
    for(auto& Pair:StudioCopies)if(Pair.Value)Pair.Value->SetVisibility(false);
    for(const auto& Weak:Sources)
    {
        auto* Source=Cast<UMeshComponent>(Weak.Get());if(!Source||!Source->IsVisible())continue;
        auto*& Copy=StudioCopies.FindOrAdd(Source);
        if(!Copy)
        {
            if(auto* Skinned=Cast<USkeletalMeshComponent>(Source))
            {
                auto* NewMesh=NewObject<USkeletalMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
                NewMesh->SetSkeletalMeshAsset(Skinned->GetSkeletalMeshAsset());NewMesh->SetLeaderPoseComponent(Skinned);Copy=NewMesh;
            }
            else if(auto* Static=Cast<UStaticMeshComponent>(Source))
            {
                auto* NewMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
                NewMesh->SetStaticMesh(Static->GetStaticMesh());Copy=NewMesh;
            }
            if(!Copy)continue;
            Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);Copy->SetCastShadow(false);
            Studio->AddComponent(Copy,Source->GetComponentTransform());
        }
        if(auto* SourceStatic=Cast<UStaticMeshComponent>(Source))
            if(auto* CopyStatic=Cast<UStaticMeshComponent>(Copy);CopyStatic&&CopyStatic->GetStaticMesh()!=SourceStatic->GetStaticMesh())CopyStatic->SetStaticMesh(SourceStatic->GetStaticMesh());
        if(auto* SourceSkinned=Cast<USkeletalMeshComponent>(Source))
            if(auto* CopySkinned=Cast<USkeletalMeshComponent>(Copy);CopySkinned&&CopySkinned->GetSkeletalMeshAsset()!=SourceSkinned->GetSkeletalMeshAsset())
            {CopySkinned->SetSkeletalMeshAsset(SourceSkinned->GetSkeletalMeshAsset());CopySkinned->SetLeaderPoseComponent(SourceSkinned);}
        FTransform Pose=Source->GetComponentTransform();
        if(!bAimPreview){Pose.SetLocation(Target+AssemblyRotation.RotateVector(Pose.GetLocation()-Pivot));Pose.SetRotation(AssemblyRotation*Pose.GetRotation());}
        Copy->SetWorldTransform(Pose);Copy->SetVisibility(true);
        for(int32 M=0;M<Source->GetNumMaterials();++M)Copy->SetMaterial(M,Source->GetMaterial(M));
        if(auto* Skinned=Cast<USkeletalMeshComponent>(Source))
            if(const auto* Asset=Skinned->GetSkeletalMeshAsset())if(const auto* Render=Asset->GetResourceForRendering())
                for(int32 L=0;L<Render->LODRenderData.Num();++L)
                    for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
                    {
                        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                        Cast<USkeletalMeshComponent>(Copy)->ShowMaterialSection(M,S,Skinned->IsMaterialSectionShown(M,L),L);
                    }
        Capture->ShowOnlyComponent(Copy);
    }
    const FQuat View=Capture->GetComponentQuat();
    Studio->DirectionalLight->SetWorldRotation(View*FRotator(-40,-55,0).Quaternion());
    StudioFill->SetWorldRotation(View*FRotator(-15,150,0).Quaternion());
}
void UM4GunsmithWidget::RotatePreview(FVector2D Delta)
{
    if(bAimPreview||!bSidePreview)SetSidePreview(true);
    PreviewOrbit.X=FMath::UnwindDegrees(PreviewOrbit.X+float(Delta.X)*.35f);
    PreviewOrbit.Y=FMath::Clamp(PreviewOrbit.Y-float(Delta.Y)*.35f,-85.f,85.f);
    PreviewMotion=1.f;CaptureAccumulator=1.f;
}
void UM4GunsmithWidget::ReleasePreview()
{
    if(PreviewSurface&&PreviewSurface->HasMouseCapture()&&FSlateApplication::IsInitialized())FSlateApplication::Get().ReleaseMouseCapture();
    PreviewSurface.Reset();
    if(Capture){Capture->TextureTarget=nullptr;Studio->RemoveComponent(Capture);Capture->DestroyComponent();Capture=nullptr;}
    StudioCopies.Reset();StudioFill=nullptr;Studio.Reset();
    PreviewBrush.SetResourceObject(nullptr);PreviewMaterial=nullptr;PreviewTarget=nullptr;
}
void UM4GunsmithWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);CaptureAccumulator+=Delta;PreviewMotion=FMath::Max(0.f,PreviewMotion-Delta);
    if(!Capture||CaptureAccumulator<(PreviewMotion>0?1.f/30.f:1.f))return;
    CaptureAccumulator=0;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!P->Equipped()||P->Equipped()->InstanceId!=Model()->Instance())return;
    if(auto* C=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn()))
    {C->UpdateGunsmithCapture(Capture,bAimPreview);SyncStudioPreview();Capture->CaptureScene();}
}
