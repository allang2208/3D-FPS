#include "PKMBipodComponent.h"
#include "PKMBipodContacts.h"
#include "WeaponBipodDeploymentComponent.h"
#include "PKMLowpolyWeaponAssets.h"
#include "../FPSGAMECharacter.h"
#include "Engine/World.h"

namespace
{
// Bipod26 measures the existing transverse pin in WPN_root, after FBX Y reflection.
const FVector PKMBipodHingeCm(-.0038191676,54.97862697,1.73475258);
const FVector PKMBipodLegPivotsCm[]={FVector(.9961809963,54.97862697,1.73475258),FVector(-1.0038191453,54.97862697,1.73475258)};
}

UPKMBipodComponent::UPKMBipodComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetCastShadow(false);bReceivesDecals=false;
    ComponentTags.Add(TEXT("PKMBipod"));
}

bool UPKMBipodComponent::Configure(USkeletalMeshComponent* Rifle,bool Enabled)
{
    if(!Enabled || !PKMLowpolyWeaponAssets::Matches(Rifle))
    {
        SetVisibility(false,true);SetComponentTickEnabled(false);ResetMotion();return true;
    }
    auto* BaseMesh=LoadObject<UStaticMesh>(nullptr,PKMBipodAssets::Base);
    auto* MeshA=LoadObject<UStaticMesh>(nullptr,PKMBipodAssets::LegA);
    auto* MeshB=LoadObject<UStaticMesh>(nullptr,PKMBipodAssets::LegB);
    if(!BaseMesh || !MeshA || !MeshB)
    {
        SetVisibility(false,true);SetComponentTickEnabled(false);
        UE_LOG(LogTemp,Error,TEXT("PKM_BIPOD: missing Bipod26 split assets"));return false;
    }
    if(Weapon.Get()!=Rifle)
    {
        if(Weapon.IsValid())RemoveTickPrerequisiteComponent(Weapon.Get());
        Weapon=Rifle;AddTickPrerequisiteComponent(Rifle);
        AttachToComponent(Rifle,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
    }
    if(auto* Deployment=GetOwner()->FindComponentByClass<UWeaponBipodDeploymentComponent>())
        AddTickPrerequisiteComponent(Deployment);
    if(GetStaticMesh()!=BaseMesh){EmptyOverrideMaterials();SetStaticMesh(BaseMesh);}
    // The new exports use the current weapon-root frame, like GripMount25.
    SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01)));
    const auto MakeLeg=[&](TObjectPtr<UStaticMeshComponent>& Leg,UStaticMesh* Asset,const TCHAR* Name,int32 Index)
    {
        if(!Leg)
        {
            Leg=NewObject<UStaticMeshComponent>(GetOwner(),MakeUniqueObjectName(GetOwner(),UStaticMeshComponent::StaticClass(),Name));GetOwner()->AddInstanceComponent(Leg);
            Leg->SetupAttachment(this);Leg->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Leg->SetCastShadow(false);Leg->bReceivesDecals=false;Leg->RegisterComponent();
        }
        if(Leg->GetStaticMesh()!=Asset){Leg->EmptyOverrideMaterials();Leg->SetStaticMesh(Asset);}
        Leg->SetRelativeTransform(FTransform(FQuat::Identity,PKMBipodLegPivotsCm[Index]));
    };
    MakeLeg(FirstLeg,MeshA,TEXT("PKMBipodLegA"),0);MakeLeg(SecondLeg,MeshB,TEXT("PKMBipodLegB"),1);
    ContactWeight=0.f;ResetMotion();SetVisibility(true,true);SetComponentTickEnabled(true);return true;
}

FVector UPKMBipodComponent::GetHingeWorld() const
{
    return GetComponentTransform().TransformPosition(PKMBipodHingeCm);
}

FVector UPKMBipodComponent::GetRestFootWorld(int32 Leg) const
{
    const int32 I=FMath::Clamp(Leg,0,1);
    const FVector Tip=I==0?PKMBipodContacts::LegA:PKMBipodContacts::LegB;
    return GetComponentTransform().TransformPosition(PKMBipodLegPivotsCm[I]+Tip);
}

