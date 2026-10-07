#include "M25BackElectricComponent.h"
#include "VortexCofferM25.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"

UM25BackElectricComponent::UM25BackElectricComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    ArcAsset = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Monsters/VortexCofferM25/VFX/NS_M25_BackElectric.NS_M25_BackElectric")));
    for (int32 I = 0; I < 9; ++I)
        TipNames[I] = FName(*FString::Printf(TEXT("socket_electric_%02d"), I));
}

void UM25BackElectricComponent::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode() == NM_DedicatedServer) return;
    auto* Character = Cast<ACharacter>(GetOwner());
    Body = Character ? Character->GetMesh() : nullptr;
    if (!Body) return;
    for (const FName Tip : TipNames)
        if (!Body->DoesSocketExist(Tip)) return;
    AddTickPrerequisiteComponent(Body);
    Cosmetic.Initialize(int32(FPlatformTime::Cycles()));
    LoadHandle = UAssetManager::GetStreamableManager().RequestAsyncLoad(ArcAsset.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this, [this]()
        {
            ArcSystem = ArcAsset.Get();
            if (ArcSystem && Body && bElectricEnabled)
            {
                CreatePresentation();
                SetComponentTickEnabled(true);
            }
        }));
}

void UM25BackElectricComponent::CreatePresentation()
{
    if (!Paths.IsEmpty()) return;
    AActor* Owner = GetOwner();
    for (int32 I = 0; I < LaneCount; ++I)
    {
        auto* Path = NewObject<USplineComponent>(Owner);
        Owner->AddInstanceComponent(Path);
        Path->SetupAttachment(Body);
        Path->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Path->SetCanEverAffectNavigation(false);
        Path->SetComponentTickEnabled(false);
        Path->ClearSplinePoints(false);
        for (int32 P = 0; P < PointCount; ++P)
        {
            Path->AddSplinePoint(FVector(P, 0, 0), ESplineCoordinateSpace::Local, false);
            Path->SetSplinePointType(P, ESplinePointType::Linear, false);
        }
        Path->UpdateSpline();
        Path->RegisterComponent();
        Paths.Add(Path);

        auto* Arc = NewObject<UNiagaraComponent>(Owner);
        Owner->AddInstanceComponent(Arc);
        Arc->SetupAttachment(Path);
        Arc->SetAutoActivate(false);
        Arc->SetAutoDestroy(false);
        Arc->SetAsset(ArcSystem);
        Arc->SetCastShadow(false);
        Arc->SetCanEverAffectNavigation(false);
        Arc->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        Arc->AddTickPrerequisiteComponent(this);
        Arc->RegisterComponent();
        Arc->SetVariableObject(TEXT("User.M25Spline"), Path);
        Arc->SetVariableFloat(TEXT("User.Progress"), 1.f);
        Arc->SetVariableFloat(TEXT("User.Jitter"), 0.f);
        Arc->SetVariableFloat(TEXT("User._ColorHue"), 0.f);
        Arc->SetVariableFloat(TEXT("User._Brightness"), 0.f);
        Arc->SetVariableFloat(TEXT("User._Width"), 1.f);
        Arc->SetVariableFloat(TEXT("User._DetailSpeed"), .0013f);
        Arc->SetVariableFloat(TEXT("User._DetailSpeedOffset"), 3.f);
        Arc->SetVariableFloat(TEXT("User.MainPowerSpeed"), 3.f);
        Arc->SetVariableBool(TEXT("User.AddDetail"), false);
        Arc->SetVariableBool(TEXT("User.AddMainPower"), true);
        // Local bounds cover all electrodes, raised bridges and short forks.
        Arc->SetSystemFixedBounds(FBox(FVector(-260,-260,-30), FVector(260,260,220)));
        Arcs.Add(Arc);
        Lanes[I].Delay = I == 0 ? 0.f : .08f + I * .09f;
    }
    BackLight = NewObject<UPointLightComponent>(Owner);
    Owner->AddInstanceComponent(BackLight);
    BackLight->SetupAttachment(Body, TipNames[0]);
    BackLight->SetRelativeLocation(FVector(0,0,8));
    BackLight->SetCastShadows(false);
    BackLight->SetIntensityUnits(ELightUnits::Lumens);
    BackLight->SetLightColor(FLinearColor(.22f,.48f,1.f));
    BackLight->SetIntensity(0.f);
    BackLight->SetAttenuationRadius(270.f);
    BackLight->SetSourceRadius(12.f);
    BackLight->SetIndirectLightingIntensity(0.f);
    BackLight->SetVolumetricScatteringIntensity(0.f);
    BackLight->RegisterComponent();

    if (auto* M = Cast<AVortexCofferM25>(Owner); M && M->CrackleSound)
    {
        CrackleVoice = NewObject<UAudioComponent>(Owner);
        Owner->AddInstanceComponent(CrackleVoice);
        CrackleVoice->SetupAttachment(Body, TipNames[0]);
        CrackleVoice->SetAutoActivate(false);
        CrackleVoice->bAutoDestroy = false;
        CrackleVoice->bAllowAnyoneToDestroyMe = false;
        CrackleVoice->SetSound(M->CrackleSound);
        CrackleVoice->bOverrideAttenuation = true;
        CrackleVoice->AttenuationOverrides.bAttenuate = true;
        CrackleVoice->AttenuationOverrides.bSpatialize = true;
        CrackleVoice->AttenuationOverrides.FalloffDistance = 1600.f;
        CrackleVoice->RegisterComponent();
    }
}

