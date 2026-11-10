#include "RuneSwordComponent.h"
#include "FPSImpactFXSubsystem.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/ChainSlashAssets.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"

namespace
{
constexpr float WaveDuration=.16f;
const FRotator ReferenceCamera[]={
#include "ChainSlashCameraKeys.inl"
};
constexpr float Side[]={-1.f,1.f,-1.f,1.f};
}

void URuneSwordComponent::ApplyChainImpact(int32 Cut)
{
    if(!bChainSlash||!ChainSlashContacts.IsValidIndex(Cut)||(ChainImpactMask&(1u<<Cut)))return;
    ChainImpactMask|=uint8(1u<<Cut);
    ChainLastImpact=Cut;
    ChainImpactAt=GetWorld()->GetTimeSeconds();
    SweepHitPause=Cut==3?.070f:.050f;
    if(Character.IsValid()&&Character->IsLocallyControlled()&&HitSound)
        UGameplayStatics::PlaySound2D(this,HitSound,Cut==3?.87f:.73f,Cut==3?.91f:1.f);
}

void URuneSwordComponent::ClientChainImpact_Implementation(uint32 Serial,int32 Cut)
{
    if(Serial!=ChainSlashSerial||!ChainSlashContacts.IsValidIndex(Cut))return;
    // A delayed receipt must not stop another stroke or a subsequent cast.
    if(Elapsed>ChainSlashContacts[Cut]+.20f)return;
    ApplyChainImpact(Cut);
}

void URuneSwordComponent::ChainSlashCamera(FVector& Location,FRotator& Rotation) const
{
    const float Key=FMath::Clamp(Elapsed*60.f,0.f,float(UE_ARRAY_COUNT(ReferenceCamera)-1));
    const int32 I=FMath::FloorToInt(Key),J=FMath::Min(I+1,int32(UE_ARRAY_COUNT(ReferenceCamera))-1);
    Rotation=FMath::Lerp(ReferenceCamera[I],ReferenceCamera[J],Key-I);
    Rotation.Pitch*=2.8f;
    Rotation.Yaw*=3.5f;
    Rotation.Roll*=4.5f;
    for(int32 Cut=0;Cut<ChainSlashContacts.Num();++Cut)
    {
        const float Phase=(Elapsed-ChainSlashContacts[Cut]+.15f)/.36f;
        if(Phase<=0.f||Phase>=1.f)continue;
        const float Envelope=FMath::Sin(PI*Phase);
        const float Sway=FMath::Sin(2.f*PI*Phase)*Envelope;
        const float Downstroke=Cut==0?1.25f:1.f;
        Rotation+=FRotator(-1.5f*Downstroke*Envelope*Envelope,Side[Cut]*2.3f*Sway,Side[Cut]*3.2f*Sway);
        Location+=FVector(-.8f*Envelope*Envelope,Side[Cut]*1.8f*Sway,-.7f*Envelope*Envelope);
    }
    if(ChainLastImpact==INDEX_NONE)return;
    const float Age=GetWorld()->GetTimeSeconds()-ChainImpactAt;
    if(Age>=WaveDuration)return;
    const float Strength=ChainLastImpact==3?1.4f:(ChainLastImpact==0?1.25f:1.f);
    const float Tail=1.f-FMath::SmoothStep(.070f,WaveDuration,Age);
    const float Kick=Strength*FMath::Exp(-23.f*Age)*FMath::Cos(53.f*Age)*Tail;
    const float Direction=Side[ChainLastImpact];
    Rotation+=FRotator(1.45f,Direction*.82f,-Direction*1.58f)*Kick;
    Location+=FVector(-2.8f,Direction*.6f,.5f)*Kick;
}

