#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriRiftRibbons.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

// Swing rift (2026-10-23, user: "a space distortion like the two-handed sword, like sword qi").  The rune sword's normal
// slash rift (URuneSwordComponent::StartRift/TickRift): a crescent baked from the blade's authored contact path, frozen
// in world space at the viewmodel's transform, revealed along U (SweepProgress) and dissolved while it drifts forward.
// Here the reveal follows the swing's author clock (it stops with the hit-stop) and the dissolve runs in real time.

namespace
{
    using FRibbon=const float (*)[2][3];

    /** Ribbons of one stage: the slashes have one crescent, the stab two crossed narrow ribbons. */
    int32 StageRibbons(int32 Stage,FRibbon Out[2])
    {
        if(Stage==0){Out[0]=KukriRiftRibbons::Sweep;return 1;}
        if(Stage==1){Out[0]=KukriRiftRibbons::Diag;return 1;}
        if(Stage==KukriRhythm::UppercutStage){Out[0]=KukriRiftRibbons::Upper;return 1;}
        if(Stage==KukriRhythm::HeavyStage){Out[0]=KukriRiftRibbons::Heavy;return 1;}
        Out[0]=KukriRiftRibbons::StabEdge;Out[1]=KukriRiftRibbons::StabFlat;return 2;
    }

    UE::Geometry::FDynamicMesh3 BuildRibbons(int32 Stage)
    {
        using namespace UE::Geometry;
        FDynamicMesh3 Mesh;Mesh.EnableAttributes();
        FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
        FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
        FRibbon Ribbons[2]={};
        const int32 Count=StageRibbons(Stage,Ribbons);
        constexpr int32 N=KukriRiftRibbons::Stations;
        for(int32 R=0;R<Count;++R)
        {
            const int32 Base=Mesh.MaxVertexID();
            for(int32 S=0;S<N;++S)
                for(int32 E=0;E<2;++E)
                {
                    const float* P=Ribbons[R][S][E];
                    Mesh.AppendVertex(FVector3d(P[0],P[1],P[2]));
                    UV->AppendElement(FVector2f(float(S)/(N-1),float(E)));
                    Normals->AppendElement(FVector3f(0.f,0.f,1.f));   // unlit two-sided material: the normal is unused
                }
            for(int32 S=0;S<N-1;++S)
            {
                const int32 A=Base+S*2;
                for(const FIndex3i T:{FIndex3i(A,A+2,A+1),FIndex3i(A+1,A+2,A+3)})
                {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
            }
        }
        return Mesh;
    }
}

void UKukriWeaponComponent::StartRift()
{
    auto* P=Pawn();
    if(!P||!Viewmodel||!Camera)return;
    if(!RiftVisual)
    {
        auto* Material=LoadObject<UMaterialInterface>(nullptr,KukriRhythm::RiftMaterial);
        if(!Material)return;
        RiftVisual=NewObject<UDynamicMeshComponent>(P,TEXT("KukriRift"));
        P->AddInstanceComponent(RiftVisual);
        RiftVisual->SetMobility(EComponentMobility::Movable);
        RiftVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);RiftVisual->SetGenerateOverlapEvents(false);
        RiftVisual->SetCanEverAffectNavigation(false);RiftVisual->SetCastShadow(false);RiftVisual->SetReceivesDecals(false);
        RiftVisual->SetOnlyOwnerSee(true);RiftVisual->bVisibleInRayTracing=false;RiftVisual->bAffectDistanceFieldLighting=false;
        RiftVisual->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        RiftVisual->RegisterComponent();
        RiftMID=UMaterialInstanceDynamic::Create(Material,this);
        RiftVisual->SetMaterial(0,RiftMID);
        RiftStage=INDEX_NONE;
    }
    if(RiftStage!=Stage){RiftVisual->SetMesh(BuildRibbons(Stage));RiftVisual->SetMaterial(0,RiftMID);RiftStage=Stage;}
    // Freeze the authored crescent where the viewmodel is now, so it stays in the world while the view moves on.
    RiftOrigin=Viewmodel->GetComponentTransform();RiftDirection=Camera->GetForwardVector();
    RiftAge=0.f;RiftFadeAge=-1.f;bRiftActive=true;
    const auto& R=KukriRhythm::Rifts[Stage];
    RiftMID->SetScalarParameterValue(TEXT("RiftStrength"),R.Strength);
    RiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    RiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    RiftVisual->SetWorldTransform(RiftOrigin);
    RiftVisual->SetVisibility(true);
}

void UKukriWeaponComponent::TickRift(float Delta)
{
    if(!bRiftActive||!RiftVisual||!RiftMID)return;
    const auto& R=KukriRhythm::Rifts[RiftStage==INDEX_NONE?Stage:RiftStage];
    RiftAge+=Delta;
    // Reveal on the swing's author clock while it plays (frozen through a hit-stop); the fade is real time.
    const float Reveal=(bAttacking||bUppercut||bHeavyAttack)&&Stage==RiftStage?FMath::Clamp((Elapsed-R.Start)/FMath::Max(.01f,R.End-R.Start),0.f,1.f):1.f;
    if(Reveal>=1.f&&RiftFadeAge<0.f)RiftFadeAge=0.f;
    else if(RiftFadeAge>=0.f)RiftFadeAge+=Delta;
    const float Recovery=RiftFadeAge<0.f?0.f:FMath::Clamp(RiftFadeAge/R.Dissolve,0.f,1.f);
    if(Recovery>=1.f){StopRift();return;}
    RiftMID->SetScalarParameterValue(TEXT("SweepProgress"),Reveal*1.06f);
    RiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f-Recovery*Recovery*(3.f-2.f*Recovery));
    FTransform Pose=RiftOrigin;Pose.AddToTranslation(RiftDirection*(RiftAge*R.DriftCM));
    RiftVisual->SetWorldTransform(Pose);
}

void UKukriWeaponComponent::StopRift()
{
    bRiftActive=false;RiftAge=0.f;RiftFadeAge=-1.f;
    if(RiftVisual)RiftVisual->SetVisibility(false);
}