float UM25BackElectricComponent::ViewDistance() const
{
    float Closest = TNumericLimits<float>::Max();
    for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        const APlayerController* Player = It->Get();
        if (!Player || !Player->IsLocalController()) continue;
        FVector Eye; FRotator View;
        Player->GetPlayerViewPoint(Eye, View);
        Closest = FMath::Min(Closest, float(FVector::Dist(Eye, GetOwner()->GetActorLocation())));
    }
    return Closest;
}

void UM25BackElectricComponent::StartLane(int32 Index, float Distance)
{
    auto& Lane = Lanes[Index];
    // Adjacent electrode pairs stay above the back rather than cutting across
    // the sacs. Retain one path for the full discharge, including its afterglow.
    static constexpr int32 Pairs[][2] = {{3,0},{0,4},{3,1},{1,5},{5,7},{4,2},{2,6},{6,8},{1,2},{5,6}};
    // One overhead bridge remains readable while the side connections alternate.
    // The other lanes cover the left and right banks, including the rear electrodes.
    static constexpr int32 Banks[3][4] = {{0,1,8,9},{2,3,4,8},{5,6,7,9}};
    const int32 Bank = Index < 3 ? Index : 0;
    int32 Choice = Cosmetic.RandRange(0,3);
    int32 Pair = Banks[Bank][Choice];
    for (int32 Attempt = 0; Attempt < 10; ++Attempt)
    {
        bool Used = false;
        for (int32 J = 0; J < 3; ++J)
            if (J != Index && Lanes[J].Active && Lanes[J].From == Pairs[Pair][0] && Lanes[J].To == Pairs[Pair][1])
                Used = true;
        if (!Used) break;
        Choice = (Choice + 1) % 4;
        Pair = Banks[Bank][Choice];
    }
    Lane.From = Pairs[Pair][0]; Lane.To = Pairs[Pair][1];
    Lane.Age = 0.f; Lane.Alpha = 0.f;
    Lane.Seed = Cosmetic.FRandRange(0.f, 2.f*PI);
    Lane.Arch = Cosmetic.FRandRange(32.f, 46.f);
    Lane.Hold = Index == 0 ? Cosmetic.FRandRange(.85f,1.05f) : Cosmetic.FRandRange(.55f,.80f);
    Lane.Fade = Cosmetic.FRandRange(.20f,.32f);
    if (Index == 3)
    {
        Lane.Parent = Cosmetic.RandRange(0, 2);
        if (!Lanes[Lane.Parent].Active || Lanes[Lane.Parent].Age > Lanes[Lane.Parent].Hold)
        {
            Lane.Delay = .2f;
            return;
        }
        Lane.BranchT = Cosmetic.FRandRange(.35f,.72f);
        Lane.BranchOffset = FVector(Cosmetic.FRandRange(-19.f,19.f), Cosmetic.FRandRange(-14.f,14.f), Cosmetic.FRandRange(14.f,25.f));
        Lane.Hold = .18f; Lane.Fade = .22f; Lane.Arch = 5.f;
    }
    for (int32 P = 0; P < PointCount; ++P)
        Lane.Noise[P] = FVector(Cosmetic.FRandRange(-1.f,1.f), Cosmetic.FRandRange(-1.f,1.f), Cosmetic.FRandRange(-.3f,.8f));
    Lane.Active = true;
    UpdatePath(Index);
    // Modest distance compensation keeps the inner core above subpixel width.
    const float Readability = FMath::Lerp(1.f, 1.45f, FMath::SmoothStep(1200.f, 4200.f, Distance));
    Arcs[Index]->SetVariableFloat(TEXT("User._Width"), Width * Readability *
        (Index == 3 ? .60f : Cosmetic.FRandRange(.95f,1.10f)));
    Arcs[Index]->SetVariableFloat(TEXT("User._Brightness"), 0.f);
    Arcs[Index]->Activate(true);
}

