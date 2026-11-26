#include "TemperateHillsWorld.h"

#if !UE_BUILD_SHIPPING
#include "../Building/ColdSteelDoor.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/RectLightComponent.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

namespace ChapelReview
{
struct FCapture
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<AColdSteelDoor> Door;
    FVector Origin=FVector::ZeroVector;
    FQuat Heading=FQuat::Identity;
    FVector At(FVector Local) const { return Origin+Heading.RotateVector(Local); }
    double Scale=1.;
    FString Folder, Trace;
    int32 Stage=0;
    double Began=FPlatformTime::Seconds(),Next=0.;
    void Record(const FString& Message)
    {
        Trace+=Message+LINE_TERMINATOR;
        UE_LOG(LogTemp,Display,TEXT("CHAPEL_REVIEW %s"),*Message);
        FFileHelper::SaveStringToFile(Trace,*(Folder/TEXT("scene.txt")));
    }
    bool Tick(float)
    {
        UWorld* W=World.Get();
        if(!W)return false;
        const double Now=FPlatformTime::Seconds();
        if(Now-Began>600.){Record(TEXT("timeout"));FPlatformMisc::RequestExitWithStatus(false,1);return false;}
        if(Now<Next)return true;
        auto* PC=W->GetFirstPlayerController();
        if(!PC||!PC->GetPawn())return true;
        ATemperateHillsWorld* H=nullptr;
        for(TActorIterator<ATemperateHillsWorld> It(W);It;++It)H=*It;
        if(!H||!H->bReady)return true;
        if(!Camera.IsValid())
        {
            TInlineComponentArray<UInstancedStaticMeshComponent*> Parts(H);
            bool bFound=false;
            for(auto* C:Parts)
            {
                if(!C->GetName().StartsWith(TEXT("OldChapel_"))||!C->GetStaticMesh())continue;
                FTransform T;if(!C->GetInstanceTransform(0,T,true))continue;
                if(C->GetName()==TEXT("OldChapel_Foundation")){Origin=T.GetLocation();Heading=T.GetRotation();Scale=T.GetScale3D().X;bFound=true;}
                Record(FString::Printf(TEXT("%s count=%d world_bounds=%s...%s"),*C->GetName(),C->GetInstanceCount(),
                    *C->Bounds.GetBox().Min.ToString(),*C->Bounds.GetBox().Max.ToString()));
            }
            if(!bFound)return true;
            for(auto* Part:Parts)if(Part->GetName()==TEXT("OldChapel_YardPier")&&Part->GetInstanceCount()==6)
            {
                FTransform P[6];for(int32 J=0;J<6;++J)Part->GetInstanceTransform(J,P[J],true);
                const FVector A=Heading.UnrotateVector(P[0].GetLocation()-Origin),B=Heading.UnrotateVector(P[5].GetLocation()-Origin);
                Record(FString::Printf(TEXT("gate centre offset Y %.2f cm, post alignment X %.2f cm, base Z difference %.2f cm, post spacing %.2f cm, front wings %.2f / %.2f cm"),
                    (A.Y+B.Y)*.5,A.X-B.X,A.Z-B.Z,FVector::Dist2D(A,B),
                    FVector::Dist2D(P[0].GetLocation(),P[1].GetLocation()),FVector::Dist2D(P[5].GetLocation(),P[4].GetLocation())));
            }
            for(auto* Light:TInlineComponentArray<URectLightComponent*>(H))
                Record(FString::Printf(TEXT("window daylight position=%s lumens=%.0f shadows=%d"),
                    *(Light->GetComponentLocation()-Origin).ToCompactString(),Light->Intensity,Light->CastShadows));
            for(TActorIterator<AColdSteelDoor> It(W);It;++It)if(It->GetOwner()==H)Door=*It;
            Camera=W->SpawnActor<ACameraActor>();
            if(!Camera.IsValid()||!Door.IsValid()){Record(TEXT("missing camera or door"));FPlatformMisc::RequestExitWithStatus(false,1);return false;}
            PC->GetPawn()->SetActorHiddenInGame(true);
            if(auto* Ch=Cast<ACharacter>(PC->GetPawn()))Ch->GetCharacterMovement()->DisableMovement();
            if(auto* Viewport=W->GetGameViewport())Viewport->RemoveAllViewportWidgets();
            Record(FString::Printf(TEXT("floor=%s foundation scale=%.3f door scale=%s"),*Origin.ToString(),Scale,*Door->GetActorScale3D().ToString()));
        }
        static const TCHAR* Names[]={TEXT("Exterior"),TEXT("Interior"),TEXT("GateOpen"),TEXT("Plinth"),TEXT("Approach")};
        static const TCHAR* YardViews[]={TEXT("Yard"),TEXT("Interior"),TEXT("Entry"),TEXT("Wall"),TEXT("Window")};
        const bool bYard=FParse::Param(FCommandLine::Get(),TEXT("ChapelYardReview"));
        const TCHAR* const* Views=bYard?YardViews:Names;
        constexpr int32 NumViews=UE_ARRAY_COUNT(Names);
        const int32 I=Stage/2;
        if(I==NumViews)
        {
            if(!IFileManager::Get().FileExists(*(Folder/(FString(Views[NumViews-1])+TEXT(".png")))))return true;
            Record(TEXT("capture complete"));
            // Let normal map travel tear down the streamed hills scene while the renderer is still live.
            const FName Context=GEngine->GetWorldContextFromWorldChecked(W).ContextHandle;
            UGameplayStatics::OpenLevel(W,TEXT("/Engine/Maps/Entry"));
            FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Context](float)
            {
                const FWorldContext* Active=GEngine->GetWorldContextFromHandle(Context);
                if(!Active||!Active->World()||Active->World()->GetOutermost()->GetName()!=TEXT("/Engine/Maps/Entry"))return true;
                FPlatformMisc::RequestExitWithStatus(false,0);return false;
            }),2.f);
            return false;
        }
        const FVector Eyes[]={FVector(-2280,2030,205),FVector(-706,0,163),FVector(-1110,70,159),FVector(-1035,780,125),FVector(-1450,145,150)};
        const FVector Targets[]={FVector(-108,0,485),FVector(645,0,185),FVector(-495,0,120),FVector(-530,410,55),FVector(-845,0,62)};
        const float Fovs[]={58,89,66,67,70};
        const FString File=Folder/(FString(Views[I])+TEXT(".png"));
        if(Stage%2==0)
        {
            if(I>0&&!IFileManager::Get().FileExists(*(Folder/(FString(Views[I-1])+TEXT(".png")))))return true;
            FVector Eye=At(FVector(Eyes[I].X*Scale,Eyes[I].Y*Scale,Eyes[I].Z));
            if(I==0)Eye.Z=H->Height(Eye.X,Eye.Y)+205.;
            FVector Target=At(Targets[I]*Scale);
            if(bYard)
            {
                static const FVector Positions[]={FVector(-4250,3020,1650),FVector(-855,-58,163),FVector(-3150,0,172),FVector(-2440,420,112),FVector(-420,110,168)};
                static const FVector Looks[]={FVector(-130,0,215),FVector(630,35,204),FVector(-700,0,207),FVector(-2240,610,48),FVector(80,-420,239)};
                auto Place=[&](FVector Local,bool Exterior)
                {
                    FVector Point=At(Local);
                    if(Exterior)Point.Z=H->Height(Point.X,Point.Y)+Local.Z;
                    return Point;
                };
                const bool Outside=I==0||I==2||I==3;
                Eye=Place(Positions[I],Outside);
                Target=Place(Looks[I],Outside);
            }
            PC->GetPawn()->SetActorLocation(Eye+FVector(0,0,220),false,nullptr,ETeleportType::TeleportPhysics);
            Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());
            Camera->GetCameraComponent()->SetFieldOfView(bYard?(I==0?65.f:I==1?83.f:I==2?69.f:64.f):Fovs[I]);
            PC->SetViewTarget(Camera.Get());
            if(!bYard&&I==2)Record(FString::Printf(TEXT("door open accepted=%d"),Door->OpenDoorFrom(PC->GetPawn())));
            if(!bYard&&I==3)Door->CloseDoor();
            if(!bYard&&I==0)
            {
                FCollisionQueryParams Q;Q.AddIgnoredActor(PC->GetPawn());
                FHitResult Hit;
                bool Closed=W->LineTraceSingleByChannel(Hit,At(FVector(-990*Scale,0,130)),At(FVector(-580*Scale,0,130)),ECC_Visibility,Q);
                Record(FString::Printf(TEXT("closed entry trace hit=%s"),Closed?*GetNameSafe(Hit.GetActor()):TEXT("none")));
            }
            ++Stage;Next=Now+(I==0?52.:10.);return true;
        }
        if(!bYard&&I==2)
        {
            FCollisionQueryParams Q;Q.AddIgnoredActor(PC->GetPawn());
            auto Sweep=[&](FVector A,FVector B)
            {
                FHitResult Hit;
                const bool Block=W->SweepSingleByChannel(Hit,At(A),At(B),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(34,88),Q);
                Record(FString::Printf(TEXT("capsule34x88 from %s to %s blocked=%d component=%s"),*A.ToCompactString(),*B.ToCompactString(),Block,*GetNameSafe(Hit.GetComponent())));
            };
            Sweep(FVector(-901*Scale,0,95),FVector(-505*Scale,0,95));Sweep(FVector(-505*Scale,0,95),FVector(310*Scale,0,95));
            for(double X:{-1100.,-948.,-899.,-854.,-790.,-744.,-712.,320.,379.,430.,564.})
            {
                FHitResult Hit;
                const double Y=(X<0.?0.:60.)*Scale;
                const bool Found=W->LineTraceSingleByChannel(Hit,At(FVector(X*Scale,Y,85)),At(FVector(X*Scale,Y,-150)),ECC_Visibility,Q);
                Record(FString::Printf(TEXT("walking surface x=%.1f z=%.2f component=%s"),X*Scale,Found?Hit.ImpactPoint.Z-Origin.Z:-999.,*GetNameSafe(Hit.GetComponent())));
            }
            // Probe the exposed pad nose and the adjacent terrain independently for every pier.
            for(double X:{-754.,-400.,0.,400.,754.})for(double Side:{-1.,1.})
            {
                FHitResult Seat,Soil;
                const FVector Pad=At(FVector(X,Side*495.,0)*Scale),Toe=At(FVector(X,Side*512.,0)*Scale);
                W->LineTraceSingleByChannel(Seat,Pad+FVector(0,0,35),Pad-FVector(0,0,140),ECC_Visibility,Q);
                W->LineTraceSingleByChannel(Soil,Toe+FVector(0,0,35),Toe-FVector(0,0,140),ECC_Visibility,Q);
                Record(FString::Printf(TEXT("pier x=%.1f side=%.0f bearing=%s soil=%s exposed_cm=%.2f"),X*Scale,Side,
                    *GetNameSafe(Seat.GetComponent()),*GetNameSafe(Soil.GetComponent()),Seat.ImpactPoint.Z-Soil.ImpactPoint.Z));
            }
        }
        FScreenshotRequest::RequestScreenshot(File,false,false);Record(TEXT("screenshot ")+File);
        ++Stage;Next=Now+2.;return true;
    }
};
FAutoConsoleCommandWithWorld ReviewCommand(TEXT("fps.ReviewOldChapel"),TEXT("Capture the chapel in an isolated hills review process."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("ChapelReview")))return;
        auto State=MakeShared<FCapture>();State->World=W;FString Batch=TEXT("current");
        FParse::Value(FCommandLine::Get(),TEXT("ChapelPass="),Batch);
        State->Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("OldChapelReview")/FPaths::MakeValidFileName(Batch));
        IFileManager::Get().MakeDirectory(*State->Folder,true);
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([State](float Dt){return State->Tick(Dt);}),.25f);
    }));
}
#endif

