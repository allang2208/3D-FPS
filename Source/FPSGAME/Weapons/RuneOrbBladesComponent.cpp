#include "RuneOrbBladesComponent.h"
#include "../Combat/FPSAttackQuery.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
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
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "SceneView.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
bool RuneBladeFixedObservation(const APawn* Pawn)
{
    const auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    return Body&&Body->IsFixedThirdPersonViewEnabled();
}

bool RuneBladeProjection(const APlayerController* PC,FSceneViewProjectionData& Projection)
{
    const auto* Local=PC?PC->GetLocalPlayer():nullptr;
    return Local&&Local->ViewportClient&&Local->ViewportClient->Viewport&&
        Local->GetProjectionData(Local->ViewportClient->Viewport,Projection);
}
}

URuneOrbBladesComponent::URuneOrbBladesComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    SetIsReplicatedByDefault(true);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> BladeAsset(
        TEXT("/Game/Weapons/RuneSpectralBlade20260927/SM_SpectralRuneBlade.SM_SpectralRuneBlade"));
    if (BladeAsset.Succeeded()) BladeMesh = BladeAsset.Object;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> StarfallAsset(
        TEXT("/Game/Weapons/AzureRunesword20260913/StarfallGuard20261030/SM_StarfallRuneBlade.SM_StarfallRuneBlade"));
    if (StarfallAsset.Succeeded()) StarfallBladeMesh = StarfallAsset.Object;
}

bool URuneOrbBladesComponent::SwordEquipped() const
{
    const auto* Model=Profile();const auto* Item=Model?Model->Equipped():nullptr;
    return Item&&!Model->ActiveProductionTool()&&Item->Definition==TEXT("ue_rune_sword");
}
UColdSteelStatusModel* URuneOrbBladesComponent::Profile() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player||!Player->GetGameInstance())return nullptr;
    if(Player->HasAuthority()&&!Player->IsLocallyControlled())return Player->GetNetShadowProfile();
    return Player->IsLocallyControlled()?Player->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}

bool URuneOrbBladesComponent::NoAbilityCooldown() const
{
    const auto* Model=Profile();return Model&&Model->HasNoAbilityCooldown();
}

float URuneOrbBladesComponent::BladeDamage(const UColdSteelStatusModel* Profile,double Coefficient,double GuardMagicMultiplier)
{
    const auto* Item = Profile->Equipped();
    // Blade finishes affect melee contacts, not the weapon input of this spell.
    // Re-evaluate with only that slot removed; keep runes, guards and all other
    // existing contributors, including the guard's once-only magic bonus below.
    const auto* Gunsmith=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    FGunsmithParts SpellParts=Gunsmith?Gunsmith->Installed(*Item):FGunsmithParts{};
    SpellParts.Remove(TEXT("blade_material"));
    const auto Stats = ColdSteelMelee::Evaluate(*Item, Profile,&SpellParts);
    // The weapon panel already contains this guard's bonus on AddedMagic.
    // Remove that factor from the input; the projectile applies it once to
    // its full magic hit, through the same damage-bonus channel as spells.
    const double Weapon = Stats.Damage - Stats.DamageParts.AddedMagic +
        Stats.DamageParts.AddedMagic / GuardMagicMultiplier;
    return FMath::FloorToFloat(float(Weapon + Profile->Derived(TEXT("matk"))) * float(Coefficient));
}

