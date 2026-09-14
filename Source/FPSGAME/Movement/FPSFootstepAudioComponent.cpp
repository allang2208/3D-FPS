#include "FPSFootstepAudioComponent.h"
#include "AutoFootstepEffectContext.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Materials/MaterialInterface.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "PhysicsEngine/PhysicsSettings.h"
#include "Sound/SoundBase.h"
#include "EngineUtils.h"
#include "../WorldGeneration/TemperateHillsWorld.h"

UFPSFootstepAudioComponent::UFPSFootstepAudioComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickInterval = 1.f / 30.f;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UFPSFootstepAudioComponent::BeginPlay()
{
    Super::BeginPlay();
    Context = NewObject<UAutoFootstepEffectContext>(this);
    auto Add = [&](FName Name, std::initializer_list<const TCHAR*> Files)
    {
        FFPSFootstepBank& Bank = Banks.FindOrAdd(Name);
        if (!Bank.Sounds.IsEmpty()) return;
        for (const TCHAR* File : Files)
            if (USoundBase* Sound = LoadObject<USoundBase>(nullptr, *FString::Printf(TEXT("/Game/Audio/FreeFootsteps/S_%s"), File)))
                Bank.Sounds.Add(Sound);
    };
    Add(TEXT("Stone"), {TEXT("stone01")});
    Add(TEXT("Wood"), {TEXT("wood01"), TEXT("wood02"), TEXT("wood03")});
    Add(TEXT("Grass"), {TEXT("mud02")});
    Add(TEXT("Dirt"), {TEXT("mud02")});
    Add(TEXT("Gravel"), {TEXT("gravel")});
    Add(TEXT("Water"), {TEXT("splash1"), TEXT("splash2")});
    Add(TEXT("DeepWater"), {TEXT("splash1_deep"), TEXT("splash2_deep")});
}

void UFPSFootstepAudioComponent::Play(FName Name, const FVector& Position, float Gain)
{
    FFPSFootstepBank* Bank = Banks.Find(Name);
    if (!Bank || Bank->Sounds.IsEmpty() || !Context) return;
    int32 Index = FMath::RandRange(0, Bank->Sounds.Num()-1);
    if (Bank->Sounds.Num()>1 && Index==Bank->Last)
        Index=(Index+FMath::RandRange(1,Bank->Sounds.Num()-1))%Bank->Sounds.Num();
    Bank->Last=Index;
    // All samples are retained by Banks, so AutoFootstep takes its synchronous loaded path.
    FAutoFootstepEffect& Effect=Context->EffectsBySurfaceType.FindOrAdd(SurfaceType_Default);
    Effect.Sound=Bank->Sounds[Index].Get();
    FAutoFootstepSoundParams Params;
    Params.VolumeMultiplier=Volume*Gain*FMath::FRandRange(.94f,1.0f);
    Params.PitchMultiplier=FMath::FRandRange(.96f,1.04f);
    Context->PlayEffectBySurfaceType(this,SurfaceType_Default,Position,FRotator::ZeroRotator,FAutoFootstepNiagaraParams(),Params);
}

FName UFPSFootstepAudioComponent::GroundBank(const FHitResult& Hit) const
{
    if (Hit.PhysMaterial.IsValid())
    {
        for (const FPhysicalSurfaceName& Surface : UPhysicsSettings::Get()->PhysicalSurfaces)
            if (Surface.Type==Hit.PhysMaterial->SurfaceType && Banks.Contains(Surface.Name))
                return Surface.Name;
    }
    FString Name=Hit.PhysMaterial.IsValid()?Hit.PhysMaterial->GetName():TEXT("");
    if (const UPrimitiveComponent* C=Hit.GetComponent())
    {
        Name+=C->GetName();
        if (C->GetMaterial(0)) Name+=C->GetMaterial(0)->GetPathName();
        for (FName Tag:C->ComponentTags) Name+=Tag.ToString();
    }
    Name=Name.ToLower();
    if(Name.Contains(TEXT("wood"))||Name.Contains(TEXT("timber")))return TEXT("Wood");
    if(Name.Contains(TEXT("gravel"))||Name.Contains(TEXT("rock")))return TEXT("Gravel");
    if(Name.Contains(TEXT("mud"))||Name.Contains(TEXT("dirt"))||Name.Contains(TEXT("soil")))return TEXT("Dirt");
    if(Name.Contains(TEXT("grass"))||Name.Contains(TEXT("leaves"))||Hit.GetActor()==Hills.Get())return TEXT("Grass");
    return TEXT("Stone");
}