void URuneSwordComponent::PresentChainRibbon()
{
    if(!RiftVisual||!RiftMaterial||!Viewmodel)return;
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(Body&&Body->IsThirdPersonViewEnabled())
    {
        if(bRiftActive)StopRift();
        ChainRibbonCut=INDEX_NONE;
        return;
    }
    constexpr float Dissolve=.115f;
    for(int32 Cut=ChainSlashContacts.Num()-1;Cut>=0;--Cut)
    {
        const float SinceMark=Elapsed-ChainSlashContacts[Cut];
        if(SinceMark < -ChainSlash::RibbonLead || SinceMark>=ChainSlash::RibbonTail+Dissolve)continue;
        if(ChainRibbonCut!=Cut)
        {
            auto* Mesh=Cast<UStaticMesh>(FSoftObjectPath(ChainSlash::CutRibbons[Cut]).ResolveObject());
            if(!Mesh)return;
            RiftVisual->SetStaticMesh(Mesh);
            RiftVisual->SetMaterial(0,RiftMaterial);
            RiftVisual->AttachToComponent(Viewmodel,FAttachmentTransformRules::SnapToTargetIncludingScale);
            RiftVisual->SetVisibility(true);
            ChainRibbonCut=Cut;bRiftActive=true;
        }
        const float Reveal=FMath::Clamp((SinceMark+ChainSlash::RibbonLead)/(ChainSlash::RibbonLead+ChainSlash::RibbonTail),0.f,1.f);
        const float FadeTime=FMath::Max(0.f,SinceMark-ChainSlash::RibbonTail);
        if(FadeTime>0.f)
        {
            if(RiftVisual->GetAttachParent())
            {
                RiftOrigin=RiftVisual->GetComponentTransform();
                RiftDirection=Camera->GetForwardVector();
                RiftVisual->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
            }
            RiftVisual->SetWorldLocation(RiftOrigin.GetLocation()+RiftDirection*(FadeTime*28.f));
        }
        const float Contact=Cut==ChainLastImpact ? FMath::Clamp(1.f-float(GetWorld()->GetTimeSeconds()-ChainImpactAt)/.10f,0.f,1.f):0.f;
        RiftMaterial->SetScalarParameterValue(TEXT("RiftStrength"),(Cut==3?.105f:.085f)+.060f*Contact);
        RiftMaterial->SetScalarParameterValue(TEXT("SweepProgress"),Reveal*1.06f);
        RiftMaterial->SetScalarParameterValue(TEXT("RiftFade"),1.f-FMath::SmoothStep(0.f,Dissolve,FadeTime));
        return;
    }
    if(bRiftActive)StopRift();
    ChainRibbonCut=INDEX_NONE;
}

void URuneSwordComponent::MulticastChainContact_Implementation(AActor* Target,FVector_NetQuantize10 Point,
    FVector_NetQuantizeNormal Normal,bool bPulse,bool bFinalCut)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* World=GetWorld();
    auto* PC=World->GetFirstPlayerController();
    auto* Viewer=PC?PC->GetViewTarget():nullptr;
    auto* Eye=Viewer?Viewer->FindComponentByClass<UCameraComponent>():nullptr;
    if(!Eye)return;
    const FVector Out=FVector(Normal).GetSafeNormal(UE_SMALL_NUMBER,(Eye->GetComponentLocation()-Point).GetSafeNormal());
    if(IsValid(Target))
    {
        FHitResult Hit(Target,Cast<UPrimitiveComponent>(Target->GetRootComponent()),Point,Out);
        Hit.ImpactPoint=Hit.Location=Point;Hit.ImpactNormal=Hit.Normal=Out;
        Hit.TraceStart=Character.IsValid()?Character->GetMeleeAimTransform().GetLocation():FVector(Point)+Out;
        Hit.TraceEnd=Point;
        if(auto* FX=World->GetSubsystem<UFPSImpactFXSubsystem>())FX->SpawnBladeContact(Hit,Eye,false);
    }
    if(!bPulse)return;
    if(!ChainImpactWave)
    {
        auto* Mesh=Cast<UStaticMesh>(FSoftObjectPath(ChainSlash::ImpactWave).ResolveObject());
        if(!Mesh||!Mesh->GetMaterial(0))return;
        auto* Owner=GetOwner();
        ChainImpactWave=NewObject<UStaticMeshComponent>(Owner);
        Owner->AddInstanceComponent(ChainImpactWave);
        ChainImpactWave->SetMobility(EComponentMobility::Movable);
        ChainImpactWave->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        ChainImpactWave->SetCanEverAffectNavigation(false);
        ChainImpactWave->SetCastShadow(false);
        ChainImpactWave->bReceivesDecals=false;
        ChainImpactWave->SetStaticMesh(Mesh);
        ChainWaveMaterial=ChainImpactWave->CreateDynamicMaterialInstance(0);
        ChainImpactWave->RegisterComponent();
    }
    if(!ChainWaveMaterial)return;
    ChainWaveAt=World->GetTimeSeconds();
    ChainWaveScale=bFinalCut?1.30f:1.f;
    ChainImpactWave->SetWorldLocationAndRotation(FVector(Point)+Out*2.f,Out.Rotation());
    ChainWaveMaterial->SetScalarParameterValue(TEXT("SweepProgress"),1.06f);
    ChainWaveMaterial->SetScalarParameterValue(TEXT("RiftStrength"),bFinalCut?.21f:.16f);
    TickChainWave();
    ChainImpactWave->SetVisibility(true);
}

void URuneSwordComponent::TickChainWave()
{
    const float U=FMath::Clamp(float(GetWorld()->GetTimeSeconds()-ChainWaveAt)/WaveDuration,0.f,1.f);
    if(U>=1.f)
    {
        ChainImpactWave->SetVisibility(false);
        ChainWaveAt=-1.;
        return;
    }
    const float Expand=1.f-FMath::Square(1.f-U);
    ChainImpactWave->SetWorldScale3D(FVector(ChainWaveScale*(.22f+.78f*Expand)));
    ChainWaveMaterial->SetScalarParameterValue(TEXT("RiftFade"),1.f-FMath::SmoothStep(.05f,1.f,U));
}
