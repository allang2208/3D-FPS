#include "FPSHelmetVisorWidget.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/DrawElements.h"

namespace
{
TAutoConsoleVariable<float> CVarHelmetInteriorBrightness(TEXT("fps.Helmet.InteriorBrightness"),.38f,
    TEXT("Helmet interior linear tint, 0..1. Does not dim the eye opening."),ECVF_Default);
TAutoConsoleVariable<float> CVarHelmetMotion(TEXT("fps.Helmet.Motion"),1.f,
    TEXT("Helmet interior response to the rendered camera feedback, 0..1."),ECVF_Default);
}

void UFPSHelmetVisorWidget::Configure(UFPSPlayerBodyComponent* Body,UObject* Surface)
{
    Source=Body;
    Camera=Body->GetOwner()->FindComponentByClass<UCameraComponent>();
    bMotionInitialized=false;
    Motion=MotionVelocity=FVector::ZeroVector;
    TurnVelocity=FVector2D::ZeroVector;
    bMaskParametersInitialized=false;
    if(auto* Material=Cast<UMaterialInterface>(Surface))
        Visor.SetResourceObject(UMaterialInstanceDynamic::Create(Material,this));
    else
        Visor.SetResourceObject(Surface);
    Visor.DrawAs=ESlateBrushDrawType::Image;
    if(const auto* Texture=Cast<UTexture2D>(Surface))
        Visor.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
    else
        Visor.ImageSize=FVector2D(1024,1024);
    SetVisibility(ESlateVisibility::HitTestInvisible);
    // The view mode can change without inventory changing. No per-frame asset
    // lookup, JSON parsing, or component creation is needed to paint this layer.
    ForceVolatile(true);
}

