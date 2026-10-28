#include "FPSImpactFXSubsystem.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

void UFPSImpactFXSubsystem::SpawnBleedingBurst(const FVector& Position,const FVector& Normal,int32 Stacks,AActor* BleedingActor)
{
    if(!bReady||Stacks<=0||GetWorld()->GetNetMode()==NM_DedicatedServer
        ||!ParticleMaterials.IsValidIndex(8)||!ParticleMaterials[7]||!ParticleMaterials[8])return;
    auto* View=Camera.Get();
    if(!IsValid(View))if(auto* PC=GetWorld()->GetFirstPlayerController();PC&&PC->IsLocalController())
        if(auto* Target=PC->GetViewTarget())
        {
            TInlineComponentArray<UCameraComponent*> Views(Target);
            for(auto* Candidate:Views)if(Candidate->IsActive()){View=Candidate;break;}
        }
    if(!IsValid(View))return;
    const FVector ToBurst=Position-View->GetComponentLocation();const float Distance=ToBurst.Size();
    if(Distance>6000.f||FVector::DotProduct(ToBurst,View->GetForwardVector())<-Distance*.1f)return;
    const double Now=GetWorld()->GetTimeSeconds();
    if(BudgetFrame!=GFrameCounter){BudgetFrame=GFrameCounter;FrameBursts=0;}
    BurstTokens=FMath::Min(8.f,BurstTokens+float(FMath::Max(0.,Now-LastBudgetTime))*40.f);LastBudgetTime=Now;
    if(FrameBursts>=8||BurstTokens<1.f)return;
    ++FrameBursts;BurstTokens-=1.f;Camera=View;
    const FVector Axis=(Normal.GetSafeNormal(SMALL_NUMBER,FVector::ForwardVector)+FVector(0,0,.22f)).GetSafeNormal();
    auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    const bool Near=Distance<2200.f;
    FHitResult Ground;
    bool bGroundQueried=false,bLanding=false,bStain=false;
    // Separate fixed ranges keep a bleeding pulse from overwriting gun-hit blood.
    for(int32 Group=8;Group>=7;--Group)
    {
        const bool Mist=Group==7;
        const int32 Requested=Mist?(Near?4:2):(Near?40+FMath::Min(Stacks-1,6)*4:Distance<4000.f?20:10);
        const int32 Wanted=Fluid?Fluid->AllocateDetail(Position,Requested,true):Requested;
        const int32 Start=Mist?232:264,End=Start+(Mist?BleedMistSlots:BleedDropSlots);
        int32 Added=0;
        for(int32 Slot=Start;Slot<End&&Added<Wanted&&ActiveParticles<MaxActiveParticles;++Slot)
        {
            if(Particles[Slot].Life>0.f)continue;
            auto& P=Particles[Slot];P=FParticle();P.Born=Now;
            P.Position=Position+Axis*3.f+BloodRandom.VRand()*BloodRandom.FRandRange(0.f,3.f);
            P.Variation=BloodRandom.FRand();P.Rotation.Roll=BloodRandom.FRandRange(-180.f,180.f);
            const FVector Direction=BloodRandom.VRandCone(Axis,FMath::DegreesToRadians(Mist?44.f:58.f));
            P.Color=FLinearColor(BloodRandom.FRandRange(.34f,.52f),.006f,.003f);
            if(Mist)
            {
                P.Velocity=Direction*BloodRandom.FRandRange(90.f,160.f)+FVector(0,0,24.f);
                P.Size=FVector(BloodRandom.FRandRange(18.f,28.f));P.Life=BloodRandom.FRandRange(.25f,.40f);
                P.Gravity=-75.f;P.Opacity=.58f;
            }
            else
            {
                P.Velocity=Direction*BloodRandom.FRandRange(210.f,430.f)+FVector(0,0,35.f);
                P.Size=FVector(BloodRandom.FRandRange(2.2f,4.5f),BloodRandom.FRandRange(5.f,11.f),1.f);
                if(Added<6){P.Size.X*=.65f;P.Size.Y*=1.8f;}
                P.Life=BloodRandom.FRandRange(.36f,.58f);P.Gravity=-980.f;P.Opacity=.94f;
                if(!bGroundQueried)
                {
                    bGroundQueried=true;
                    if(Distance<4500.f&&(!Fluid||Fluid->ReserveGeometryQueries(2)))
                    {
                        // Reuse the bounded floor query, ignoring the bleeding body.
                        const FVector SurfaceNormal=Normal.GetSafeNormal(SMALL_NUMBER,FVector::UpVector);
                        FHitResult Contact(BleedingActor,nullptr,Position,SurfaceNormal);
                        Contact.TraceStart=Position+SurfaceNormal;Contact.TraceEnd=Position;
                        bLanding=FindBloodLanding(Contact,View,Now,Ground);
                    }
                }
                if(bLanding)
                {
                    P.LandingPoint=Ground.ImpactPoint;P.LandingNormal=Ground.ImpactNormal;
                    P.bHasLandingPlane=true;
                    if(Added<6)
                    {
                        // Match the existing stain's arrival delay to Tick's damped
                        // trajectory, so a few heavy drops visibly reach the patch.
                        const float Height=FMath::Max(0.f,float(Position.Z-Ground.ImpactPoint.Z));
                        const float Flight=FMath::Clamp(FMath::Sqrt(2.f*Height/980.f),.24f,1.1f);
                        const float Travel=(1.f-FMath::Exp(-1.6f*Flight))/1.6f;
                        const FVector Spread=FVector::VectorPlaneProject(BloodRandom.VRand()*BloodRandom.FRandRange(2.f,12.f),P.LandingNormal);
                        const FVector Target=P.LandingPoint+Spread+P.LandingNormal*.5f;
                        P.Velocity=(Target-P.Position-FVector(0,0,P.Gravity*.5f*Flight*Flight))/Travel;
                        P.Life=Flight+.18f;P.Size.Y*=.75f;bStain=true;
                    }
                }
            }
            ++Added;++ActiveParticles;
        }
    }
    if(bStain)AddBloodStain(Ground,Position,Now);
}
