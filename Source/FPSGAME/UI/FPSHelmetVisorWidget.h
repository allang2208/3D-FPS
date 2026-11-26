#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "FPSHelmetVisorWidget.generated.h"

/** Owner-local optical obstruction, below HUD panels and above scope imagery. */
UCLASS()
class FPSGAME_API UFPSHelmetVisorWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(class UFPSPlayerBodyComponent* Body, UObject* Surface);
protected:
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,
        FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
private:
    TWeakObjectPtr<class UFPSPlayerBodyComponent> Source;
    TWeakObjectPtr<class UCameraComponent> Camera;
    UPROPERTY(Transient) FSlateBrush Visor;
    mutable FVector RestCameraLocation=FVector::ZeroVector;
    mutable double LastMotionTime=0.;
    mutable bool bMotionInitialized=false;
    mutable FQuat PreviousAim=FQuat::Identity;
    mutable FVector2D TurnVelocity=FVector2D::ZeroVector;
    mutable FVector Motion=FVector::ZeroVector;
    mutable FVector MotionVelocity=FVector::ZeroVector;
    mutable FVector LastMaskMotion=FVector::ZeroVector;
    mutable float LastMaskAspect=0.f;
    mutable bool bMaskParametersInitialized=false;
};
