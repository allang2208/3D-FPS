#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriDashRhythm.h"
#include "KukriSkillRiftRibbons.h"
#include "../RuneSwordWhirlwindFeel.h"
#include "../../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

// Skill rifts (2026-10-24, user: the combo's space distortion on the whirlwind and the sprint attack too).  Same material
// and life cycle as the combo rift (KukriRift.cpp: M_RuneRift, SweepProgress reveal, real-time dissolve), on a separate
// owner-only dynamic mesh so the combo / uppercut / heavy rifts keep their own state.
//  * Sprint attack: the chop's crescent (KukriSkillRiftRibbons::Dash, baked from the clip like the combo's), frozen at
//    the viewmodel when the blade comes over the top, revealed on the dash clock, carried along with the dash momentum
//    while it unfolds, then dissolved while it drifts forward.
//  * Whirlwind: the held blade sweeps a ring around the player (the camera turns about the vertical axis, the viewmodel
//    with it).  At the start of the spin the band between the inner and outer blade points is swept KukriWhirlRingDegrees
//    about the vertical axis through the camera; U runs along the turn, so SweepProgress follows the turned angle and the
//    ring closes behind the blade during the first turn, glows harder through the second, then widens and dissolves.

namespace
{
/** Whirlwind ring: angular extent (a little over one turn so the feathered ends overlap), stations, band along the blade. */
constexpr float KukriWhirlRingDegrees=380.f;
constexpr int32 KukriWhirlRingStations=96;
constexpr float KukriWhirlRingInner=.40f, KukriWhirlRingOuter=1.35f;     // along the grip->tip vector, as the crescents
/** RiftStrength over the first / second turn, the dissolve (real s) and the radial widening while it dissolves. */
constexpr float KukriWhirlRingStrength=.085f, KukriWhirlRingSecondStrength=.11f, KukriWhirlRingDissolve=.32f, KukriWhirlRingSpread=.14f;

UE::Geometry::FDynamicMesh3 KukriRibbonMesh(int32 Stations,TFunctionRef<void(int32,FVector&,FVector&)> Station)
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
    FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 S=0;S<Stations;++S)
    {
        FVector Inner,Outer;Station(S,Inner,Outer);
        for(int32 E=0;E<2;++E)
        {
            Mesh.AppendVertex(FVector3d(E?Outer:Inner));
            UV->AppendElement(FVector2f(float(S)/(Stations-1),float(E)));
            Normals->AppendElement(FVector3f(0.f,0.f,1.f));   // unlit two-sided material: the normal is unused
        }
    }
    for(int32 S=0;S<Stations-1;++S)
    {
        const int32 A=S*2;
        for(const FIndex3i T:{FIndex3i(A,A+2,A+1),FIndex3i(A+1,A+2,A+3)})
        {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
    }
    return Mesh;
}
}

bool UKukriWeaponComponent::PrepareSkillRift()
{
    auto* P=Pawn();
    if(!P||!Viewmodel||!Camera)return false;
    if(!SkillRiftVisual)
    {
        auto* Material=LoadObject<UMaterialInterface>(nullptr,KukriRhythm::RiftMaterial);
        if(!Material)return false;
        SkillRiftVisual=NewObject<UDynamicMeshComponent>(P,TEXT("KukriSkillRift"));
        P->AddInstanceComponent(SkillRiftVisual);
        SkillRiftVisual->SetMobility(EComponentMobility::Movable);
        SkillRiftVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);SkillRiftVisual->SetGenerateOverlapEvents(false);
        SkillRiftVisual->SetCanEverAffectNavigation(false);SkillRiftVisual->SetCastShadow(false);SkillRiftVisual->SetReceivesDecals(false);
        SkillRiftVisual->SetOnlyOwnerSee(true);SkillRiftVisual->bVisibleInRayTracing=false;SkillRiftVisual->bAffectDistanceFieldLighting=false;
        SkillRiftVisual->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        SkillRiftVisual->RegisterComponent();
        SkillRiftMID=UMaterialInstanceDynamic::Create(Material,this);
        SkillRiftVisual->SetMaterial(0,SkillRiftMID);
    }
    return SkillRiftMID!=nullptr;
}

void UKukriWeaponComponent::StartDashRift()
{
    auto* P=Pawn();
    if(!PrepareSkillRift())return;
    if(SkillRiftMesh!=EKukriSkillRift::Dash)
    {
        SkillRiftVisual->SetMesh(KukriRibbonMesh(KukriSkillRiftRibbons::Stations,[](int32 S,FVector& Inner,FVector& Outer)
        {
            const float* A=KukriSkillRiftRibbons::Dash[S][0];const float* B=KukriSkillRiftRibbons::Dash[S][1];
            Inner=FVector(A[0],A[1],A[2]);Outer=FVector(B[0],B[1],B[2]);
        }));
        SkillRiftVisual->SetMaterial(0,SkillRiftMID);SkillRiftMesh=EKukriSkillRift::Dash;
    }
    // Freeze the authored crescent where the viewmodel is now; it rides with the dash momentum while it unfolds.
    SkillRiftOrigin=Viewmodel->GetComponentTransform();SkillRiftDirection=Camera->GetForwardVector();
    SkillRiftPawnLocation=P->GetActorLocation();
    SkillRift=EKukriSkillRift::Dash;SkillRiftAge=0.f;SkillRiftFadeAge=-1.f;
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),KukriDashRhythm::RiftStrength);
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    SkillRiftVisual->SetWorldTransform(SkillRiftOrigin);
    SkillRiftVisual->SetVisibility(true);
}