float UFPSFootstepAudioComponent::GetStepDistanceCm(const ACharacter* Pawn) const
{
    const float Speed = Pawn->GetVelocity().Size2D();
    return FMath::Max(1.f, Pawn->bIsCrouched ? CrouchStrideCm
        : FMath::Lerp(WalkStrideCm, RunStrideCm, FMath::Clamp((Speed - 300.f) / 350.f, 0.f, 1.f)));
}

float UFPSFootstepAudioComponent::GetStridePhaseRadians() const
{
    const ACharacter* Pawn = Cast<ACharacter>(GetOwner());
    if (!Pawn || !bInitialized) return 0.f;
    const float PendingTravel = FVector::Dist2D(Pawn->GetActorLocation(), Previous);
    if (PendingTravel > 500.f) return 0.f; // Same teleport boundary as the audio clock.
    const float Steps = (bAlternateStep ? 1.f : 0.f)
        + (Distance + PendingTravel) / GetStepDistanceCm(Pawn);
    return FMath::Fmod(PI * Steps, 2.f * PI);
}

void UFPSFootstepAudioComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Dt,Type,Fn);
    ACharacter* Pawn=Cast<ACharacter>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled())return;
    UCharacterMovementComponent* Move=Pawn->GetCharacterMovement();
    if(!Move)return;
    const FVector P=Pawn->GetActorLocation();
    const FVector Feet=P-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    FindWorldCountdown-=Dt;
    if(!Hills.IsValid()&&FindWorldCountdown<=0)
    {
        FindWorldCountdown=2.f;
        for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
    }
    const auto River=Hills.IsValid()?Hills->SampleRiver(P.X,P.Y):TemperateRiver::FSample();
    const float WaterDepth=River.Distance<River.HalfWidth?FMath::Max(0.f,float(River.WaterZ-Feet.Z)):0.f;
    const bool Wet=WaterDepth>3.f;
    const bool Grounded=Move->IsMovingOnGround();
    const float Travel=FVector::Dist2D(P,Previous);
    if(!bInitialized||Travel>500.f)
    {
        bInitialized=true;Previous=P;Distance=0;bWasWet=Wet;bWasGrounded=Grounded;bAlternateStep=false;
        LastVerticalSpeed=Move->Velocity.Z;return;
    }
    Previous=P;
    const float Speed=Move->Velocity.Size2D();
    const bool Landed=Grounded&&!bWasGrounded&&LastVerticalSpeed< -200.f;
    if(Wet!=bWasWet)Play(TEXT("Water"),Feet, Wet?.9f:.45f);
    if(Landed)
    {
        Play(Wet?FName(TEXT("Water")):GroundBank(Move->CurrentFloor.HitResult),Feet,1.15f);
        Distance=0;
    }
    else if((Grounded||Move->IsSwimming()||Wet)&&Speed>15.f&&Travel>.1f)
    {
        Distance+=Travel;
        const float Stride=GetStepDistanceCm(Pawn);
        if(Distance>=Stride)
        {
            if (FMath::FloorToInt(Distance / Stride) % 2 != 0) bAlternateStep = !bAlternateStep;
            Distance=FMath::Fmod(Distance,Stride);
            const float Gain=Pawn->bIsCrouched?.42f:FMath::GetMappedRangeValueClamped(FVector2D(100,650),FVector2D(.65,1.15),Speed);
            if(Wet||Move->IsSwimming())
            {
                Play(WaterDepth>40.f||Move->IsSwimming()?TEXT("DeepWater"):TEXT("Water"),Feet,Gain);
                if(Grounded&&WaterDepth<25.f)Play(GroundBank(Move->CurrentFloor.HitResult),Feet,Gain*.25f);
            }
            else Play(GroundBank(Move->CurrentFloor.HitResult),Feet,Gain);
        }
    }
    else Distance=0;
    bWasWet=Wet;bWasGrounded=Grounded;LastVerticalSpeed=Move->Velocity.Z;
}