void UM25BackElectricComponent::UpdatePath(int32 Index)
{
    auto& Lane = Lanes[Index];
    FVector A = Tips[Lane.From], B = Tips[Lane.To];
    if (Index == 3)
    {
        auto* ParentPath = Paths[Lane.Parent].Get();
        A = ParentPath->GetLocationAtDistanceAlongSpline(ParentPath->GetSplineLength()*Lane.BranchT, ESplineCoordinateSpace::Local);
        B = A + Lane.BranchOffset;
    }
    const FVector Delta = B-A;
    const float Jitter = FMath::Min(float(Delta.Size())*.09f, 7.f);
    FVector Side = FVector::CrossProduct(Delta.GetSafeNormal(), FVector::UpVector).GetSafeNormal();
    for (int32 P = 0; P < PointCount; ++P)
    {
        const float T = float(P)/(PointCount-1);
        const float Envelope = FMath::Sin(PI*T);
        const float Drift = FMath::Sin(Lane.Seed+T*8.f+Lane.Age*5.2f)*.7f;
        // Spatial shape changes continuously and goes exactly to zero at tips.
        const FVector Location = FMath::Lerp(A,B,T) + Envelope *
            (FVector::UpVector*Lane.Arch + Lane.Noise[P]*Jitter + Side*Drift);
        Paths[Index]->SetLocationAtSplinePoint(P, Location, ESplineCoordinateSpace::Local, false);
    }
    Paths[Index]->UpdateSpline();
}

void UM25BackElectricComponent::HidePresentation()
{
    if (!bVisible) return;
    for (int32 I = 0; I < Arcs.Num(); ++I)
    {
        Arcs[I]->DeactivateImmediate();
        Lanes[I].Active = false;
        Lanes[I].Delay = I == 0 ? 0.f : .06f + I*.09f;
        Lanes[I].Alpha = 0.f;
    }
    if (BackLight) BackLight->SetIntensity(0.f);
    if (CrackleVoice && CrackleVoice->IsPlaying()) CrackleVoice->Stop();
    bVisible = false;
}