void UKukriWeaponComponent::StartWhirlwindRift()
{
    if(!PrepareSkillRift())return;
    // The held blade now (the spin starts on the authored hold): its band, swept about the vertical through the camera.
    const FTransform Knife=BladeFrame();
    const FVector Center=Camera->GetComponentLocation();
    const FVector Inner=Knife.TransformPosition(KukriRhythm::BladeTip*KukriWhirlRingInner)-Center;
    const FVector Outer=Knife.TransformPosition(KukriRhythm::BladeTip*KukriWhirlRingOuter)-Center;
    const float Direction=WhirlwindTuning.TurnDegrees<0.f?-1.f:1.f;
    SkillRiftVisual->SetMesh(KukriRibbonMesh(KukriWhirlRingStations,[&](int32 S,FVector& In,FVector& Out)
    {
        const FRotator Turn(0.f,Direction*KukriWhirlRingDegrees*S/(KukriWhirlRingStations-1),0.f);
        In=Turn.RotateVector(Inner);Out=Turn.RotateVector(Outer);
    }));
    SkillRiftVisual->SetMaterial(0,SkillRiftMID);SkillRiftMesh=EKukriSkillRift::Whirlwind;
    SkillRiftOrigin=FTransform(Center);SkillRiftDirection=FVector::ZeroVector;
    SkillRift=EKukriSkillRift::Whirlwind;SkillRiftAge=0.f;SkillRiftFadeAge=-1.f;
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),KukriWhirlRingStrength);
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    SkillRiftVisual->SetWorldTransform(SkillRiftOrigin);
    SkillRiftVisual->SetVisibility(true);
}

void UKukriWeaponComponent::TickSkillRift(float Delta)
{
    if(SkillRift==EKukriSkillRift::None||!SkillRiftVisual||!SkillRiftMID)return;
    SkillRiftAge+=Delta;
    float Reveal=1.f,Dissolve=KukriDashRhythm::RiftDissolve;
    if(SkillRift==EKukriSkillRift::Dash)
    {
        // Reveal on the dash clock (it stops with the hit-stop); ride along with the dash momentum until it has unfolded.
        if(bDashAttack)
        {
            Reveal=FMath::Clamp((Elapsed-KukriDashRhythm::RiftStart)/(KukriDashRhythm::RiftEnd-KukriDashRhythm::RiftStart),0.f,1.f);
            if(const auto* P=Pawn();P&&Reveal<1.f)
            {
                const FVector Location=P->GetActorLocation();
                SkillRiftOrigin.AddToTranslation(Location-SkillRiftPawnLocation);SkillRiftPawnLocation=Location;
            }
        }
    }
    else
    {
        // Reveal on the turned angle (it stops with the hit-stop); the second turn glows harder.
        Dissolve=KukriWhirlRingDissolve;
        if(bWhirlwind)
        {
            const float Turned=FMath::Abs(WhirlwindTuning.TurnDegrees*WhirlwindFeel::Phase(Elapsed,WhirlwindTuning));
            Reveal=FMath::Clamp(Turned/KukriWhirlRingDegrees,0.f,1.f);
            const float Second=FMath::Clamp((Turned-360.f)/360.f,0.f,1.f);
            SkillRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),FMath::Lerp(KukriWhirlRingStrength,KukriWhirlRingSecondStrength,Second));
            // Hold the ring until the spin is over.
            if(Elapsed<WhirlwindTuning.ReadySeconds+WhirlwindTuning.SpinSeconds)Reveal=FMath::Min(Reveal,.999f);
        }
    }
    if(Reveal>=1.f&&SkillRiftFadeAge<0.f)SkillRiftFadeAge=0.f;
    else if(SkillRiftFadeAge>=0.f)SkillRiftFadeAge+=Delta;
    const float Recovery=SkillRiftFadeAge<0.f?0.f:FMath::Clamp(SkillRiftFadeAge/Dissolve,0.f,1.f);
    if(Recovery>=1.f){StopSkillRift();return;}
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),Reveal*1.06f);
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f-Recovery*Recovery*(3.f-2.f*Recovery));
    FTransform Pose=SkillRiftOrigin;
    if(SkillRift==EKukriSkillRift::Dash)Pose.AddToTranslation(SkillRiftDirection*(FMath::Max(0.f,SkillRiftFadeAge)*KukriDashRhythm::RiftDriftCM));
    else
    {
        const float Spread=1.f+KukriWhirlRingSpread*FMath::SmoothStep(0.f,1.f,Recovery);
        Pose.SetScale3D(FVector(Spread,Spread,1.f));
    }
    SkillRiftVisual->SetWorldTransform(Pose);
}

void UKukriWeaponComponent::StopSkillRift()
{
    SkillRift=EKukriSkillRift::None;SkillRiftAge=0.f;SkillRiftFadeAge=-1.f;
    if(SkillRiftVisual)SkillRiftVisual->SetVisibility(false);
}
