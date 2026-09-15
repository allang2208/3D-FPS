#include "M4GunsmithWidget.h"
#include "ColdSteelMeleePreview.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/TextureRenderTarget2D.h"

void UM4GunsmithWidget::SetStandaloneMeleeItem(const FColdSteelItem& Item)
{
    const FString Path=ColdSteelMeleePreview::MeshPath(Item),Key=Item.InstanceId+TEXT("|")+Path;
    if(StandaloneMelee&&StandaloneKey==Key)return;
    CloseStandalonePreview();
    auto* Asset=Path.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Asset)return;
    InitializePreview();if(!Capture)return;
    StandaloneMelee=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
    StandaloneMelee->SetStaticMesh(Asset);StandaloneMelee->SetForcedLodModel(1);
    StandaloneMelee->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Studio->AddComponent(StandaloneMelee,FTransform::Identity);
    StandaloneKey=Key;bPreviewStreamingDirty=true;SetSidePreview(true);
}

void UM4GunsmithWidget::SyncStandaloneMeleePreview()
{
    if(!Capture||!StandaloneMelee||!StandaloneMelee->GetStaticMesh())return;
    const auto& Asset=*StandaloneMelee->GetStaticMesh();
    const FQuat Base=ColdSteelMeleePreview::Rotation(Asset);
    const FQuat Turn(FVector::UpVector,FMath::DegreesToRadians(PreviewOrbit.X));
    const FQuat Tilt(FVector::RightVector,FMath::DegreesToRadians(PreviewOrbit.Y));
    StandaloneMelee->SetWorldTransform(ColdSteelMeleePreview::Pose(Asset,Turn*Tilt*Base));
    Capture->ShowOnlyComponents.Reset();Capture->ShowOnlyComponent(StandaloneMelee);
    Capture->SetWorldTransform(FTransform::Identity);Capture->ProjectionType=ECameraProjectionMode::Orthographic;
    const float Aspect=float(PreviewTarget->SizeX)/FMath::Max(1,PreviewTarget->SizeY);
    // Keep the viewing scale steady while orbiting the blade.
    const FVector Size=Asset.GetBoundingBox().TransformBy(FTransform(Base)).GetSize();
    Capture->OrthoWidth=FMath::Max(30.f,FMath::Max(float(Size.Y)/.84f,float(Size.Z)*Aspect/.60f))/PreviewZoom;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    const float Far=FMath::Max(2000.f,float(Size.Size())+600.f);
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/Far,-.1f);
    Studio->DirectionalLight->SetWorldRotation(FRotator(-40,-55,0));
    StudioFill->SetWorldRotation(FRotator(-15,150,0));
}