void UM25BackElectricComponent::TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta, Type, Tick);
    if (!Body || Paths.Num() != LaneCount) return;
    const float Distance = ViewDistance();
    if (!bElectricEnabled || GetOwner()->IsHidden() || !Body->IsVisible() ||
        !Body->WasRecentlyRendered(.6f) || Distance >= MaxDrawDistance)
    {
        HidePresentation();
        SetComponentTickInterval(.2f);
        return;
    }
    if (!bVisible) Delta = 0.f;
    bVisible = true;
    SetComponentTickInterval(Distance > 1500.f ? 1.f/30.f : 0.f);
    for (int32 I = 0; I < 9; ++I)
        Tips[I] = Body->GetSocketTransform(TipNames[I], RTS_Component).GetLocation();
    const float DistanceAlpha = 1.f-FMath::SmoothStep(MaxDrawDistance*.78f, MaxDrawDistance, Distance);
    const int32 MainBudget = Distance > 3500.f ? 2 : 3;
    float Peak = 0.f;
    for (int32 I = 0; I < LaneCount; ++I)
    {
        auto& Lane = Lanes[I];
        const bool Allowed = I < MainBudget || (I == 3 && Distance < 1800.f);
        if (!Lane.Active)
        {
            Lane.Delay -= Delta;
            if (Allowed && Lane.Delay <= 0.f) StartLane(I, Distance);
        }
        if (!Lane.Active) continue;
        Lane.Age += Delta;
        if (I == 3 && !Lanes[Lane.Parent].Active)
            Lane.Age = Lane.Hold+Lane.Fade;
        if (Lane.Age >= Lane.Hold+Lane.Fade)
        {
            Lane.Active = false;
            Lane.Alpha = 0.f;
            Arcs[I]->DeactivateImmediate();
            Lane.Delay = I == 0 ? 0.f : Cosmetic.FRandRange(.06f,.22f) * (I == 3 ? 1.8f : 1.f);
            // Renew the main bridge immediately; no deliberate all-off interval.
            if (I == 0 && Allowed) StartLane(I, Distance);
            else continue;
        }
        UpdatePath(I);
        const float Attack = FMath::SmoothStep(0.f,.035f,Lane.Age);
        const float Cooling = FMath::Pow(1.f-FMath::Clamp((Lane.Age-Lane.Hold)/Lane.Fade,0.f,1.f),1.25f);
        const float Flicker = .88f+.08f*FMath::Sin(Lane.Age*31.f+Lane.Seed)+.04f*FMath::Sin(Lane.Age*53.f+Lane.Seed);
        Lane.Alpha = Attack*Cooling*DistanceAlpha;
        if (I == 3) Lane.Alpha *= Lanes[Lane.Parent].Alpha;
        Arcs[I]->SetVariableFloat(TEXT("User._Brightness"), Brightness*Lane.Alpha*Flicker*(I==3?.7f:1.f));
        Peak = FMath::Max(Peak, Lane.Alpha);
    }
    if (BackLight)
        BackLight->SetIntensity(150.f*Peak*(1.f-FMath::SmoothStep(1000.f,1800.f,Distance)));
    if (CrackleVoice)
    {
        CrackleVoice->SetVolumeMultiplier(FMath::Lerp(.3f, 1.f, Peak));
        if (!CrackleVoice->IsPlaying()) CrackleVoice->Play();
    }
}

void UM25BackElectricComponent::EndPlay(EEndPlayReason::Type Reason)
{
    if (LoadHandle) LoadHandle->CancelHandle();
    LoadHandle.Reset();
    HidePresentation();
    for (const auto& Arc : Arcs) if (Arc) { GetOwner()->RemoveInstanceComponent(Arc); Arc->DestroyComponent(); }
    Arcs.Reset();
    for (const auto& Path : Paths) if (Path) { GetOwner()->RemoveInstanceComponent(Path); Path->DestroyComponent(); }
    Paths.Reset();
    if (BackLight) { GetOwner()->RemoveInstanceComponent(BackLight); BackLight->DestroyComponent(); BackLight=nullptr; }
    if (CrackleVoice) { GetOwner()->RemoveInstanceComponent(CrackleVoice); CrackleVoice->DestroyComponent(); CrackleVoice=nullptr; }
    Super::EndPlay(Reason);
}

void UM25BackElectricComponent::StopDischarges()
{
    bElectricEnabled = false;
    if (LoadHandle.IsValid()) LoadHandle->CancelHandle();
    LoadHandle.Reset();
    HidePresentation();
    SetComponentTickEnabled(false);
}
