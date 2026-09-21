#include "RuneOrbBladesComponent.h"
#include "RuneOrbBladeProjectile.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "UObject/ConstructorHelpers.h"

URuneOrbBladesComponent::URuneOrbBladesComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> BladeAsset(
        TEXT("/Game/Weapons/RuneOrbBlade20260921/SM_RuneOrbBlade.SM_RuneOrbBlade"));
    if (BladeAsset.Succeeded()) BladeMesh = BladeAsset.Object;
}

bool URuneOrbBladesComponent::SwordEquipped() const
{
    const auto* Owner = Cast<APawn>(GetOwner());
    const auto* Profile = Owner && Owner->GetGameInstance()
        ? Owner->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    const auto* Item = Profile ? Profile->Equipped() : nullptr;
    return Item && !Profile->ActiveProductionTool() && Item->Definition == TEXT("ue_rune_sword");
}

bool URuneOrbBladesComponent::NoAbilityCooldown() const
{
    const auto* Owner = Cast<APawn>(GetOwner());
    const auto* Profile = Owner && Owner->GetGameInstance()
        ? Owner->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    return Profile && Profile->HasNoAbilityCooldown();
}

float URuneOrbBladesComponent::BladeDamage(const UColdSteelStatusModel* Profile)
{
    const auto* Item = Profile->Equipped();
    const double Weapon = ColdSteelMelee::Evaluate(*Item, Profile).Damage;
    return FMath::FloorToFloat(float(Weapon + Profile->Derived(TEXT("matk"))) * BladeDamageMultiplier);
}

bool URuneOrbBladesComponent::CanUse() const
{
    const auto* Player = Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC = Player ? Cast<APlayerController>(Player->GetController()) : nullptr;
    const auto* Health = Player ? Player->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
    const auto* Build = PC ? PC->FindComponentByClass<UVoxelBuildComponent>() : nullptr;
    return Player && Player->IsLocallyControlled() && GetWorld()->GetNetMode() == NM_Standalone && PC &&
        !AFPSGAMEPlayerController::BlocksOngoingActions(PC) && !Player->IsTraversing() &&
        !Player->IsLeftHandHeldForCast() && (!Health || !Health->IsDead()) && (!Build || !Build->IsBuilding()) && SwordEquipped();
}

int32 URuneOrbBladesComponent::AvailableBladeCount() const
{
    int32 Count = 0;
    for (const auto& Slot : Slots)
        if (!Slot.bLaunched && Slot.Orb.IsValid() && Slot.Orb->CanLaunch()) ++Count;
    return Count;
}

void URuneOrbBladesComponent::Trigger()
{
    if (!CanUse() || Cooldown > 0.f) return;
    // The press only queues a request; the blade row appears with the raised-hand
    // gather gesture and each launch rides the release push (shared fireball hands).
    if (bActive) PendingLaunches = FMath::Min(PendingLaunches + 1, AvailableBladeCount());
    else bQueuedSummon = true;
}

UFPSFireballComponent* URuneOrbBladesComponent::Hands() const
{
    const auto* Owner = Cast<APawn>(GetOwner());
    return Owner ? Owner->FindComponentByClass<UFPSFireballComponent>() : nullptr;
}

void URuneOrbBladesComponent::ServiceGestureQueue()
{
    if (!bQueuedSummon && PendingLaunches == 0) return;
    auto* Player = Cast<AFPSGAMECharacter>(GetOwner());
    auto* H = Hands();
    if (!Player || !H || !CanUse()) { bQueuedSummon = false; PendingLaunches = 0; return; }
    // Transient weapon actions can finish before this queued gesture takes the hand.
    if (Player->IsLeftHandBusyForCast()) return;
    if (bQueuedSummon)
    {
        if (Cooldown > 0.f || bActive || !SwordEquipped()) { bQueuedSummon = false; return; }
        // Raise-and-gather: the hand lifts like the fireball charge while the row appears.
        if (!H->TryBeginSpellGesture(this, false, 1.f, FSimpleDelegate())) return;
        bQueuedSummon = false;
        OpenOrbit();
    }
    if (PendingLaunches > 0)
    {
        PendingLaunches = bActive ? FMath::Min(PendingLaunches, AvailableBladeCount()) : 0;
        if (PendingLaunches == 0) return;
        if (H->IsSpellGesture(this))
        {
            // While gathering/readying, the first contact is still pending. Once
            // extended, each queued press launches at 100 ms spacing without a re-push.
            if (GetWorld()->GetTimeSeconds() - LastLaunchTime >= BurstInterval &&
                H->ContinueSpellRelease(this, BurstHoldSeconds, true)) LaunchOne();
            return;
        }
        // Release push: the blade leaves the row at the gesture's contact frame.
        if (!H->TryBeginSpellGesture(this, true, 1.f,
            FSimpleDelegate::CreateUObject(this, &ThisClass::LaunchOne))) return;
        // Consume only at contact; presses arriving before it remain counted.
    }
}

