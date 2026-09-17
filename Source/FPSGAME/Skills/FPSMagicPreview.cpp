#include "FPSMagicPreview.h"

#include "../Monsters/MonsterCombatComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/LineBatchComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"

// Live tuning while the user dials the drop by eye; the per-spell value stays in skills.json.
static TAutoConsoleVariable<float> MagicGravityScale(TEXT("fps.Magic.GravityScale"),1.f,
    TEXT("Multiplier on the configured projectile-spell gravity (0 = straight flight)."));
// Dash rhythm of the trajectory preview, measured along the path so the breaks stay evenly spaced.
static TAutoConsoleVariable<float> MagicPreviewDashCM(TEXT("fps.Magic.PreviewDashCM"),45.f,
    TEXT("Length of one dashed segment of the trajectory preview, in cm along the path."));
static TAutoConsoleVariable<float> MagicPreviewGapCM(TEXT("fps.Magic.PreviewGapCM"),30.f,
    TEXT("Break between dashed segments of the trajectory preview, in cm along the path."));

FLinearColor FPSMagicPreview::LineColor()
{ return FLinearColor(.95f,.12f,.08f,1.f); }

float FPSMagicPreview::GravityScale()
{ return FMath::Max(0.f,MagicGravityScale.GetValueOnGameThread()); }

FVector FPSMagicPreview::AimPoint(const APawn* Shooter,const AActor* Ignore)
{
    if(!Shooter||!Shooter->GetWorld())return FVector::ZeroVector;
    const auto* Camera=Shooter->FindComponentByClass<UCameraComponent>();
    const FVector Eye=Camera?Camera->GetComponentLocation():Shooter->GetPawnViewLocation();
    const FVector Forward=Camera?Camera->GetForwardVector():Shooter->GetActorForwardVector();
    const FVector End=Eye+Forward*20000;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MagicAimPreview),true,Shooter);
    if(Ignore)Query.AddIgnoredActor(Ignore);
    FHitResult Hit;
    Shooter->GetWorld()->LineTraceSingleByChannel(Hit,Eye,End,ECC_Visibility,Query);
    return Hit.bBlockingHit?Hit.ImpactPoint:End;
}

bool FPSMagicPreview::SweepSegment(const APawn* Shooter,const AActor* Ignore,const FVector& Start,
    const FVector& End,float SweepRadius,FVector& OutEnd)
{
    OutEnd=End;
    if(!Shooter||!Shooter->GetWorld())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MagicAimPreviewTrace),false,Shooter);
    if(Ignore)Query.AddIgnoredActor(Ignore);
    FHitResult Hit;
    // A body that is already down must not consume the projectile, so it is skipped and the
    // sweep continues; walls and living targets end the segment at their contact point.
    for(int32 Pass=0;Pass<8;++Pass)
    {
        if(!Shooter->GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(SweepRadius),Query))break;
        const auto* Blocking=IsValid(Hit.GetActor())?Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Blocking||!Blocking->IsDead()){OutEnd=Hit.ImpactPoint;return true;}
        Query.AddIgnoredActor(Hit.GetActor());
    }
    return false;
}

void FPSMagicPreview::SamplePath(const APawn* Shooter,const AActor* Ignore,const FVector& Start,
    const FVector& LaunchVelocity,float Gravity,float MaxDistance,float SweepRadius,TArray<FVector>& OutPoints)
{
    OutPoints.Reset();
    OutPoints.Add(Start);
    const FVector Acceleration(0,0,-FMath::Max(0.f,Gravity));
    FVector Previous=Start;
    float Travelled=0.f;
    for(int32 Step=1;Step<=MaxPathPoints&&Travelled<MaxDistance;++Step)
    {
        // Same ballistic integration the flight uses, so the drawn arc is the real trajectory.
        const float T=Step*StepSeconds;
        const FVector Next=Start+LaunchVelocity*T+.5f*Acceleration*T*T;
        FVector End;
        if(SweepSegment(Shooter,Ignore,Previous,Next,SweepRadius,End)){OutPoints.Add(End);return;}
        Travelled+=FVector::Distance(Previous,Next);
        Previous=Next;
        OutPoints.Add(Next);
    }
}

void FPSMagicPreview::BeginRefresh(TObjectPtr<ULineBatchComponent>& Lines,AActor* Owner)
{
    if(!Lines)
    {
        if(!Owner)return;
        Lines=NewObject<ULineBatchComponent>(Owner,TEXT("MagicAimPreviewLines"));
        Owner->AddInstanceComponent(Lines);Lines->RegisterComponent();
    }
    // Persistent lines are dropped here, so a refresh always shows exactly this frame's geometry.
    Lines->Flush();
}

void FPSMagicPreview::DrawPath(TObjectPtr<ULineBatchComponent>& Lines,const TArray<FVector>& Points)
{
    if(!Lines||Points.Num()<2)return;
    const FLinearColor Color=LineColor();
    const float Dash=FMath::Max(1.f,MagicPreviewDashCM.GetValueOnGameThread());
    const float Gap=FMath::Max(1.f,MagicPreviewGapCM.GetValueOnGameThread());
    float Total=0.f;
    for(int32 I=1;I<Points.Num();++I)Total+=FVector::Distance(Points[I-1],Points[I]);
    if(Total<=UE_KINDA_SMALL_NUMBER)return;
    // Walk the whole path in one pass so the dash rhythm and the near-end fade both run along the
    // arc instead of restarting per sampled segment; that keeps the breaks evenly spaced.
    float Travelled=0.f,Phase=0.f;
    bool bDash=true;
    for(int32 I=1;I<Points.Num();++I)
    {
        const FVector Start=Points[I-1],End=Points[I];
        const float Length=FVector::Distance(Start,End);
        if(Length<=UE_KINDA_SMALL_NUMBER)continue;
        const FVector Step=(End-Start)/Length;
        float Consumed=0.f;
        while(Consumed<Length-UE_KINDA_SMALL_NUMBER)
        {
            const float PhaseLength=bDash?Dash:Gap;
            const float Piece=FMath::Min(PhaseLength-Phase,Length-Consumed);
            if(bDash)
            {
                // Only the end touching the spell is softened. Thick batched lines composite
                // with SE_BLEND_AlphaBlend (Src.rgb*Src.a + Dst.rgb*(1-Src.a)), so the fade
                // must ride on alpha while RGB stays full strength: pressing RGB at alpha 1
                // paints opaque dark red over the background, which reads as a shadow band
                // instead of a fade (2026-09-17 round 3 tried exactly that).
                const float Progress=FMath::Clamp((Travelled+Consumed)/Total,0.f,1.f);
                const float Fade=Progress<FadeInFraction?FMath::Clamp(Progress/FadeInFraction,0.f,1.f):1.f;
                Lines->DrawLine(Start+Step*Consumed,Start+Step*(Consumed+Piece),
                    FLinearColor(Color.R,Color.G,Color.B,Color.A*Fade),
                    0,LineThickness*FMath::Lerp(.3f,1.f,Fade),0.f);
            }
            Consumed+=Piece;Phase+=Piece;
            if(Phase>=PhaseLength-UE_KINDA_SMALL_NUMBER){Phase=0.f;bDash=!bDash;}
        }
        Travelled+=Length;
    }
}

void FPSMagicPreview::Clear(ULineBatchComponent* Lines)
{ if(Lines)Lines->Flush(); }