bool URuneOrbBladesComponent::CanUse() const
{
    const auto* Player = Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC = Player ? Cast<APlayerController>(Player->GetController()) : nullptr;
    const auto* Health = Player ? Player->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
    const auto* Build = PC ? PC->FindComponentByClass<UVoxelBuildComponent>() : nullptr;
    return Player && Player->IsLocallyControlled() && PC &&
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
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return;
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
    auto* Profile = this->Profile();
    if (!Profile || !Profile->Equipped()) return;
    const auto Modifiers=ColdSteelMelee::EquippedModifiers(Profile);
    ActiveBlastRadius=FMath::Max(0.f,float(Modifiers.RuneBladeBlastRadius));
    ActiveBladeMesh=ActiveBlastRadius>0.f?StarfallBladeMesh:BladeMesh;
    if(!ActiveBladeMesh)return;
    ActiveForwardDistance=ActiveBlastRadius>0.f?144.f:ForwardDistance;
    const float Extra=Modifiers.CooldownReduceSecondsPerHit;
    ActiveHitReduction=Extra>0.f?.5f+Extra:0.f;
    ActiveGuardMagicMultiplier=float(Modifiers.RuneBladeMagicDamage);
    if(GetNetMode()==NM_Client)ServerOrbitIntent(0,0,FVector::ZeroVector);
    FVector Eye, Forward, Right, Up;
    float TanVertical;
    if (!ViewBasis(Eye, Forward, Right, Up, TanVertical)) return;
    const double Coefficient=Modifiers.RuneBladeDamageMultiplier>0?Modifiers.RuneBladeDamageMultiplier:BladeDamageMultiplier;
    const float Damage = BladeDamage(Profile,Coefficient,Modifiers.RuneBladeMagicDamage);
    CooldownDuration = BaseCooldownDuration * float(Modifiers.SkillCooldown * Modifiers.RuneBladeCooldown);
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
    const int32 OriginalBladeCount=ActiveBladeCount;
    ActiveBladeCount+=FMath::Max(0,FMath::FloorToInt(float(Modifiers.RuneBladeCountAdd)));
    if(Modifiers.RuneBladeCountOverride>0)
        ActiveBladeCount=FMath::Max(1,FMath::FloorToInt(float(Modifiers.RuneBladeCountOverride)));
    bActive = true; Elapsed = 0.f; LastLaunchTime = -1.0; Slots.Reset();
    // View-space wing row, the ice spike's layout: even indices take the left wing so
    // the row stays symmetric and never crowds the right-handed melee weapon.
    for (int32 i = 0; i < ActiveBladeCount; ++i)
    {
        FBladeSlot Slot;
        Slot.Lateral = (i % 2 == 0 ? -1.f : 1.f) * (WingGap + float(i / 2) * WingSpacing);
        if(i>=OriginalBladeCount)
        {
            // Append left/right outside the existing row. An odd craft count
            // must not move its original slots or reverse the extra pair.
            const int32 AddedIndex=i-OriginalBladeCount;
            const bool bLeft=AddedIndex%2==0;
            const int32 WingCount=bLeft?(OriginalBladeCount+1)/2:OriginalBladeCount/2;
            Slot.Lateral=(bLeft?-1.f:1.f)*(WingGap+float(WingCount+AddedIndex/2)*WingSpacing);
        }
        Slot.Roll = i * 113.f;
        if(Modifiers.RuneBladeCountOverride>0) {Slot.Lateral=0.f;Slot.Roll=0.f;}
        Slot.SwayPhase = i * 0.5f;
        Slots.Add(MoveTemp(Slot));
    }
    const FVector Extent = ActiveBladeMesh->GetBounds().BoxExtent;
    const float VisibleHeight = FMath::Max(4.f, (ActiveForwardDistance - Extent.X) * TanVertical - FMath::Max(Extent.Y, Extent.Z));
    for (auto& Slot : Slots)
    {
        const FVector Position = Eye + Forward * ActiveForwardDistance + Right * Slot.Lateral + Up * VisibleHeight;
        // Tip (+X) faces away from the camera, matching the ice shard silhouette.
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Params.Owner = Character; Params.Instigator = Character;
        if (auto* Orb = GetWorld()->SpawnActor<ARuneOrbBlade>(Position, Forward.Rotation().Add(0.f, 0.f, Slot.Roll), Params))
        {
            Orb->Setup(this, Character, Damage, ActiveBladeMesh);
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
    if(!Character->IsLocallyControlled())Eye=Character->GetPawnViewLocation();
    const FRotationMatrix ViewBasis(Character->IsLocallyControlled()?Camera->GetComponentRotation():Character->GetBaseAimRotation());
    Forward = ViewBasis.GetUnitAxis(EAxis::X);
    Right = ViewBasis.GetUnitAxis(EAxis::Y);
    Up = ViewBasis.GetUnitAxis(EAxis::Z);
    // The player camera maintains vertical FOV, using its configured aspect to store horizontal FOV.
    TanVertical = FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView * .5f)) / FMath::Max(.1f, Camera->AspectRatio);
    return true;
}

