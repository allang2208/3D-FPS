#include "SecurityDroppedHat.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Net/UnrealNetwork.h"

ASecurityDroppedHat::ASecurityDroppedHat()
{
    PrimaryActorTick.bCanEverTick = false;
    bReplicates = true;
    SetReplicateMovement(true);
    HatBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HatBody"));
    SetRootComponent(HatBody);
    HatBody->SetMobility(EComponentMobility::Movable);
    HatBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HatBody->SetGenerateOverlapEvents(false);
    HatBody->SetCanEverAffectNavigation(false);
    HatBody->SetLinearDamping(.25f);
    HatBody->SetAngularDamping(.65f);
}

void ASecurityDroppedHat::BeginPlay()
{
    Super::BeginPlay();
    ConfigureBody();
    if (HasAuthority()) SetLifeSpan(35.f);
}

void ASecurityDroppedHat::SetHatMesh(UStaticMesh* Mesh)
{
    HatMesh = Mesh;
    if (HasActorBegunPlay()) ConfigureBody();
}

void ASecurityDroppedHat::ConfigureBody()
{
    if (!HatMesh) return;
    if (HatBody->GetStaticMesh() != HatMesh) HatBody->SetStaticMesh(HatMesh);
    HatBody->SetCollisionObjectType(ECC_PhysicsBody);
    HatBody->SetCollisionResponseToAllChannels(ECR_Ignore);
    HatBody->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
    HatBody->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Block);
    HatBody->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    HatBody->SetEnableGravity(true);
    HatBody->SetMassOverrideInKg(NAME_None, .32f);
    HatBody->SetUseCCD(true);
    HatBody->SetSimulatePhysics(true);
}

void ASecurityDroppedHat::Launch(const FVector& IncomingDirection, const FVector& HitLocation, const FVector& InheritedVelocity)
{
    if (!HasAuthority() || !HatBody->IsSimulatingPhysics()) return;
    const FVector Direction = IncomingDirection.GetSafeNormal(SMALL_NUMBER, FVector::ForwardVector);
    HatBody->SetPhysicsLinearVelocity(InheritedVelocity);
    const FVector Centre = HatBody->GetCenterOfMass();
    const FVector TransferPoint = Centre + (HitLocation - Centre).GetClampedToMaxSize(11.f);
    const FVector Impulse = (Direction * 230.f + FVector::UpVector * 165.f) * HatBody->GetMass();
    HatBody->AddImpulseAtLocation(Impulse, TransferPoint);
    const FVector TumbleAxis = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal(SMALL_NUMBER, FVector::RightVector);
    HatBody->AddAngularImpulseInDegrees(TumbleAxis * 120.f, NAME_None, true);
    HatBody->WakeAllRigidBodies();
    ForceNetUpdate();
}

void ASecurityDroppedHat::OnRep_HatMesh() { ConfigureBody(); }

void ASecurityDroppedHat::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ASecurityDroppedHat, HatMesh);
}