int32 UFPSHelmetVisorWidget::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
    const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,
    const FWidgetStyle& Style,bool Enabled) const
{
    const int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    const auto* PC=GetOwningPlayer();
    if(!Source.IsValid()||!PC||PC->GetPawn()!=Source->GetOwner()||
       PC->GetViewTarget()!=Source->GetOwner()||!Source->ShouldShowHelmetVisor())
    {bMotionInitialized=false;return Result;}

    const FVector2D Size=Geometry.GetLocalSize();
    if(Size.X<=0.||Size.Y<=0.)return Result;
    FVector2D Shift=FVector2D::ZeroVector;
    float Roll=0.f;
    if(const auto* Eye=Camera.Get();Eye&&PC->PlayerCameraManager)
    {
        // Read the final view after component bob/recoil, action-camera
        // additive offsets, body reactions and PlayerCameraManager shakes.
        // Separate camera feedback from aim; aim speed contributes only the
        // small inertial response below.
        const FMinimalViewInfo& View=PC->PlayerCameraManager->GetCameraCacheView();
        const FQuat Aim=PC->GetControlRotation().Quaternion();
        const FRotator Feedback=(Aim.Inverse()*View.Rotation.Quaternion()).Rotator();
        const FVector Relative=Eye->GetRelativeLocation();
        const double Now=GetWorld()->GetTimeSeconds();
        float MotionDelta=0.f;
        if(!bMotionInitialized||Now<LastMotionTime||Now-LastMotionTime>.2)
        {
            RestCameraLocation=Relative;
            PreviousAim=Aim;
            TurnVelocity=FVector2D::ZeroVector;
            Motion=MotionVelocity=FVector::ZeroVector;
            bMotionInitialized=true;
        }
        else if(Now>LastMotionTime)
        {
            MotionDelta=float(Now-LastMotionTime);
            const FRotator Turn=(PreviousAim.Inverse()*Aim).Rotator();
            TurnVelocity=FVector2D(Turn.Yaw,Turn.Pitch)/MotionDelta;
            PreviousAim=Aim;
            // Track slow posture changes, retaining the actual walking and
            // landing displacement without including the actor's world travel.
            RestCameraLocation=FMath::Lerp(RestCameraLocation,Relative,
                1.f-FMath::Exp(-3.f*MotionDelta));
        }
        LastMotionTime=Now;
        const auto* Parent=Eye->GetAttachParent();
        const FTransform Frame=Parent?Parent->GetComponentTransform():FTransform::Identity;
        const FVector Travel=Aim.UnrotateVector(
            Frame.TransformVectorNoScale(Relative-RestCameraLocation)+
            View.Location-Eye->GetComponentLocation());
        const float Strength=FMath::Clamp(CVarHelmetMotion.GetValueOnGameThread(),0.f,1.f);
        const FVector Target(
            FMath::Clamp(-Feedback.Yaw*.0015-Travel.Y*.0012-TurnVelocity.X*.00002,-.012,.012)*Strength,
            FMath::Clamp(Feedback.Pitch*.002+Travel.Z*.002+TurnVelocity.Y*.00002,-.02,.02)*Strength,
            FMath::DegreesToRadians(FMath::Clamp(-Feedback.Roll*.22,-.9,.9))*Strength);
        if(Strength<=0.f)Motion=MotionVelocity=FVector::ZeroVector;
        else if(MotionDelta>0.f)
        {
            // Closed-form critically damped response: short inertial follow
            // and a quiet return, advanced only once per world frame.
            constexpr float Frequency=2.f*UE_PI*7.f;
            const FVector Error=Motion-Target;
            const FVector Joint=MotionVelocity+Frequency*Error;
            const float Decay=FMath::Exp(-Frequency*MotionDelta);
            Motion=Target+(Error+Joint*MotionDelta)*Decay;
            MotionVelocity=(MotionVelocity-Frequency*Joint*MotionDelta)*Decay;
            Motion.X=FMath::Clamp(Motion.X,-.012,.012);
            Motion.Y=FMath::Clamp(Motion.Y,-.02,.02);
            Motion.Z=FMath::Clamp(Motion.Z,-FMath::DegreesToRadians(.9),FMath::DegreesToRadians(.9));
        }
        Shift=FVector2D(Motion.X*Size.X,Motion.Y*Size.Y);
        Roll=float(Motion.Z);
    }
    if(auto* Mask=Cast<UMaterialInstanceDynamic>(Visor.GetResourceObject()))
    {
        // The procedural frame fills the viewport. Its opacity evaluates the
        // shifted opening directly, including the feathered edge and corners.
        const float Aspect=float(Size.X/Size.Y);
        if(!bMaskParametersInitialized||!LastMaskMotion.Equals(Motion,.000001))
        {
            Mask->SetVectorParameterValue(TEXT("HelmetMotion"),FLinearColor(Motion.X,Motion.Y,Motion.Z,0));
            LastMaskMotion=Motion;
        }
        if(!bMaskParametersInitialized||!FMath::IsNearlyEqual(Aspect,LastMaskAspect))
        {
            Mask->SetScalarParameterValue(TEXT("HelmetAspect"),Aspect);
            LastMaskAspect=Aspect;
        }
        bMaskParametersInitialized=true;
        FSlateDrawElement::MakeBox(Elements,Result+1,
            Geometry.ToPaintGeometry(Size,FSlateLayoutTransform()),
            &Visor,ESlateDrawEffect::None,FLinearColor::White);
        return Result+1;
    }
    // Extend the clamped border texels beyond the viewport. UV and geometry
    // grow together, so the approved eye opening keeps its original size.
    const float BorderExtension=.04f+.5f*FMath::Sin(FMath::DegreesToRadians(.9f))*
        float(FMath::Max(Size.X/Size.Y,Size.Y/Size.X));
    FSlateBrush DrawVisor=Visor;
    DrawVisor.SetUVRegion(FBox2f(FVector2f(-BorderExtension,-BorderExtension),FVector2f(1+BorderExtension,1+BorderExtension)));
    const FVector2D DrawSize=Size*(1+2*BorderExtension);
    const FVector2D Origin=-Size*BorderExtension+Shift;
    const float Brightness=FMath::Clamp(CVarHelmetInteriorBrightness.GetValueOnGameThread(),0.f,1.f);
    FSlateDrawElement::MakeBox(Elements,Result+1,
        Geometry.ToPaintGeometry(DrawSize,FSlateLayoutTransform(Origin),
            FSlateRenderTransform(FQuat2D(Roll)),FVector2D(.5,.5)),
        &DrawVisor,ESlateDrawEffect::None,FLinearColor(Brightness,Brightness,Brightness,1.f));
    return Result+1;
}