bool URuneOrbBladesComponent::ResolveAimTarget(const FVector& LaunchOrigin,FVector& Target,FVector* ContactNormal) const
{
    if(ContactNormal)*ContactNormal=FVector::ZeroVector;
    const auto* Character=Cast<APawn>(GetOwner());
    const auto* PC=Character?Cast<APlayerController>(Character->GetController()):nullptr;
    if(!PC)return false;
    FVector Eye,Direction;
    if(RuneBladeFixedObservation(Character))
    {
        // This developer camera observes an independently controlled character.
        // Keep its physical aim contract; the HUD projects this target below.
        const auto* Camera=Character->FindComponentByClass<UCameraComponent>();
        if(!Camera)return false;
        Eye=Camera->GetComponentLocation();Direction=Camera->GetForwardVector();
    }
    else
    {
        FSceneViewProjectionData Projection;
        if(!RuneBladeProjection(PC,Projection))return false;
        const FIntRect& View=Projection.GetViewRect();
        const FVector2D Center=FVector2D(View.Min)+FVector2D(View.Size())*.5;
        // Use the same final rendered POV/projection as the HUD center, including
        // camera-manager shakes and the third-person camera's final location.
        FSceneView::DeprojectScreenToWorld(Center,Projection.GetConstrainedViewRect(),
            Projection.ComputeViewProjectionMatrix().InverseFast(),Eye,Direction);
    }
    // Converge at the reachable range when the center ray hits empty space.
    // Solve its intersection with the blade's travel sphere, not a 200 m target
    // that leaves the entire 16 m flight displaced from the reticle.
    const FVector Offset=LaunchOrigin-Eye;
    const double Along=FVector::DotProduct(Offset,Direction);
    const double AcrossSquared=FMath::Max(0.0,Offset.SizeSquared()-Along*Along);
    const double Range=FMath::Max(0.f,ActiveRangeCM);
    const double Reach=Along+FMath::Sqrt(FMath::Max(0.0,Range*Range-AcrossSquared));
    const FVector End=Eye+Direction*FMath::Clamp(Reach,1.0,20000.0);
    const auto* PhysicalCamera=Character->FindComponentByClass<UCameraComponent>();
    const FVector PhysicalEye=PhysicalCamera?PhysicalCamera->GetComponentLocation():Character->GetPawnViewLocation();
    // A pulled-back third-person view must not select scenery between its
    // camera and the player and ask a forward spell to fly behind its caster.
    const FVector AimStart=Eye+Direction*FMath::Max(0.0,FVector::DotProduct(PhysicalEye-Eye,Direction));
    FHitResult Aim;
    FFPSAttackQuery Query(SCENE_QUERY_STAT(RuneBladeAim),false,Character);
    Target=End;
    // Match flight collision: a corpse ignored by the projectile must not
    // attract the targeting ray and pull the blade away from a living target.
    for(int32 Pass=0;Pass<8;++Pass)
    {
        if(!RangedAttackQuery::LineTraceSingle(GetWorld(),GetOwner(),Aim,AimStart,End,ECC_Visibility,Query))break;
        const auto* Combat=IsValid(Aim.GetActor())?Aim.GetActor()->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Combat||!Combat->IsDead())
        {
            Target=Aim.ImpactPoint;
            if(ContactNormal)*ContactNormal=Aim.ImpactNormal.GetSafeNormal();
            break;
        }
        Query.AddIgnoredActor(Aim.GetActor());
    }
    return true;
}

bool URuneOrbBladesComponent::GetAimReticlePosition(FVector2D& NormalizedPosition) const
{
    NormalizedPosition=FVector2D(.5,.5);
    const auto* Character=Cast<APawn>(GetOwner());
    if(!RuneBladeFixedObservation(Character))return true;
    const auto* PC=Character?Cast<APlayerController>(Character->GetController()):nullptr;
    FSceneViewProjectionData Projection;
    if(!RuneBladeProjection(PC,Projection))return false;
    const ARuneOrbBlade* Ready=nullptr;
    for(const auto& Slot:Slots)
        if(!Slot.bLaunched&&Slot.Orb.IsValid()&&Slot.Orb->CanLaunch()){Ready=Slot.Orb.Get();break;}
    FVector Target;
    if(!Ready||!ResolveAimTarget(Ready->GetActorLocation(),Target))return false;
    FVector2D Pixel;
    if(!FSceneView::ProjectWorldToScreen(Target,Projection.GetConstrainedViewRect(),Projection.ComputeViewProjectionMatrix(),Pixel))return false;
    const FIntRect& View=Projection.GetViewRect();
    if(View.Width()<=0||View.Height()<=0)return false;
    NormalizedPosition=(Pixel-FVector2D(View.Min))/FVector2D(View.Size());
    return NormalizedPosition.X>=0&&NormalizedPosition.X<=1&&NormalizedPosition.Y>=0&&NormalizedPosition.Y<=1;
}