void URuneOrbBladesComponent::OpenOrbit()
{
    auto* Character = Cast<ACharacter>(GetOwner());
    if (!Character || !Character->GetGameInstance() || !BladeMesh) return;
    auto* Profile = Character->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile || !Profile->Equipped()) return;
    FVector Eye, Forward, Right, Up;
    float TanVertical;
    if (!ViewBasis(Eye, Forward, Right, Up, TanVertical)) return;
    const float Damage = BladeDamage(Profile);
    // 2D craft-affix bridge, snapshotted per summon like the 2D trigger reads _craftEffects.
    ActiveBladeCount = BaseBladeCount; ActiveRangeCM = 1600.f; VulnerabilityStacks = 0;
    if (const auto* Item = Profile->Equipped())
        if (auto* E = Character->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            ActiveBladeCount += FMath::Max(0, FMath::FloorToInt(
                float(E->CraftEffect(*Item, TEXT("runeRestructureCount")))));
            ActiveRangeCM += float(E->CraftEffect(*Item, TEXT("specialRangeDelta"))) * 1.6f; // 2D px -> cm
            if (E->CraftEffect(*Item, TEXT("magicVulnerabilityOnHit")) > 0)
                VulnerabilityStacks = FMath::Max(1, FMath::FloorToInt(
                    float(E->CraftEffect(*Item, TEXT("magicVulnerabilityStacks")))));
        }
    bActive = true; Elapsed = 0.f; LastLaunchTime = -1.0; Slots.Reset();
    // View-space wing row, the ice spike's layout: even indices take the left wing so
    // the row stays symmetric and never crowds the right-handed melee weapon.
    for (int32 i = 0; i < ActiveBladeCount; ++i)
    {
        FBladeSlot Slot;
        Slot.Lateral = (i % 2 == 0 ? -1.f : 1.f) * (WingGap + float(i / 2) * WingSpacing);
        Slot.Roll = i * 113.f;
        Slot.SwayPhase = i * 0.5f;
        Slots.Add(MoveTemp(Slot));
    }
    const FVector Extent = BladeMesh->GetBounds().BoxExtent;
    const float VisibleHeight = FMath::Max(4.f, (ForwardDistance - Extent.X) * TanVertical - FMath::Max(Extent.Y, Extent.Z));
    for (auto& Slot : Slots)
    {
        const FVector Position = Eye + Forward * ForwardDistance + Right * Slot.Lateral + Up * VisibleHeight;
        // Tip (+X) faces away from the camera, matching the ice shard silhouette.
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Params.Owner = Character; Params.Instigator = Character;
        if (auto* Orb = GetWorld()->SpawnActor<ARuneOrbBlade>(Position, Forward.Rotation().Add(0.f, 0.f, Slot.Roll), Params))
        {
            Orb->Setup(this, Character, Damage, BladeMesh);
            Slot.Orb = Orb;
        }
    }
}

bool URuneOrbBladesComponent::ViewBasis(FVector& Eye, FVector& Forward, FVector& Right, FVector& Up, float& TanVertical) const
{
    const auto* Character = Cast<APawn>(GetOwner());
    const auto* Camera = Character ? Character->FindComponentByClass<UCameraComponent>() : nullptr;
    if (!Camera) return false;
    Eye = Camera->GetComponentLocation();
    const FRotationMatrix ViewBasis(Camera->GetComponentRotation());
    Forward = ViewBasis.GetUnitAxis(EAxis::X);
    Right = ViewBasis.GetUnitAxis(EAxis::Y);
    Up = ViewBasis.GetUnitAxis(EAxis::Z);
    // The player camera maintains vertical FOV, using its configured aspect to store horizontal FOV.
    TanVertical = FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView * .5f)) / FMath::Max(.1f, Camera->AspectRatio);
    return true;
}

void URuneOrbBladesComponent::LaunchOne()
{
    // Contact delegates are rechecked: equipment/menu/death can change after G.
    if (!bActive || !CanUse() || PendingLaunches <= 0) { PendingLaunches = 0; return; }
    auto* Character = Cast<APawn>(GetOwner());
    const auto* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
    const auto* Camera = Character ? Character->FindComponentByClass<UCameraComponent>() : nullptr;
    if (!PC || !Camera) return;
    // Crosshair aim, the same eye-trace convention as the fireball release.
    FHitResult Aim;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RuneBladeAim), false, Character);
    const FVector Eye = Camera->GetComponentLocation();
    GetWorld()->LineTraceSingleByChannel(Aim, Eye, Eye + Camera->GetForwardVector() * 20000.f,
        ECC_Visibility, Query);
    const FVector Target = Aim.bBlockingHit ? Aim.ImpactPoint : Eye + Camera->GetForwardVector() * 20000.f;
    // A random still-hovering blade leaves the ring, like the 2D launcher.
    TArray<int32> Available;
    for (int32 i = 0; i < Slots.Num(); ++i)
        if (Slots[i].Orb.IsValid() && !Slots[i].bLaunched && Slots[i].Orb->CanLaunch()) Available.Add(i);
    if (Available.IsEmpty()) { PendingLaunches = 0; return; }
    const int32 Pick = Available[FMath::RandRange(0, Available.Num() - 1)];
    Slots[Pick].bLaunched = true;
    if (auto* Orb = Slots[Pick].Orb.Get()) Orb->Launch(Target);
    --PendingLaunches;
    LastLaunchTime = GetWorld()->GetTimeSeconds();
    if (auto* H = Hands()) H->ContinueSpellRelease(this, BurstHoldSeconds, false);
}

