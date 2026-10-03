#include "SlagBlackMist.h"
#include "HundredEyedSlagMonster.h"
#include "SlagMistViewComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    TArray<TWeakObjectPtr<ASlagBlackMist>> Clouds;
    constexpr float DissipationSeconds = 1.5f;
    constexpr float RiseAcceleration = .45f;
    // One shared scale expands particle spread, puff size and exposure together.
    constexpr float CoverageScale = 1.5f;
    constexpr int32 MaximumHistory = 32;
    FVector PuffCenter(const FVector& Origin, const FVector& Drift, float Age)
    {
        return Origin + Drift * Age + FVector(0, 0, RiseAcceleration * Age * Age);
    }
}

ASlagBlackMist::ASlagBlackMist()
{
    bReplicates = true; bNetUseOwnerRelevancy = true;
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .1f;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("MistOrigin")); SetRootComponent(Root);
    Smoke = CreateDefaultSubobject<UNiagaraComponent>(TEXT("RollingSoot"));
    Smoke->SetupAttachment(Root); Smoke->SetAutoActivate(false);
    Smoke->SetCollisionEnabled(ECollisionEnabled::NoCollision); Smoke->SetCastShadow(false);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> FX(
        TEXT("/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/NS_SlagBodySmoke.NS_SlagBodySmoke"));
    Smoke->SetAsset(FX.Object);
}
void ASlagBlackMist::BeginPlay()
{
    Super::BeginPlay(); Clouds.AddUnique(this);
    if (GetOwner()) AddTickPrerequisiteActor(GetOwner());
    if (const auto* Monster = Cast<ACharacter>(GetOwner()))
        AddTickPrerequisiteComponent(Monster->GetMesh());
    Smoke->AddTickPrerequisiteActor(this);
    UpdateWake(); OnRep_Cloud();
}
void ASlagBlackMist::OnRep_Cloud()
{
    // An editor may have loaded this class before the smoke asset was authored.
    // Resolve a missing template once at activation, rather than caching null forever.
    if (!Smoke->GetAsset()) Smoke->SetAsset(LoadObject<UNiagaraSystem>(nullptr,
        TEXT("/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/NS_SlagBodySmoke.NS_SlagBodySmoke")));
    Smoke->SetVariableFloat(TEXT("User.Radius"), Radius * CoverageScale);
    Smoke->SetVariableFloat(TEXT("User.DiffusionSpeed"), GetDiffusionSpeed());
    Smoke->SetVariableFloat(TEXT("User.SmokeHoldTime"), SmokeLifetime);
    Smoke->SetVariableFloat(TEXT("User.SmokeLifetime"), SmokeLifetime + DissipationSeconds);
    Smoke->SetVariableFloat(TEXT("User.EmissionRate"), bEmitting ? 8.f : 0.f);
    if (GetNetMode() != NM_DedicatedServer && !Smoke->IsActive()) Smoke->Activate(true);
}
void ASlagBlackMist::EndPlay(const EEndPlayReason::Type Reason)
{
    Clouds.RemoveAll([this](const auto& Cloud){ return !Cloud.IsValid() || Cloud.Get() == this; });
    Smoke->DeactivateImmediate(); Super::EndPlay(Reason);
}
void ASlagBlackMist::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ASlagBlackMist, Radius); DOREPLIFETIME(ASlagBlackMist, BlindSeconds);
    DOREPLIFETIME(ASlagBlackMist, SmokeLifetime); DOREPLIFETIME(ASlagBlackMist, bEmitting);
}
void ASlagBlackMist::Gather(UWorld* World, TArray<ASlagBlackMist*>& Out)
{
    for (const auto& Weak : Clouds)
        if (auto* Cloud = Weak.Get(); IsValid(Cloud) && Cloud->GetWorld() == World)
            if (!Cloud->Trail.IsEmpty()) Out.Add(Cloud);
}
bool ASlagBlackMist::ContainsExposedEye(const FVector& Eye, const AActor* Player) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SlagMistExposure), false, this);
    Query.AddIgnoredActor(GetOwner()); Query.AddIgnoredActor(Player);
    const double Now = GetWorld()->GetTimeSeconds();
    const float Lifetime = SmokeLifetime + DissipationSeconds;
    for (const FWakePuff& Puff : Trail)
    {
        const float Age = Now - Puff.Born;
        if (Age < .18f || Age >= Lifetime) continue;
        const float N = FMath::Clamp(Age * GetDiffusionSpeed() / Lifetime, 0.f, 1.f);
        // Only the visible, dense core applies blindness; fading fringes do not.
        const float Fade = FMath::Clamp((Lifetime - Age) / DissipationSeconds, 0.f, 1.f);
        const float Core = Radius * CoverageScale * (.18f + .23f * FMath::Sqrt(N)) * FMath::Sqrt(Fade);
        for (const FVector& Origin : Puff.Origins)
        {
            const FVector Center = PuffCenter(Origin, Puff.Drift, Age);
            if (FVector::DistSquared(Eye, Center) > FMath::Square(Core)) continue;
            FHitResult Cover;
            if (!GetWorld()->LineTraceSingleByChannel(Cover, Center, Eye, ECC_Visibility, Query)) return true;
        }
    }
    return false;
}
void ASlagBlackMist::UpdateWake()
{
    const double Now = GetWorld()->GetTimeSeconds();
    const float Lifetime = SmokeLifetime + DissipationSeconds;
    Trail.RemoveAllSwap([&](const FWakePuff& Puff){ return Now - Puff.Born >= Lifetime; });
    if (bEmitting)
    {
        // Animated body locations affect new smoke only. Old particles retain
        // their birth positions and rise independently of movement or facing.
        static const FName Origins[] = {TEXT("User.EmitOrigin0"), TEXT("User.EmitOrigin1"), TEXT("User.EmitOrigin2")};
        FWakePuff NewPuff;
        GetEmissionSources(NewPuff.Origins, NewPuff.Drift); NewPuff.Born = Now;
        for (int32 I = 0; I < 3; ++I)
        {
            Smoke->SetVariablePosition(Origins[I], NewPuff.Origins[I]);
        }
        Smoke->SetVariableVec3(TEXT("User.EmitDrift"), NewPuff.Drift);
        if (Now >= NextWake)
        {
            // Three body origins per 0.3 s group cover the full 9.5 s life.
            if (Trail.Num() == MaximumHistory) Trail.RemoveAt(0);
            Trail.Add(NewPuff); NextWake = Now + .3;
        }
    }
    FBox WorldBounds(ForceInit);
    for (const FWakePuff& Puff : Trail)
    {
        for (const FVector& Origin : Puff.Origins)
            WorldBounds += FBox::BuildAABB(PuffCenter(Origin, Puff.Drift, float(Now - Puff.Born)), FVector(Radius * CoverageScale));
    }
    if (WorldBounds.IsValid)
        Smoke->SetSystemFixedBounds(WorldBounds.TransformBy(Smoke->GetComponentTransform().ToInverseMatrixWithScale()));
}
void ASlagBlackMist::GetEmissionSources(FVector (&Origins)[3], FVector& Drift) const
{
    const auto* Monster = Cast<AHundredEyedSlagMonster>(GetOwner());
    const auto* Mesh = Monster ? Monster->GetMesh() : nullptr;
    static const FName Bones[] = {TEXT("carapace"), TEXT("shell_L"), TEXT("shell_R")};
    const FVector Offsets[] = {FVector(-4,0,8), FVector(0,12,18), FVector(0,-12,18)};
    for (int32 I=0; I<3; ++I)
        Origins[I] = Mesh && Mesh->GetBoneIndex(Bones[I]) != INDEX_NONE
            ? Mesh->GetSocketLocation(Bones[I]) + Monster->GetActorTransform().TransformVectorNoScale(Offsets[I])
            : GetActorLocation();
    Drift = FVector(4,-3,18);
}
bool ASlagBlackMist::ShouldEmit() const
{
    const auto* Monster = Cast<AHundredEyedSlagMonster>(GetOwner());
    return IsValid(Monster) && !Monster->Dead();
}
void ASlagBlackMist::StopEmission()
{
    if (!bEmitting) return;
    bEmitting = false;
    DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
    Smoke->SetVariableFloat(TEXT("User.EmissionRate"), 0.f);
    // Keep simulation alive so emitted particles finish dispersing naturally.
    SetLifeSpan(SmokeLifetime + DissipationSeconds);
    if (HasAuthority()) ForceNetUpdate();
}
void ASlagBlackMist::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!ShouldEmit()) StopEmission();
    UpdateWake();
    // Each pawn owns one post-process layer, even with several monsters/clouds.
    // A new possession/respawn gets its own component, without altering player defaults.
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PC = It->Get(); PC && PC->GetPawn())
            if (auto* View = USlagMistViewComponent::GetOrAdd(PC->GetPawn())) View->SetComponentTickEnabled(true);
}