void URuneOrbBladesComponent::LaunchOne()
{
    // Contact delegates are rechecked: equipment/menu/death can change after G.
    if (!bActive || !CanUse() || PendingLaunches <= 0) { PendingLaunches = 0; return; }
    // A random still-hovering blade leaves the ring, like the 2D launcher.
    TArray<int32> Available;
    for (int32 i = 0; i < Slots.Num(); ++i)
        if (Slots[i].Orb.IsValid() && !Slots[i].bLaunched && Slots[i].Orb->CanLaunch()) Available.Add(i);
    if (Available.IsEmpty()) { PendingLaunches = 0; return; }
    const int32 Pick = Available[FMath::RandRange(0, Available.Num() - 1)];
    FVector Target,ContactNormal;
    if(!ResolveAimTarget(Slots[Pick].Orb->GetActorLocation(),Target,&ContactNormal))return;
    // Aim the sweep sphere's contact surface at the reticle, rather than its
    // center through that surface. This compensates near-range parallax while
    // preserving the ordinary/giant collision radii and all real obstruction.
    const auto* Pawn=CastChecked<APawn>(GetOwner());
    const auto* PhysicalCamera=Pawn->FindComponentByClass<UCameraComponent>();
    const FVector PhysicalEye=PhysicalCamera?PhysicalCamera->GetComponentLocation():Pawn->GetPawnViewLocation();
    const FVector ToContact=Target-PhysicalEye;
    const float Radius=Slots[Pick].Orb->CollisionRadiusCM();
    const FVector Compensation=ContactNormal*Radius;
    // Soften the offset inside two radii: keep it within half the eye-to-hit
    // distance so a grazing/overlapping surface cannot turn aim backwards.
    const double CompensationScale=FMath::Min(1.0,ToContact.Length()/(2.0*Radius));
    const FVector FlightTarget=Target+Compensation*CompensationScale;
    Slots[Pick].bLaunched = true;
    if(GetNetMode()==NM_Client)ServerOrbitIntent(1,Pick,FlightTarget);
    if (auto* Orb = Slots[Pick].Orb.Get()) Orb->Launch(FlightTarget);
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

void URuneOrbBladesComponent::InterruptPending(bool bGathering)
{
    bQueuedSummon=false;PendingLaunches=0;
    if(bGathering && bActive)FinishOrbit(false);
}

void URuneOrbBladesComponent::FinishOrbit(bool bCancelGesture)
{
    if(GetNetMode()==NM_Client&&bActive)ServerOrbitIntent(2,0,FVector::ZeroVector);
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

void URuneOrbBladesComponent::NotifyBladeResult(bool bKilled,float HitReduction)
{
    if(!GetOwner()->HasAuthority())return;
    // A gold kill is one hit reward, not a hit plus an additional kill reward.
    const float Seconds=HitReduction>0.f?HitReduction:(bKilled?.5f:0.f);
    if(Seconds<=0.f)return;
    if(auto* Model=Profile())Model->ReduceMagicCooldowns(Seconds);
    if(auto* Owner=Cast<APawn>(GetOwner());Owner&&!Owner->IsLocallyControlled())ClientBladeMagicCooldown(Seconds);
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
    if(Character&&!Character->HasAuthority()&&!Character->IsLocallyControlled())return;
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
    const FVector Extent = ActiveBladeMesh->GetBounds().BoxExtent;
    const float VisibleHeight = FMath::Max(4.f, (ActiveForwardDistance - Extent.X) * TanVertical - FMath::Max(Extent.Y, Extent.Z));
    const FRotator Facing = Forward.Rotation();
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
            // Prepared hover ignores world geometry unconditionally so stairs/walls never snag blades.
            const FVector Desired = Eye + Forward * ActiveForwardDistance
                + Right * (Slot.Lateral + FMath::Sin(Slot.SwayPhase * 2.0f) * 3.f)
                + Up * (VisibleHeight + SwayY);
            Slot.Orb->SetActorLocationAndRotation(Desired, Facing + FRotator(0.f, 0.f, Slot.Roll), false, nullptr, ETeleportType::TeleportPhysics);
        }
    }
    if (!bAnyPending) FinishOrbit(false);
}
