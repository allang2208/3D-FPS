#include "SecurityHatComponent.h"
#include "SecurityDroppedHat.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

USecurityHatComponent::USecurityHatComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    SetIsReplicatedByDefault(true);
    SetMobility(EComponentMobility::Movable);
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetGenerateOverlapEvents(false);
    SetCanEverAffectNavigation(false);
}

void USecurityHatComponent::BeginPlay()
{
    Super::BeginPlay();
    ACharacter* Guard = Cast<ACharacter>(GetOwner());
    if (!Guard || !GetStaticMesh() || !Guard->GetMesh()->DoesSocketExist(HeadBone)) return;
    AttachToComponent(Guard->GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, HeadBone);
    SetRelativeTransform(HeadAttachmentTransform);
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Guard->OnTakePointDamage.AddDynamic(this, &USecurityHatComponent::OnOwnerPointDamage);
    OnRep_Dropped();
}

void USecurityHatComponent::OnOwnerPointDamage(AActor* DamagedActor, float Damage, AController* InstigatedBy,
    FVector HitLocation, UPrimitiveComponent* HitComponent, FName BoneName, FVector ShotFromDirection,
    const UDamageType* DamageType, AActor* DamageCauser)
{
    if (bDropped || Damage <= 0.f || !DamagedActor || DamagedActor != GetOwner() || !DamagedActor->HasAuthority()) return;
    const ACharacter* Guard = Cast<ACharacter>(DamagedActor);
    if (!Guard || !GetStaticMesh()) return;
    const USkeletalMeshComponent* Body = Guard->GetMesh();
    if (BoneName != HeadBone && !Body->BoneIsChildOf(BoneName, HeadBone)) return;
    // The delegate is dispatched before the lethal hit starts the corpse.
    // Do not reject zero remaining health: lethal headshots must detach too.
    const FTransform DropTransform = GetComponentTransform();
    ASecurityDroppedHat* Dropped = GetWorld()->SpawnActorDeferred<ASecurityDroppedHat>(
        ASecurityDroppedHat::StaticClass(), DropTransform, nullptr, nullptr,
        ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if (!Dropped) return;
    Dropped->SetHatMesh(GetStaticMesh());
    UGameplayStatics::FinishSpawningActor(Dropped, DropTransform);
    bDropped = true;
    OnRep_Dropped();
    DamagedActor->ForceNetUpdate();
    FVector Direction = ShotFromDirection.GetSafeNormal();
    if (Direction.IsNearlyZero() && DamageCauser) Direction = (HitLocation - DamageCauser->GetActorLocation()).GetSafeNormal();
    if (Direction.IsNearlyZero()) Direction = -Guard->GetActorForwardVector();
    Dropped->Launch(Direction, HitLocation, Guard->GetVelocity());
}

void USecurityHatComponent::OnRep_Dropped()
{
    SetVisibility(!bDropped);
    SetHiddenInGame(bDropped);
}

void USecurityHatComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (AActor* Guard = GetOwner()) Guard->OnTakePointDamage.RemoveDynamic(this, &USecurityHatComponent::OnOwnerPointDamage);
    Super::EndPlay(EndPlayReason);
}

void USecurityHatComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(USecurityHatComponent, bDropped);
}
