#include "M66FurnaceVisualComponent.h"
#include "M66IncineratorMonster.h"
#include "M66BreathTiming.h"
#include "../Skills/FireMagicArea.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

UM66FurnaceVisualComponent::UM66FurnaceVisualComponent()
{
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostPhysics;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Source(TEXT("/Engine/BasicShapes/Plane.Plane"));Plane=Source.Object;
}
void UM66FurnaceVisualComponent::BeginPlay()
{
    Super::BeginPlay();Monster=Cast<AM66IncineratorMonster>(GetOwner());
    if(!Monster||GetNetMode()==NM_DedicatedServer){SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteComponent(Monster->GetMesh());
    if(Monster->BreathGlowMaterial)
    {
        Glow=NewObject<UStaticMeshComponent>(Monster);Monster->AddInstanceComponent(Glow);
        Glow->SetStaticMesh(Plane);Glow->SetCollisionEnabled(ECollisionEnabled::NoCollision);Glow->SetCastShadow(false);
        Glow->SetCanEverAffectNavigation(false);Glow->SetReceivesDecals(false);Glow->SetVisibility(false);Glow->RegisterComponent();
        GlowMaterial=Glow->CreateDynamicMaterialInstance(0,Monster->BreathGlowMaterial);
    }
    Prepare();
}
void UM66FurnaceVisualComponent::Wake(){if(GetNetMode()!=NM_DedicatedServer)SetComponentTickEnabled(true);}
bool UM66FurnaceVisualComponent::IsReady() const
{return GetNetMode()==NM_DedicatedServer||(bPrepared&&Jet&&Monster&&Monster->BreathSystem&&Monster->BreathSystem->IsReadyToRun());}
void UM66FurnaceVisualComponent::Configure()
{
    const float Range=Monster->BreathRange;const FVector Domain(Range*1.2f+160.f,Range*.85f+160.f,Range*.5f+200.f);
    Jet->SetVariableVec3(TEXT("User.WorldSpaceSize"),Domain);Jet->SetVariableInt(TEXT("User.ResolutionMaxAxis"),80);
    Jet->SetVariableFloat(TEXT("User.CellSize"),float(Domain.GetMax())/80.f);Jet->SetVariableBool(TEXT("User.DrawBounds"),false);
    Jet->SetVariableFloat(TEXT("User.Range"),Range);Jet->SetVariableFloat(TEXT("User.HalfAngle"),FMath::DegreesToRadians(Monster->BreathArcDegrees*.5f));
    const FVector Bounds=Domain*.5f+FVector(64);Jet->SetSystemFixedBounds(FBox(-Bounds,Bounds));
}
bool UM66FurnaceVisualComponent::Prepare()
{
    if(bPrepared)return true;
    if(!Monster||!Monster->BreathSystem)return false;
#if WITH_EDITOR
    if(!bCompileRequested){Monster->BreathSystem->RequestCompile(false);bCompileRequested=true;}
    Monster->BreathSystem->PollForCompilationComplete(false);
    if(Monster->BreathSystem->HasOutstandingCompilationRequests(true))return false;
#endif
    if(!Monster->BreathSystem->IsReadyToRun())return false;
    if(!Jet)
    {
        Jet=NewObject<UNiagaraComponent>(Monster);Monster->AddInstanceComponent(Jet);
        Jet->SetAutoActivate(false);Jet->SetAutoDestroy(false);Jet->SetAsset(Monster->BreathSystem);
        Jet->SetVisibility(false);Jet->SetCastShadow(false);Jet->SetCanEverAffectNavigation(false);Configure();
        Jet->SetVariableFloat(TEXT("User.Strength"),0);Jet->SetVariableFloat(TEXT("User.EmissionScale"),0);
        Jet->RegisterComponent();Jet->AddTickPrerequisiteComponent(this);Jet->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);Jet->PrecachePSOs();return false;
    }
    if(Jet->IsPSOPrecaching())return false;
    Jet->Activate(false);if(!Jet->IsActive())return false;
    Jet->DeactivateImmediate();bPrepared=true;return true;
}
void UM66FurnaceVisualComponent::UpdateOcclusion(const FVector& Origin,const FQuat& Rotation)
{
    static const FName Rays[]={TEXT("User.Ray0"),TEXT("User.Ray1"),TEXT("User.Ray2"),TEXT("User.Ray3"),TEXT("User.Ray4"),TEXT("User.Ray5"),TEXT("User.Ray6"),TEXT("User.Ray7"),TEXT("User.Ray8")};
    static const FName Normals[]={TEXT("User.HitNormal0"),TEXT("User.HitNormal1"),TEXT("User.HitNormal2"),TEXT("User.HitNormal3"),TEXT("User.HitNormal4"),TEXT("User.HitNormal5"),TEXT("User.HitNormal6"),TEXT("User.HitNormal7"),TEXT("User.HitNormal8")};
    for(int32 I=0;I<9;++I)
    {
        const float Angle=FMath::DegreesToRadians(FMath::Lerp(-Monster->BreathArcDegrees*.5f,Monster->BreathArcDegrees*.5f,I/8.f));
        const FVector Direction=Rotation.RotateVector(FVector(FMath::Cos(Angle),FMath::Sin(Angle),0));FHitResult Hit;
        const bool Blocked=FireMagic::TraceSurface(Monster,Origin,Origin+Direction*Monster->BreathRange,Hit,true);
        Jet->SetVariableFloat(Rays[I],Blocked?FMath::Max(0.f,Hit.Distance-12.f):Monster->BreathRange);
        Jet->SetVariableVec3(Normals[I],Blocked?Hit.ImpactNormal.GetSafeNormal():-Direction);
    }
}
void UM66FurnaceVisualComponent::StopVisuals()
{
    if(Jet){Jet->DeactivateImmediate();Jet->SetVisibility(false);}
    if(Sound){Sound->Stop();Sound=nullptr;}
    if(Inhale){Inhale->Stop();Inhale=nullptr;}
    bJetStarted=false;TailLeft=0;
}
void UM66FurnaceVisualComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Dt,Type,Function);if(!Monster)return;
    const bool Ready=Prepare(),Active=Monster->IsBreathing();const float Age=Active?Monster->SweepAge():M66BreathTiming::End;
    if(Active&&Serial!=Monster->SweepSerial())
    {StopVisuals();Serial=Monster->SweepSerial();bSoundPlayed=bInhalePlayed=false;ProbeClock=0;}
    const float Mouth=Active?M66BreathTiming::Mouth(Age):0.f;
    if(!FMath::IsNearlyEqual(Mouth,LastMouth,.0001f))
    {Monster->GetMesh()->SetMorphTarget(Monster->BreathMouthMorph,Mouth);LastMouth=Mouth;}
    FVector Origin;FQuat Rotation;Monster->FurnaceBreathFrame(Origin,Rotation);
    if(Active&&Age<M66BreathTiming::Release&&!bInhalePlayed&&Monster->BreathInhaleSound)
    {Inhale=UGameplayStatics::SpawnSoundAtLocation(this,Monster->BreathInhaleSound,Origin,Rotation.Rotator(),.7f,1.f,Age);bInhalePlayed=true;}
    if(Inhale){Inhale->SetWorldLocation(Origin);if(!Active||Age>=M66BreathTiming::Release){Inhale->FadeOut(.06f,0);Inhale=nullptr;}}
    if(Glow)
    {
        Glow->SetVisibility(Active&&Age<M66BreathTiming::HoldEnd);
        Glow->SetWorldLocationAndRotation(Origin-Rotation.GetForwardVector()*12.f,FRotationMatrix::MakeFromZX(Rotation.GetForwardVector(),Rotation.GetRightVector()).ToQuat());
        Glow->SetWorldScale3D(FVector(.42,.70,1));
        if(GlowMaterial)GlowMaterial->SetScalarParameterValue(TEXT("Intensity"),Mouth*(Age<M66BreathTiming::Release?.3f:.9f)*(1-FMath::SmoothStep(M66BreathTiming::FireEnd,M66BreathTiming::HoldEnd,Age)));
    }
    const bool Fire=Active&&Age>=M66BreathTiming::Release&&Age<M66BreathTiming::FireEnd;
    // Audio follows the replicated release clock even while the local GPU
    // effect is compiling. A late observer seeks rather than replaying onset.
    if(Fire&&!bSoundPlayed&&Monster->BreathSound)
    {
        bSoundPlayed=true;
        const float Offset=M66BreathTiming::ReleaseSoundOffset(Age);
        if(Offset<Monster->BreathSound->GetDuration())
            Sound=UGameplayStatics::SpawnSoundAtLocation(this,Monster->BreathSound,Origin,Rotation.Rotator(),
                .75f,M66BreathTiming::ReleaseSoundPitch,Offset);
    }
    if(Sound)
    {
        Sound->SetWorldLocation(Origin);
        if(!Fire){Sound->FadeOut(.10f,0);Sound=nullptr;}
    }
    if(Fire&&Ready)
    {
        Jet->SetWorldLocationAndRotation(Origin+Rotation.GetForwardVector()*(Monster->BreathRange*.46f),Rotation);
        Jet->SetVariablePosition(TEXT("User.Origin"),Origin);Jet->SetVariableVec3(TEXT("User.Forward"),Rotation.GetForwardVector());
        Jet->SetVariableVec3(TEXT("User.Side"),Rotation.GetRightVector());Jet->SetVariableVec3(TEXT("User.Up"),Rotation.GetUpVector());
        ProbeClock-=Dt;if(ProbeClock<=0||!bJetStarted){UpdateOcclusion(Origin,Rotation);ProbeClock=.1f;}
        const float Pulse=.88f+.12f*FMath::Sin((Age-M66BreathTiming::Release)*PI*10.f);
        Jet->SetVariableFloat(TEXT("User.Strength"),1);Jet->SetVariableFloat(TEXT("User.EmissionScale"),Pulse);
        if(!bJetStarted){Jet->SetVisibility(true);Jet->Activate(true);bJetStarted=true;}
        else if(!Jet->IsActive())Jet->Activate(true);
        TailLeft=M66BreathTiming::Tail;
    }
    else if(bJetStarted&&Jet)
    {
        Jet->SetVariableFloat(TEXT("User.EmissionScale"),0);
        if(!Active&&bWasBreathing)TailLeft=FMath::Min(TailLeft,.15f);
        if(Active)TailLeft=FMath::Max(0.f,M66BreathTiming::Tail-(Age-M66BreathTiming::FireEnd));
        else TailLeft=FMath::Max(0.f,TailLeft-Dt);
        Jet->SetVariableFloat(TEXT("User.Strength"),TailLeft/M66BreathTiming::Tail);
        if(TailLeft<=0)StopVisuals();
    }
    bWasBreathing=Active;
    if(!Active&&!bJetStarted&&Ready)SetComponentTickEnabled(false);
}
void UM66FurnaceVisualComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    StopVisuals();if(Monster&&Monster->GetMesh())Monster->GetMesh()->SetMorphTarget(Monster->BreathMouthMorph,0);
    if(Jet)Jet->DestroyComponent();if(Glow)Glow->DestroyComponent();Super::EndPlay(Reason);
}