bool UPKMBipodComponent::CanReachContacts(const FVector& A,const FVector& B,const FVector& MountDelta) const
{
    const FVector Goals[]={A,B};const FTransform Frame=GetComponentTransform();
    for(int32 I=0;I<2;++I)
    {
        const FVector Tip=I==0?PKMBipodContacts::LegA:PKMBipodContacts::LegB;
        const FVector Pivot=Frame.TransformPosition(PKMBipodLegPivotsCm[I])+MountDelta;
        const FVector Rest=Frame.TransformVector(Tip);
        const FVector Target=Goals[I]-Pivot;
        const double Ratio=Target.Size()/FMath::Max(.01,Rest.Size());
        // 2026-09-23 放宽架设判定：腿长适应 ±5%→±8%，方向容差 cos .82→.78。
        if(Ratio<.92 || Ratio>1.08 || FVector::DotProduct(Rest.GetSafeNormal(),Target.GetSafeNormal())<.78)return false;
    }
    return true;
}

void UPKMBipodComponent::SetDeploymentContacts(const FVector& A,const FVector& B,float Weight)
{
    const float Previous=ContactWeight;ContactWeight=FMath::Clamp(Weight,0.f,1.f);
    ContactPoints[0]=A;ContactPoints[1]=B;
    if(Previous>0.f && ContactWeight<=0.f)ResetMotion();
    ApplyAngle();
}

void UPKMBipodComponent::ResetMotion()
{
    LastTime=-1.;Angles[0]=Angles[1]=AngularSpeeds[0]=AngularSpeeds[1]=0.f;
    LastVelocity=LastSpin=Acceleration=SpinAcceleration=FVector::ZeroVector;
    ApplyAngle();
}

void UPKMBipodComponent::ApplyAngle()
{
    // The source meshes already contain the requested legs-down rest pose.
    // Each opened leg has its own damped hinge; the barrel clamp stays fixed.
    UStaticMeshComponent* Legs[]={FirstLeg,SecondLeg};
    for(int32 I=0;I<2;++I)if(auto* Leg=Legs[I])
    {
        const FQuat FreeRotation(FVector::ForwardVector,Angles[I]);
        FQuat Rotation=FreeRotation;double LengthScale=1.;
        if(ContactWeight>0.f)
        {
            const FVector Tip=I==0?PKMBipodContacts::LegA:PKMBipodContacts::LegB;
            const FVector Goal=GetComponentTransform().InverseTransformPosition(ContactPoints[I])-PKMBipodLegPivotsCm[I];
            Rotation=FQuat::Slerp(FreeRotation,FQuat::FindBetweenNormals(Tip.GetSafeNormal(),Goal.GetSafeNormal()),ContactWeight);
            // Small independent leg-length adaptation for uneven top surfaces.
            LengthScale=FMath::Lerp(1.,FMath::Clamp(Goal.Size()/Tip.Size(),.95,1.05),static_cast<double>(ContactWeight));
        }
        Leg->SetRelativeRotation(Rotation);Leg->SetRelativeScale3D(FVector(LengthScale));
    }
}

void UPKMBipodComponent::SetLegsFrozen(bool bFrozen)
{
    if(bLegsFrozen==bFrozen)return;
    bLegsFrozen=bFrozen;
    if(bFrozen)
    {
        // 冻结即回到默认下垂：网格自带 legs-down 静止姿态，零角即可。
        LastTime=-1.;ContactWeight=0.f;
        Angles[0]=Angles[1]=AngularSpeeds[0]=AngularSpeeds[1]=0.f;
        ApplyAngle();
    }
}

