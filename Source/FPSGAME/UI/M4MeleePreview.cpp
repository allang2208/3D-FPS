#include "M4GunsmithWidget.h"
#include "ColdSteelMeleePreview.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Engine/GameInstance.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/TextureRenderTarget2D.h"

void UM4GunsmithWidget::SetStandaloneMeleeItem(const FColdSteelItem& Item)
{
    const bool Draft=Model()->IsOpen()&&Model()->Instance()==Item.InstanceId;
    if(ColdSteelModularSword::Supports(Item))
    {
        const FString Key=Item.InstanceId+TEXT("|")+ColdSteelModularSword::Key(Item,Draft?&Model()->Draft():nullptr);
        const bool Created=!StandaloneMelee||!StandaloneKey.StartsWith(Item.InstanceId+TEXT("|"));
        if(Created)
        {
            CloseStandalonePreview();InitializePreview();if(!Capture)return;
            StandaloneMelee=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
            StandaloneMelee->SetCollisionEnabled(ECollisionEnabled::NoCollision);StandaloneMelee->SetForcedLodModel(1);
            Studio->AddComponent(StandaloneMelee,FTransform::Identity);
        }
        if(!ColdSteelModularSword::Apply(StandaloneMelee,Item,Draft?&Model()->Draft():nullptr))return;
        if(StandaloneKey!=Key){StandaloneKey=Key;bPreviewStreamingDirty=true;PreviewMotion=1.f;}
        if(Created)SetSidePreview(true);
        return;
    }
    const FString Path=ColdSteelMeleeGuard::WorldMesh(Item,Draft?&Model()->Draft():nullptr),Key=Item.InstanceId+TEXT("|")+Path;
    const FString Rune=Model()->IsOpen()&&Model()->Instance()==Item.InstanceId?Model()->Draft().FindRef(TEXT("blade_2")):ColdSteelMeleeRune::Selected(Item);
    if(StandaloneMelee&&StandaloneKey.StartsWith(Item.InstanceId+TEXT("|")))
    {
        if(StandaloneKey!=Key)
        {
            auto* Replacement=LoadObject<UStaticMesh>(nullptr,*Path);if(!Replacement)return;
            StandaloneMelee->EmptyOverrideMaterials();StandaloneMelee->SetStaticMesh(Replacement);
            StandaloneKey=Key;bPreviewStreamingDirty=true;PreviewMotion=1.f;
        }
        ColdSteelMeleeRune::Apply(StandaloneMelee,Rune);return;
    }
    CloseStandalonePreview();
    auto* Asset=Path.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Asset)return;
    InitializePreview();if(!Capture)return;
    StandaloneMelee=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
    StandaloneMelee->SetStaticMesh(Asset);StandaloneMelee->SetForcedLodModel(1);
    ColdSteelMeleeRune::Apply(StandaloneMelee,Rune);
    StandaloneMelee->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Studio->AddComponent(StandaloneMelee,FTransform::Identity);
    StandaloneKey=Key;bPreviewStreamingDirty=true;SetSidePreview(true);
}

void UM4GunsmithWidget::SyncStandaloneMeleePreview()
{
    if(!Capture||!StandaloneMelee||!StandaloneMelee->GetStaticMesh())return;
    const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Model()->Instance());
    if(Item&&Model()->IsOpen()&&StandaloneKey.StartsWith(Item->InstanceId+TEXT("|")))SetStandaloneMeleeItem(*Item);
    const FBox Bounds=ColdSteelModularSword::LocalBounds(StandaloneMelee);
    const FQuat Base=ColdSteelMeleePreview::Rotation(Bounds);
    const FQuat Turn(FVector::UpVector,FMath::DegreesToRadians(PreviewOrbit.X));
    const FQuat Tilt(FVector::RightVector,FMath::DegreesToRadians(PreviewOrbit.Y));
    StandaloneMelee->SetWorldTransform(ColdSteelMeleePreview::Pose(Bounds,Turn*Tilt*Base));
    if(ColdSteelMeleeRune::UpdatePose(StandaloneMelee,FMath::Fmod(FPlatformTime::Seconds(),3600.)))PreviewMotion=FMath::Max(PreviewMotion,.25f);
    Capture->ShowOnlyComponents.Reset();for(auto* Part:ColdSteelModularSword::Components(StandaloneMelee))Capture->ShowOnlyComponent(Part);
    Capture->SetWorldTransform(FTransform::Identity);Capture->ProjectionType=ECameraProjectionMode::Orthographic;
    const float Aspect=float(PreviewTarget->SizeX)/FMath::Max(1,PreviewTarget->SizeY);
    // Keep the viewing scale steady while orbiting the blade.
    const FVector Size=Bounds.TransformBy(FTransform(Base)).GetSize();
    Capture->OrthoWidth=FMath::Max(30.f,FMath::Max(float(Size.Y)/.84f,float(Size.Z)*Aspect/.60f))/PreviewZoom;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    const float Far=FMath::Max(2000.f,float(Size.Size())+600.f);
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/Far,-.1f);
    Studio->DirectionalLight->SetWorldRotation(FRotator(-40,-55,0));
    StudioFill->SetWorldRotation(FRotator(-15,150,0));
}
