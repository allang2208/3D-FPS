#include "FPSIceArmorComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "SceneView.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

void UFPSIceArmorComponent::ClearVisuals()
{
    for(auto& C:BodyShells)if(C)C->DestroyComponent();BodyShells.Reset();
    if(Lens)Lens->DestroyComponent();Lens=nullptr;
    if(Mist)Mist->DestroyComponent();Mist=nullptr;
    if(Chips)Chips->DestroyComponent();Chips=nullptr;ChipParticles.Reset();ChipCursor=0;
    ArmorMID=nullptr;LensMID=nullptr;bVisualWasActive=false;EndingAt=-1;NextOutfitAt=NextDetailAt=0;VisualHitAt=-10;
}
void UFPSIceArmorComponent::UpdateOutfit()
{
    NextOutfitAt=Clock()+.3;
    const auto* Outfit=GetOwner()->FindComponentByClass<UFPSModularOutfitComponent>();
    const FString Shirt=Outfit?Outfit->EquippedOutfit(7).ToString():FString(),Pants=Outfit?Outfit->EquippedOutfit(15).ToString():FString();
    const FString Gloves=Outfit?Outfit->EquippedOutfit(3).ToString():FString(),Boots=Outfit?Outfit->EquippedOutfit(13).ToString():FString();
    auto Profile=[](const FString& Name){return Name.IsEmpty()||Name==TEXT("None")?0:(Name.Contains(TEXT("chainmail"))||Name.Contains(TEXT("armor"))||Name.Contains(TEXT("steel"))?2:1);};
    OutfitProfiles[0]=Profile(Shirt);
    OutfitProfiles[1]=OutfitProfiles[0]*3+Profile(Gloves);
    OutfitProfiles[2]=Profile(Pants)*3+Profile(Boots);
    bHideThigh=Shirt.Contains(TEXT("robe"))||Shirt.Contains(TEXT("coat"));bHideBack=false;
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();auto* Leader=Body?Body->GetBodyMesh():nullptr;
    TArray<USkeletalMeshComponent*> Parts;GetOwner()->GetComponents(Parts);
    for(auto* Part:Parts)if(Part!=Leader&&Part->GetAttachParent()==Leader&&Part->GetSkeletalMeshAsset()&&Part->IsVisible())
        if(Part->GetSkeletalMeshAsset()->GetName().Contains(TEXT("Backpack"))){bHideBack=true;break;}
    if(!bHideBack)
    {
        TArray<UStaticMeshComponent*> StaticParts;GetOwner()->GetComponents(StaticParts);
        for(auto* Part:StaticParts)if(Part->GetAttachParent()==Leader&&Part->GetStaticMesh()&&Part->IsVisible())
            if(Part->GetStaticMesh()->GetName().Contains(TEXT("Backpack"))){bHideBack=true;break;}
    }
}
void UFPSIceArmorComponent::OnRep_Impact()
{
    if(GetNetMode()==NM_DedicatedServer||!Impact.Serial||Impact.Serial==LastImpactSerial||Remaining()<=0)return;
    // Hit and cast state can arrive in different updates. Tick consumes the hit once both exist.
    if(Impact.CastSerial!=State.Serial||!State.bActive)return;
    LastImpactSerial=Impact.Serial;if(Clock()-Impact.At>.4||Impact.At<State.StartedAt)return;
    VisualHitAt=Impact.At;VisualHitDirection=GetOwner()->GetActorTransform().TransformVectorNoScale(Impact.LocalDirection).GetSafeNormal();EmitChips(VisualHitDirection,5);
}
void UFPSIceArmorComponent::UpdateVisuals(float Delta)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());if(!P)return;
    const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();if(Health&&Health->IsDead()){ClearVisuals();return;}
    const double Now=Clock();const bool Active=Remaining()>0;
    if(Active){bVisualWasActive=true;EndingAt=-1;VisualStartedAt=View().StartedAt;VisualEndAt=View().StartedAt+View().Cast.Duration;VisualPulseSeconds=FMath::Max(.1f,View().Cast.PulseSeconds);}
    else if(bVisualWasActive){bVisualWasActive=false;EndingAt=Now;EmitChips(P->GetActorForwardVector(),12);}
    if(!Active&&(EndingAt<0||Now-EndingAt>.6)){ClearVisuals();return;}
    const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();auto* Leader=Body?Body->GetBodyMesh():nullptr;
    const bool First=P->IsLocallyControlled()&&(!Body||!Body->IsThirdPersonViewEnabled()),WorldVisible=!First&&Leader&&Leader->IsVisible()&&!Leader->bHiddenInGame;
    if(First!=bLastFirstPerson){for(auto& C:ChipParticles)C.At=-100;bLastFirstPerson=First;}
    if(Now>=NextOutfitAt)UpdateOutfit();
    if(Now>=NextDetailAt)
    {
        NextDetailAt=Now+.25;
        if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
        {VisualDetail=float(Fluid->AllocateDetail(P->GetActorLocation(),8,P->IsLocallyControlled()))/8;VisualWind=Fluid->WindAt(P->GetActorLocation())*.08;}
    }
    const float Age=FMath::Max(0.,Now-VisualStartedAt),Dissolve=EndingAt>=0?FMath::Clamp(float((Now-EndingAt)/.55),0.f,1.f):0.f,Growth=FMath::Clamp(Age/.7f,0.f,1.f);
    const float PulsePhase=FMath::Clamp(FMath::Fmod(Age,VisualPulseSeconds)/.36f,0.f,1.f);
    const float Pulse=Active&&Age>=VisualPulseSeconds&&PulsePhase<1.f?FMath::Sin(PI*PulsePhase):0.f;
    const float Hit=FMath::Square(FMath::Clamp(1.f-float(Now-VisualHitAt)/.18f,0.f,1.f));
    if(ArmorMaterial&&!ArmorMID)ArmorMID=UMaterialInstanceDynamic::Create(ArmorMaterial,this);
    if(LensMaterial&&!LensMID)LensMID=UMaterialInstanceDynamic::Create(LensMaterial,this);
    const FVector HitPoint=(Leader?Leader->GetSocketLocation(TEXT("spine_05")):P->GetActorLocation()+FVector(0,0,35))+VisualHitDirection*22;
    for(auto* MID:{ArmorMID.Get(),LensMID.Get()})if(MID)
    {
        MID->SetScalarParameterValue(TEXT("Growth"),Growth);MID->SetScalarParameterValue(TEXT("Fade"),1.f);MID->SetScalarParameterValue(TEXT("Dissolve"),Dissolve);
        MID->SetScalarParameterValue(TEXT("Pulse"),Pulse*.35f);MID->SetScalarParameterValue(TEXT("PulsePhase"),PulsePhase);MID->SetScalarParameterValue(TEXT("Impact"),Hit);MID->SetVectorParameterValue(TEXT("HitPosition"),FLinearColor(HitPoint));
    }
    if(ArmorMID){ArmorMID->SetScalarParameterValue(TEXT("HideBack"),bHideBack?1:0);ArmorMID->SetScalarParameterValue(TEXT("HideThigh"),bHideThigh?1:0);}
    if(First&&P->FirstPersonCamera&&LensMesh&&LensMID)
    {
        if(!Lens)
        {
            // Camera descendants inherit weapon-specific FirstPersonScale. A
            // helmet has its own eye projection and must keep its full depth.
            Lens=NewObject<UStaticMeshComponent>(P,NAME_None,RF_Transient);P->AddInstanceComponent(Lens);Lens->SetupAttachment(P->GetRootComponent());Lens->SetAbsolute(true,true,true);
            Lens->SetStaticMesh(LensMesh);Lens->SetMaterial(0,LensMID);Lens->SetMobility(EComponentMobility::Movable);
            Lens->SetCollisionEnabled(ECollisionEnabled::NoCollision);Lens->SetGenerateOverlapEvents(false);Lens->SetCastShadow(false);
            Lens->SetVisibleInRayTracing(false);Lens->SetCanEverAffectNavigation(false);Lens->SetOnlyOwnerSee(true);Lens->SetOwnerNoSee(false);
            Lens->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::None);Lens->SetTranslucentSortPriority(100);Lens->RegisterComponent();
            PreviousCameraRotation=P->FirstPersonCamera->GetComponentRotation();LensSway=FRotator::ZeroRotator;
        }
        int32 W=1920,H=1080;const auto* PC=Cast<APlayerController>(P->GetController());if(PC)PC->GetViewportSize(W,H);
        const auto* Manager=PC?PC->PlayerCameraManager.Get():nullptr;const bool FinalPOV=Manager&&PC->GetViewTarget()==P;
        const FVector Eye=FinalPOV?Manager->GetCameraLocation():P->FirstPersonCamera->GetComponentLocation();
        const FRotator Rotation=FinalPOV?Manager->GetCameraRotation():P->FirstPersonCamera->GetComponentRotation();
        const float FOV=FinalPOV?Manager->GetFOVAngle():P->FirstPersonCamera->FieldOfView,Distance=42.f;
        FMinimalViewInfo View;if(FinalPOV)View=Manager->GetCameraCacheView();
        else {View.AspectRatio=P->FirstPersonCamera->AspectRatio;View.bConstrainAspectRatio=P->FirstPersonCamera->bConstrainAspectRatio;View.AspectRatioAxisConstraint=P->FirstPersonCamera->AspectRatioAxisConstraint;}
        View.FOV=FMath::Clamp(FOV,1.f,170.f);
        FSceneViewProjectionData Projection;const FIntRect ViewRect(0,0,FMath::Max(1,W),FMath::Max(1,H));Projection.SetViewRectangle(ViewRect);
        // Use the engine projection: this player's camera maintains vertical FOV.
        FMinimalViewInfo::CalculateProjectionMatrixGivenViewRectangle(View,P->FirstPersonCamera->AspectRatioAxisConstraint,ViewRect,Projection);
        const float HalfWidth=Distance/float(Projection.ProjectionMatrix.M[0][0]),HalfHeight=Distance/float(Projection.ProjectionMatrix.M[1][1]),Aspect=HalfWidth/HalfHeight;
        const FRotator Motion=(PreviousCameraRotation-Rotation).GetNormalized();PreviousCameraRotation=Rotation;
        if(Delta>0)LensSway=FMath::RInterpTo(LensSway,FRotator(FMath::Clamp(Motion.Pitch*.055,-.12,.12),FMath::Clamp(Motion.Yaw*.055,-.12,.12),0),Delta,18);
        Lens->SetWorldLocationAndRotation(Eye+Rotation.RotateVector(FVector(Distance,0,0)),Rotation.Quaternion()*LensSway.Quaternion());
        Lens->SetWorldScale3D(FVector(1,HalfWidth/50,HalfHeight/50));Lens->SetVisibility(true);
        const FVector Right=Rotation.RotateVector(FVector::RightVector),Up=Rotation.RotateVector(FVector::UpVector);
        const float Side=FVector::DotProduct(VisualHitDirection,Right)>=0?1:-1;
        const FVector LensHit=Eye+Rotation.Vector()*Distance+Right*HalfWidth*.82*Side-Up*(HalfHeight*.25);
        LensMID->SetVectorParameterValue(TEXT("HitPosition"),FLinearColor(LensHit));LensMID->SetScalarParameterValue(TEXT("HelmetAspect"),Aspect);
    }
    else if(Lens)Lens->SetVisibility(false);
    if(WorldVisible&&ArmorMID&&ShellMeshes.Num()==UE_ARRAY_COUNT(IceArmorAssets::Shells))
    {
        while(BodyShells.Num()<IceArmorAssets::WorldPartCount)
        {
            auto* C=NewObject<USkeletalMeshComponent>(P,NAME_None,RF_Transient);P->AddInstanceComponent(C);C->SetupAttachment(Leader);C->SetRelativeTransform(FTransform::Identity);
            C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetCastShadow(false);C->SetVisibleInRayTracing(false);
            C->SetCanEverAffectNavigation(false);C->SetDisablePostProcessBlueprint(true);
            // The separate helmet extends above the headless body's bounds.
            C->bUseAttachParentBound=false;C->bUseBoundsFromLeaderPoseComponent=false;C->SetBoundsScale(1.15f);
            C->RegisterComponent();C->AddTickPrerequisiteComponent(Leader);BodyShells.Add(C);
        }
        for(int32 I=0;I<IceArmorAssets::WorldPartCount;++I)
        {
            const int32 Index=I==0?OutfitProfiles[0]:I==1?IceArmorAssets::ArmShellOffset+OutfitProfiles[1]:I==2?IceArmorAssets::LegShellOffset+OutfitProfiles[2]:IceArmorAssets::HelmetShellIndex;
            auto* C=BodyShells[I].Get();auto* Asset=ShellMeshes[Index].Get();
            if(C->GetAttachParent()!=Leader){C->AttachToComponent(Leader,FAttachmentTransformRules::SnapToTargetNotIncludingScale);C->SetLeaderPoseComponent(Leader);C->AddTickPrerequisiteComponent(Leader);}
            if(Asset&&C->GetSkeletalMeshAsset()!=Asset){C->SetSkeletalMeshAsset(Asset);C->SetMaterial(0,ArmorMID);C->SetLeaderPoseComponent(Leader);}
            C->SetVisibility(Asset!=nullptr);C->SetOwnerNoSee(false);
        }
    }
    else for(auto& C:BodyShells)if(C)C->SetVisibility(false);
    if(MistSystem&&Active&&!Mist)
    {
        Mist=NewObject<UNiagaraComponent>(P,NAME_None,RF_Transient);P->AddInstanceComponent(Mist);Mist->SetupAttachment(P->GetRootComponent());
        Mist->SetAutoActivate(false);Mist->SetAsset(MistSystem);Mist->SetCastShadow(false);Mist->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mist->SetCanEverAffectNavigation(false);Mist->RegisterComponent();
        Mist->SetVariablePosition(TEXT("User.CurrentPosition"),P->GetActorLocation());Mist->SetVariableVec3(TEXT("User.Wind"),VisualWind);
        Mist->SetVariableFloat(TEXT("User.Strength"),0.f);Mist->Activate(true);
    }
    if(Mist)
    {
        Mist->SetVariablePosition(TEXT("User.CurrentPosition"),P->GetActorLocation());Mist->SetVariableVec3(TEXT("User.Wind"),VisualWind);
        Mist->SetVariableFloat(TEXT("User.Strength"),Active&&(First||WorldVisible)?VisualDetail*FMath::Max(Pulse,Age<.7f?.45f:0.f)*(First?.2f:1.f):0.f);
    }
    UpdateChips();
}