void UPKMBipodComponent::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(DeltaTime,TickType,Tick);
    if(bLegsFrozen)return; // 架设中两腿钉死在默认下垂，不跟随枪体移动
    const auto* World=GetWorld();const auto* Rifle=Weapon.Get();
    if(!World || !World->IsGameWorld() || !Rifle || !Rifle->IsVisible() || Rifle->bHiddenInGame ||
       !IsVisible() || bHiddenInGame || GetOwner()->IsHidden() || !GetOwner()->IsActorTickEnabled())
    {ResetMotion();return;}
    if(ContactWeight>0.f)
    {
        const float Settle=FMath::Exp(-22.f*DeltaTime);
        for(int32 I=0;I<2;++I){Angles[I]*=Settle;AngularSpeeds[I]=0.f;}
        LastTime=-1.;ApplyAngle();return;
    }
    const FTransform Mount=GetComponentTransform();
    const FVector Position=Mount.TransformPosition(PKMBipodHingeCm);
    const FQuat Rotation=Mount.GetRotation();
    const double Now=World->GetTimeSeconds(),Elapsed=Now-LastTime;
    if(LastTime<0. || Elapsed<0. || Elapsed>.25 ||
       FVector::DistSquared(Position,LastPosition)>FMath::Square(80.) || Rotation.AngularDistance(LastRotation)>1.2)
    {
        ResetMotion();LastTime=Now;LastPosition=Position;LastRotation=Rotation;
        LastVelocity=GetOwner()->GetVelocity();return;
    }
    if(Elapsed<=UE_SMALL_NUMBER)return;
    const FVector Velocity=(Position-LastPosition)/Elapsed;
    FQuat Delta=Rotation*LastRotation.Inverse();Delta.Normalize();
    FVector SpinAxis;double SpinAngle;Delta.ToAxisAndAngle(SpinAxis,SpinAngle);
    if(SpinAngle>UE_PI)SpinAngle-=2.*UE_PI;
    const FVector Spin=SpinAxis*(SpinAngle/Elapsed);
    const float Filter=1.f-FMath::Exp(-25.f*static_cast<float>(Elapsed));
    Acceleration=FMath::Lerp(Acceleration,((Velocity-LastVelocity)/Elapsed).GetClampedToMaxSize(8000.),Filter);
    SpinAcceleration=FMath::Lerp(SpinAcceleration,((Spin-LastSpin)/Elapsed).GetClampedToMaxSize(160.),Filter);
    const FVector Axis=Rotation.RotateVector(FVector::ForwardVector);
    const FVector RestLever=Mount.TransformVector(FVector(0.,-1.53314,-14.04679));
    const FVector Force=FVector(0.,0.,World->GetGravityZ())-Acceleration*.8;
    constexpr float Min=-6.f*PI/180.f,Max=6.f*PI/180.f,Soft=.75f*PI/180.f;
    const double Duration=FMath::Min(Elapsed,.06);
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(Duration*240.));
    const float Dt=static_cast<float>(Duration/Steps);
    for(int32 Leg=0;Leg<2;++Leg)
    {
        const float Omega=2.f*PI*(Leg==0?3.2f:3.4f),Damping=Leg==0?.40f:.42f;
        float& Angle=Angles[Leg];float& AngularSpeed=AngularSpeeds[Leg];
        for(int32 Step=0;Step<Steps;++Step)
        {
            const FVector Lever=FQuat(Axis,Angle).RotateVector(RestLever);
            const double Inertia=FVector::DotProduct(Axis,FVector::CrossProduct(Lever,Force))/FMath::Max(1.,Lever.SizeSquared())
                -.7*FVector::DotProduct(Axis,SpinAcceleration);
            const float Stop=1800.f*(FMath::Max(0.f,Min+Soft-Angle)-FMath::Max(0.f,Angle-(Max-Soft)));
            AngularSpeed+=(FMath::Clamp(static_cast<float>(Inertia),-120.f,120.f)+Stop-Omega*Omega*Angle-2.f*Damping*Omega*AngularSpeed)*Dt;
            Angle+=AngularSpeed*Dt;
            if(Angle<Min){Angle=Min;if(AngularSpeed<0.f)AngularSpeed*= -.08f;}
            if(Angle>Max){Angle=Max;if(AngularSpeed>0.f)AngularSpeed*= -.08f;}
        }
    }
    ApplyAngle();LastTime=Now;LastPosition=Position;LastRotation=Rotation;LastVelocity=Velocity;LastSpin=Spin;
}

void UPKMBipodComponent::OnComponentDestroyed(bool bDestroyingHierarchy)
{
    if(IsValid(FirstLeg))FirstLeg->DestroyComponent();
    if(IsValid(SecondLeg))SecondLeg->DestroyComponent();
    FirstLeg=nullptr;SecondLeg=nullptr;
    Super::OnComponentDestroyed(bDestroyingHierarchy);
}

void PKMLowpolyWeaponAssets::ConfigureBipod(AActor* Owner,USkeletalMeshComponent* Weapon,bool Enabled)
{
    if(!Owner)return;
    auto* Part=Cast<UPKMBipodComponent>(FindBipod(Owner));
    // Remove the whole assembly when unequipped so a later recursive weapon
    // visibility refresh cannot reveal an attachment the player did not equip.
    if(!Enabled || !Matches(Weapon)){if(Part)Part->DestroyComponent();return;}
    if(!Part)
    {
        Part=NewObject<UPKMBipodComponent>(Owner);Owner->AddInstanceComponent(Part);
        Part->SetupAttachment(Weapon,TEXT("WPN_root"));Part->RegisterComponent();
    }
    Part->Configure(Weapon,true);
}

void AFPSGAMECharacter::SetGunsmithBipod(const FString& Variant)
{
    PKMLowpolyWeaponAssets::ConfigureBipod(this,AKMViewmodel,bInventoryWeaponReady&&Variant==TEXT("pkm_bipod"));
}