void URuneOrbBladesComponent::EndOrbit()
{
    bQueuedSummon = false; PendingLaunches = 0;
    if (bActive) FinishOrbit(true);
    else if (auto* H = Hands()) H->CancelSpellGesture(this);
}

void URuneOrbBladesComponent::FinishOrbit(bool bCancelGesture)
{
    for (auto& Slot : Slots)
        if (auto* Orb = Slot.Orb.Get())
            if (!Orb->IsFlying() && !Orb->IsFinished()) Orb->StartFade();
    Slots.Reset();
    bActive = false; Elapsed = 0.f;
    bQueuedSummon = false; PendingLaunches = 0;
    // A nearby final hit must not cut the last shot's palm hold/recovery short.
    if (bCancelGesture) if (auto* H = Hands()) H->CancelSpellGesture(this);
    Cooldown = NoAbilityCooldown() ? 0.f : CooldownDuration;
}

void URuneOrbBladesComponent::NotifyBladeResult(bool bKilled)
{
    // 2D contract: a blade kill runs the same reduction as a melee swing — every
    // ability cooldown (this orbit's own included) shrinks by half a second.
    if (!bKilled) return;
    if (auto* Owner = Cast<APawn>(GetOwner()); Owner && Owner->GetGameInstance())
        if (auto* Profile = Owner->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Profile->ReduceAllAbilityCooldowns(.5f);
}

void URuneOrbBladesComponent::BeginPlay()
{
    Super::BeginPlay();
    if (auto* H = Hands()) AddTickPrerequisiteComponent(H);
    SetComponentTickEnabled(true);
}

void URuneOrbBladesComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    EndOrbit();
    Super::EndPlay(Reason);
}

void URuneOrbBladesComponent::TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta, Type, Tick);
    Cooldown = NoAbilityCooldown() ? 0.f : FMath::Max(0.f, Cooldown - Delta);
    auto* Character = Cast<APawn>(GetOwner());
    const auto* Health = Character ? Character->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
    if (!Character || !SwordEquipped() || (Health && Health->IsDead())) { EndOrbit(); return; }
    if (!CanUse())
    {
        bQueuedSummon = false; PendingLaunches = 0;
        if (auto* H = Hands()) H->CancelSpellGesture(this);
    }
    else ServiceGestureQueue();
    if (!bActive) return;
    Elapsed += Delta;
    if (Elapsed >= ActiveSeconds) { FinishOrbit(true); return; }
    FVector Eye, Forward, Right, Up;
    float TanVertical;
    if (!ViewBasis(Eye, Forward, Right, Up, TanVertical)) return;
    const FVector Extent = BladeMesh->GetBounds().BoxExtent;
    const float VisibleHeight = FMath::Max(4.f, (ForwardDistance - Extent.X) * TanVertical - FMath::Max(Extent.Y, Extent.Z));
    const FRotator Facing = Forward.Rotation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RuneBladeHover), false, Character);
    bool bAnyPending = false;
    for (auto& Slot : Slots)
    {
        if (Slot.Orb.IsValid())
        {
            if (Slot.Orb->IsFinished()) { Slot.Orb.Reset(); }
            else bAnyPending = true;
        }
        if (Slot.Orb.IsValid() && !Slot.bLaunched)
        {
            // Independent sway phases keep the row alive instead of pulsing in lockstep.
            Slot.SwayPhase += Delta;
            const float SwayY = FMath::Sin(Slot.SwayPhase * 1.8f) * 2.f;
            FVector Desired = Eye + Forward * ForwardDistance
                + Right * (Slot.Lateral + FMath::Sin(Slot.SwayPhase * 2.0f) * 3.f)
                + Up * (VisibleHeight + SwayY);
            // Same cover rule as the ice row: a wall between the eye and a slot pulls
            // the blade in to the contact instead of letting it hover through geometry.
            FHitResult Cover;
            if (GetWorld()->SweepSingleByChannel(Cover, Eye, Desired, FQuat::Identity,
                ECC_Visibility, FCollisionShape::MakeSphere(20.f), Query)) Desired = Cover.Location;
            Slot.Orb->SetActorLocationAndRotation(Desired, Facing + FRotator(0.f, 0.f, Slot.Roll));
        }
    }
    if (!bAnyPending) FinishOrbit(false);
}
