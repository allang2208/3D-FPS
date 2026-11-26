#include "GunAssemblyInteraction.h"
#include "WorkstationViewRestore.h"
#include "GunAssemblySystem.h"
#include "Misc/Crc.h"
#include "ForgeArmsMeshComponent.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWorld.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/GunAssemblyActionWidget.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundNodeWavePlayer.h"
#include "Sound/SoundWave.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "InputKeyEventArgs.h"
#include "UnrealClient.h"

namespace
{
const FString GAArms=TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7");
const FString GAGhost=TEXT("/Game/Building/GunWorkbench20260927/Assembly/M_AssemblyGhost");
const FString GASound=TEXT("/Game/Weapons/M4HK416Audio/S_HK416_MagSeat");
const FString GACalibrationSound=TEXT("/Game/Weapons/PKMLowpoly20260922/ChargeAudio35/S_PKM_ChargePullMove");
constexpr float GARotationStep=5.f,GARotationHoldDelay=.18f,GARotationSpeed=120.f;
FSoftObjectPath GAPath(const FString& P){return FSoftObjectPath(P+TEXT(".")+FPaths::GetCleanFilename(P));}
template<class T>T* GAResolve(const FString& P){return Cast<T>(GAPath(P).ResolveObject());}
FVector GAVector(const TArray<TSharedPtr<FJsonValue>>& V){return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());}
FQuat GAQuat(const TArray<TSharedPtr<FJsonValue>>& V){return FQuat(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber(),V[3]->AsNumber()).GetNormalized();}
}

AGunAssemblyInteraction::AGunAssemblyInteraction()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.bTickEvenWhenPaused=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("GunWorkbenchFrame"));
    CalibrationAudio=CreateDefaultSubobject<UAudioComponent>(TEXT("CalibrationFeedback"));CalibrationAudio->SetupAttachment(RootComponent);
    CalibrationAudio->bAutoActivate=false;CalibrationAudio->bAutoDestroy=false;CalibrationAudio->bStopWhenOwnerDestroyed=true;
    CalibrationAudio->bAllowSpatialization=false;CalibrationAudio->bIsUISound=false;CalibrationAudio->bCanPlayMultipleInstances=false;
    CalibrationAudio->SetVolumeMultiplier(.14f);CalibrationAudio->SetPitchMultiplier(.85f);
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("AssemblyCamera"));Camera->SetupAttachment(RootComponent);Camera->FieldOfView=65;
    Camera->bOverrideAspectRatioAxisConstraint=true;Camera->SetAspectRatioAxisConstraint(AspectRatio_MaintainXFOV);
    Body=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FixedReceiver"));Body->SetupAttachment(RootComponent);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Ghost=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TargetOutline"));Ghost->SetupAttachment(RootComponent);Ghost->SetCollisionEnabled(ECollisionEnabled::NoCollision);Ghost->SetCastShadow(false);Ghost->SetVisibility(false);
    Arms=CreateDefaultSubobject<UForgeArmsMeshComponent>(TEXT("V7AssemblyHands"));Arms->SetupAttachment(RootComponent);Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCastShadow(false);Arms->SetComponentTickEnabled(false);Arms->bReceivesDecals=false;
    SetActorHiddenInGame(true);
}
void AGunAssemblyInteraction::Prepare(APlayerController* Player,AVoxelBuildPrefabActor* Table,UColdSteelHUDWidget* OwnerHUD)
{
    PC=Player;Station=Table;HUD=OwnerHUD;SetOwner(Player);SetActorTransform(Table->Body()->GetComponentTransform());
    System=GetGameInstance()->GetSubsystem<UGunAssemblySystem>();const auto& R=System->Recipe();
    if(R.Id.IsNone()){Error=TEXT("当前工件的配方不可用，可在管理面板取消工件并查看返料");return;}
    if(!System->Job().Id.IsEmpty()&&System->Job().PartCount!=R.Parts.Num())
    {Error=TEXT("工件组件与配方不一致，可在管理面板取消工件并查看返料");return;}
    Camera->SetRelativeLocation(R.Camera);Camera->SetRelativeRotation((R.LookAt-R.Camera).Rotation());
    TArray<FSoftObjectPath> Assets={GAPath(R.BodyMesh),GAPath(GAArms),GAPath(GAGhost),GAPath(GASound),GAPath(GACalibrationSound)};
    for(const auto& P:R.Parts)Assets.Add(GAPath(P.Mesh));
    Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets,FStreamableDelegate::CreateUObject(this,&ThisClass::AssetsLoaded));
}
void AGunAssemblyInteraction::AssetsLoaded()
{
    const auto& R=System->Recipe();Body->SetStaticMesh(GAResolve<UStaticMesh>(R.BodyMesh));Body->SetRelativeLocation(R.BodyPosition);
    auto* ArmMesh=GAResolve<USkeletalMesh>(GAArms);auto* Material=GAResolve<UMaterialInterface>(GAGhost);
    if(!Body->GetStaticMesh()||!ArmMesh||!Material){Error=TEXT("拼装模型或手臂资源未就绪");return;}
    Arms->SetSkinnedAssetAndUpdate(ArmMesh,true);GhostMaterial=UMaterialInstanceDynamic::Create(Material,this);
    for(int32 I=0;I<R.Parts.Num();++I)
    {
        auto* Mesh=GAResolve<UStaticMesh>(R.Parts[I].Mesh);if(!Mesh){Error=TEXT("拼装组件资源未就绪");return;}
        auto* C=NewObject<UStaticMeshComponent>(this);AddInstanceComponent(C);C->SetupAttachment(RootComponent);
        C->SetStaticMesh(Mesh);C->SetMobility(EComponentMobility::Movable);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->RegisterComponent();Parts.Add(C);
        Positions.Add(R.Parts[I].Loose);Angles.Add(R.Parts[I].Angle);
    }
    ContactSound=GAResolve<USoundBase>(GASound);SetupHands();CacheWorkspace();
    if(auto* Wave=GAResolve<USoundWave>(GACalibrationSound))
    {
        // Instance-local loop: do not change the waveform or its use by the original gun.
        CalibrationLoop=NewObject<USoundCue>(this,NAME_None,RF_Transient);
        CalibrationLoop->SoundClassObject=Wave->SoundClassObject;CalibrationLoop->VolumeMultiplier=1.f;
        auto* Player=NewObject<USoundNodeWavePlayer>(CalibrationLoop,NAME_None,RF_Transient);
        Player->SetSoundWave(Wave);Player->bLooping=true;CalibrationLoop->FirstNode=Player;
        CalibrationLoop->Duration=INDEFINITELY_LOOPING_DURATION;CalibrationAudio->SetSound(CalibrationLoop);
    }
    bReady=bHandsReady&&!Parts.IsEmpty()&&Parts.Num()==R.Parts.Num();if(!bReady)Error=TEXT("装配抓握资源未就绪");
}
void AGunAssemblyInteraction::CacheWorkspace()
{
    const auto& R=System->Recipe();Workspace=FBox(ForceInit);DragBounds=FBox(ForceInit);
    Workspace+=Body->GetStaticMesh()->GetBoundingBox().ShiftBy(R.BodyPosition);
    for(int32 I=0;I<R.Parts.Num();++I)
    {
        const auto& Part=R.Parts[I];const FBox MeshBox=Parts[I]->GetStaticMesh()->GetBoundingBox();
        // Reserve the part's full rotation envelope, including off-centre source meshes.
        const FVector E=MeshBox.GetExtent()+MeshBox.GetCenter().GetAbs();
        const double Radius=FVector2D(E.X,E.Y).Size();const FVector Extent(Radius,Radius,E.Z);
        for(const FVector& Position:{Part.Loose,Part.Target})
        {Workspace+=FBox(Position-Extent,Position+Extent);DragBounds+=Position;}
    }
    Workspace=Workspace.ExpandBy(4.);DragBounds=DragBounds.ExpandBy(FMath::Max(12.f,R.PositionTolerance*2));
}
void AGunAssemblyInteraction::FrameWorkspace()
{
    if(!PC.IsValid()||!Workspace.IsValid||Dragged!=INDEX_NONE||Snapping!=INDEX_NONE)return;
    int32 W=0,H=0;PC->GetViewportSize(W,H);if(W<=0||H<=0||FramedViewport==FIntPoint(W,H))return;
    FramedViewport=FIntPoint(W,H);WorkspaceBottom=Prompt?Prompt->WorkspaceBottom(H):.6f;
    const auto& R=System->Recipe();const FVector Forward=(R.LookAt-R.Camera).GetSafeNormal();
    const FRotator ViewRotation=Forward.Rotation();
    const FVector Right=ViewRotation.RotateVector(FVector::RightVector),Up=ViewRotation.RotateVector(FVector::UpVector);
    const double TanX=FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView*.5)),TanY=TanX*H/W;
    const double CentreY=(.08+WorkspaceBottom)*.5;double Distance=FMath::Max(20.,(R.Camera-R.LookAt).Size());
    FVector Eye=R.Camera;
    // Fit once on entry/resize; the camera never follows a dragged part or a new install step.
    for(int32 Attempt=0;Attempt<64;++Attempt)
    {
        const FVector Focus=Workspace.GetCenter()-Up*((1.-2.*CentreY)*Distance*TanY);
        Eye=Focus-Forward*Distance;bool Fits=true;
        for(int32 Corner=0;Corner<8;++Corner)
        {
            const FVector V=FVector(Corner&1?Workspace.Max.X:Workspace.Min.X,Corner&2?Workspace.Max.Y:Workspace.Min.Y,Corner&4?Workspace.Max.Z:Workspace.Min.Z)-Eye;
            const double Depth=V|Forward;if(Depth<=1.){Fits=false;break;}
            const double X=.5+(V|Right)/(2.*Depth*TanX),Y=.5-(V|Up)/(2.*Depth*TanY);
            if(X<.06||X>.94||Y<.08||Y>WorkspaceBottom){Fits=false;break;}
        }
        if(Fits)break;Distance*=1.12;
    }
    Camera->SetRelativeLocation(Eye);Camera->SetRelativeRotation(ViewRotation);
}
bool AGunAssemblyInteraction::Ready(FString& Reason) const
{
    if(!Error.IsEmpty()){Reason=Error;return false;}
    if(!bReady){Reason=TEXT("正在准备真实组件与手臂…");return false;}
    if(!PC.IsValid()||!Station.IsValid()||Station->IsFalling()){Reason=TEXT("工作台已不可用");return false;}
    return true;
}
bool AGunAssemblyInteraction::Start(FString& Reason)
{
    if(!Ready(Reason))return false;
    if(System->Job().Id.IsEmpty())return System->Start(Reason);
    return System->Resume(Reason);
}
void AGunAssemblyInteraction::Enter()
{
    auto* Player=PC.Get();if(!Player)return;
    bRunning=true;WorkingPawn=Player->GetPawn();PreviousView=Player->GetViewTarget();bWasCursor=Player->bShowMouseCursor;
    ColdSteelWorkstationView::BeginIdle(this,WorkingPawn.Get());
    if(auto* Pawn=Cast<AFPSGAMECharacter>(WorkingPawn.Get())){Pawn->SuspendWeaponForMenu();Pawn->GetCharacterMovement()->StopMovementImmediately();}
    Player->FlushPressedKeys();Player->SetIgnoreMoveInput(true);Player->SetIgnoreLookInput(true);bInputLocked=true;
    Player->bShowMouseCursor=false;Player->SetInputMode(FInputModeGameOnly());
    if(WorkingPawn.IsValid()&&!Player->HiddenActors.Contains(WorkingPawn.Get())){Player->HiddenActors.Add(WorkingPawn.Get());bHiddenPawn=true;}
    for(int32 I=0;I<Parts.Num();++I)
    {if(System->Installed(I)){Positions[I]=System->Recipe().Parts[I].Target;Angles[I]=0;}else ResetLoose(I);}
    HandPosition=FVector(43,27,110);Clock=FinishRetryAt=0;
    CalibrationClock=System->Job().CalibrationTime;CalibrationSeed=FCrc::StrCrc32(*System->Job().Id);
    Prompt=CreateWidget<UGunAssemblyActionWidget>(Player);Prompt->AddToViewport(80);
    Prompt->Refresh(System,FString(),INDEX_NONE,false);FrameWorkspace();
    SetActorHiddenInGame(false);SetActorTickEnabled(true);Present(0);Player->SetViewTargetWithBlend(this,.35f,VTBlend_Cubic);
}
bool AGunAssemblyInteraction::CursorOnPlane(float Height,FVector& Local) const
{
    auto* Player=PC.Get();if(!Player)return false;
    int32 W=0,H=0;Player->GetViewportSize(W,H);FVector O,D;
    if(!Player->DeprojectScreenPositionToWorld(Aim.X*W,Aim.Y*H,O,D))return false;
    O=GetActorTransform().InverseTransformPosition(O);D=GetActorTransform().InverseTransformVector(D);
    if(FMath::Abs(D.Z)<.0001)return false;const double T=(Height-O.Z)/D.Z;if(T<0)return false;
    Local=O+D*T;return true;
}
bool AGunAssemblyInteraction::HandleInput(const FInputKeyEventArgs& E)
{
    if(!bRunning)return false;
    if(E.Key==EKeys::Q||E.Key==EKeys::E)
    {
        bool& Held=E.Key==EKeys::Q?bRotateLeft:bRotateRight;
        if(E.Event==IE_Released){Held=false;RotationDelayRemaining=GARotationHoldDelay;}
        else if(E.Event==IE_Pressed&&Dragged!=INDEX_NONE)
        {
            Held=true;RotationDelayRemaining=GARotationHoldDelay;
            if(bRotateLeft!=bRotateRight)Angles[Dragged]=FMath::UnwindDegrees(Angles[Dragged]+(bRotateRight?GARotationStep:-GARotationStep));
        }
        return true; // Tick owns held rotation; OS keyboard repeat never adds duplicate steps.
    }
    if(E.Key==EKeys::MouseScrollUp||E.Key==EKeys::MouseScrollDown)
    {
        if(Dragged!=INDEX_NONE&&(E.Event==IE_Pressed||E.Event==IE_Repeat))
            Angles[Dragged]=FMath::UnwindDegrees(Angles[Dragged]+(E.Key==EKeys::MouseScrollUp?GARotationStep:-GARotationStep));
        return true;
    }
    if(E.Key==EKeys::MouseX||E.Key==EKeys::MouseY)
    {
        int32 W=1,H=1;PC->GetViewportSize(W,H);
        if(E.Key==EKeys::MouseX)Aim.X=FMath::Clamp(Aim.X+E.AmountDepressed/FMath::Max(W,1),.015,.985);
        else Aim.Y=FMath::Clamp(Aim.Y-E.AmountDepressed/FMath::Max(H,1),.025,.78);
        return true;
    }
    if(E.Event==IE_Pressed)
    {
        if(E.Key==EKeys::Escape){Stop(true);return true;}
        if(E.Key==EKeys::Enter&&System->Job().bFinished){Stop(true);return true;}
        if(E.Key==EKeys::RightMouseButton&&Dragged!=INDEX_NONE){ResetLoose(Dragged);Dragged=INDEX_NONE;bHeld=false;return true;}
        if(E.Key==EKeys::Tab&&!System->Assembled()&&Dragged==INDEX_NONE)
        {
            for(int32 N=1;N<=Parts.Num();++N){const int32 I=(Hovered+N+Parts.Num())%Parts.Num();if(System->Installed(I))continue;
                FVector2D P;int32 W,H;PC->GetViewportSize(W,H);if(PC->ProjectWorldLocationToScreen(GetActorTransform().TransformPosition(Positions[I]),P))Aim=P/FVector2D(W,H);Hovered=I;break;}return true;
        }
        if(E.Key==EKeys::LeftMouseButton&&Snapping==INDEX_NONE&&Clock>.4f)
        {
            bHeld=true;
            if(!System->Assembled()&&Hovered!=INDEX_NONE&&!System->Installed(Hovered))
            {
                Dragged=Hovered;FVector P;DragOffset=FVector::ZeroVector;
                if(CursorOnPlane(System->Recipe().Parts[Dragged].Target.Z,P))DragOffset=Positions[Dragged]-P;
                DragOffset.Z=0;
                PlayContact(.85f);Feedback=System->Recipe().Parts[Dragged].Name+TEXT(" · 将零件圆心拖到明亮安装圈，旋转至 0°");FeedbackUntil=Clock+2;
            }
        }
    }
    if(E.Key==EKeys::LeftMouseButton&&E.Event==IE_Released){bHeld=false;UpdateCalibrationAudio(false,0.f);if(Dragged!=INDEX_NONE)Drop();}
    return true; // No fire, movement, hotbar or menu key can pass into gameplay.
}
void AGunAssemblyInteraction::ClearRotationInput()
{bRotateLeft=bRotateRight=false;RotationDelayRemaining=0;}
void AGunAssemblyInteraction::ResetLoose(int32 I)
{ClearRotationInput();Positions[I]=System->Recipe().Parts[I].Loose;Angles[I]=System->Recipe().Parts[I].Angle;}
void AGunAssemblyInteraction::Drop()
{
    ClearRotationInput();
    const int32 I=Dragged;Dragged=INDEX_NONE;const auto& P=System->Recipe().Parts[I];
    const float Distance=FVector2D(Positions[I]-P.Target).Size();
    if(System->Install(I,Distance,FMath::UnwindDegrees(Angles[I]),Feedback))
    {Snapping=I;SnapTime=0;SnapFrom=Positions[I];SnapAngle=Angles[I];bContactPlayed=false;}
    else ResetLoose(I);
    FeedbackUntil=Clock+2.2f;
}
void AGunAssemblyInteraction::Tick(float Dt)
{
    Super::Tick(Dt);if(!bRunning)return;
    const auto* World=Station.IsValid()?Cast<AVoxelBuildWorld>(Station->GetOwner()):nullptr;
    if(!PC.IsValid()||PC->GetPawn()!=WorkingPawn.Get()||!Station.IsValid()||Station->IsFalling()||!World||!World->HasPrefabAt(Station->AnchorCell())){Stop(false);return;}
    if(WorkingPawn.IsValid())if(const auto* Health=WorkingPawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead()){Stop(false);return;}
    auto* VP=GetWorld()->GetGameViewport();
    const bool Focused=VP&&VP->Viewport&&VP->Viewport->HasFocus()&&!GetWorld()->IsPaused();
    if(!Focused)
    {bHeld=false;StopCalibrationAudio();ClearRotationInput();if(Dragged!=INDEX_NONE){ResetLoose(Dragged);Dragged=INDEX_NONE;}Ghost->SetVisibility(false);return;}
    Clock+=Dt;FrameWorkspace();
    if(Snapping!=INDEX_NONE)
    {
        SnapTime+=Dt;const float A=FMath::SmoothStep(0.f,1.f,FMath::Clamp(SnapTime/.32f,0.f,1.f));
        Positions[Snapping]=FMath::Lerp(SnapFrom,System->Recipe().Parts[Snapping].Target,A);Angles[Snapping]=FMath::Lerp(SnapAngle,0.f,A);
        if(SnapTime>=.28f&&!bContactPlayed){PlayContact(1.15f);bContactPlayed=true;}
        if(SnapTime>=.32f)Snapping=INDEX_NONE;
    }
    if(Dragged!=INDEX_NONE)
    {
        if(bRotateLeft!=bRotateRight)
        {
            const float Step=FMath::Clamp(Dt,0.f,.1f),Wait=FMath::Min(Step,RotationDelayRemaining);
            RotationDelayRemaining-=Wait;
            Angles[Dragged]=FMath::UnwindDegrees(Angles[Dragged]+(bRotateRight?1.f:-1.f)*GARotationSpeed*(Step-Wait));
        }
        FVector P;const auto& Part=System->Recipe().Parts[Dragged];
        const float Height=Part.Target.Z;
        if(CursorOnPlane(Height,P)){P+=DragOffset;Positions[Dragged]=FVector(FMath::Clamp(P.X,DragBounds.Min.X,DragBounds.Max.X),FMath::Clamp(P.Y,DragBounds.Min.Y,DragBounds.Max.Y),Height);}
    }
    Hovered=INDEX_NONE;double Best=MAX_dbl;
    if(Dragged==INDEX_NONE&&!System->Assembled())for(int32 I=0;I<Parts.Num();++I)if(!System->Installed(I))
    {
        FVector P;if(!CursorOnPlane(Positions[I].Z,P))continue;
        const FVector D=FRotator(0,-Angles[I],0).RotateVector(P-Positions[I]);const auto& R=System->Recipe().Parts[I];
        const double Metric=FMath::Square(D.X/FMath::Max(3.5,R.Extent.X+1.5))+FMath::Square(D.Y/FMath::Max(3.5,R.Extent.Y+1.5));
        if(Metric<=1.35&&Metric<Best){Best=Metric;Hovered=I;}
    }
    if(System->Job().bFinished){PlayContact(.95f);Stop(true);return;}
    const float T=GetNetMode()==NM_Client?FMath::Max(CalibrationClock,System->Job().CalibrationTime):System->Job().CalibrationTime;
    int32 W=1,H=1;PC->GetViewportSize(W,H);
    const float Radius=GunAssemblyCalibration::Radius(T,CalibrationSeed);
    // Reserve the top instruction banner as well as the bottom panel, including the largest ring.
    const float Top=Prompt?Prompt->CalibrationTop(H):.08f;
    const float RadiusY=Radius*FMath::Min(W,H)/FMath::Max(1,H);
    const float Travel=FMath::Min(.05f,FMath::Max(0.f,(WorkspaceBottom-Top)*.5f-RadiusY-.01f));
    CalibrationTarget=FVector2D(.5+.105*FMath::Sin(T*.9),(Top+WorkspaceBottom)*.5f+Travel*FMath::Sin(T*1.3+.4));
    const float CalibrationError=((Aim-CalibrationTarget)*FVector2D(W,H)).Size()/FMath::Max(1.f,FMath::Min(W,H)*Radius);
    const bool Inside=System->Assembled()&&Snapping==INDEX_NONE&&bHeld&&CalibrationError<=1&&GunAssemblyCalibration::Following(T);
    UpdateCalibrationAudio(Inside,Dt);
    if(System->Assembled()&&Snapping==INDEX_NONE)
    {
        System->Calibrate(Dt,bHeld?CalibrationError:2.f);
        // Smooth the owner HUD between authoritative 4 Hz snapshots, without predicting the result.
        CalibrationClock=FMath::Min(FMath::Min(GunAssemblyCalibration::Duration,System->Job().CalibrationTime+.35f),T+FMath::Clamp(Dt,0.f,.25f));
        if(GunAssemblyCalibration::Complete(System->Job().CalibrationTime)&&Clock>=FinishRetryAt)
        {
            System->Finish(Feedback);bHeld=false;FeedbackUntil=Clock+5;FinishRetryAt=Clock+2;
        }
    }
    if(System->Job().bFinished){PlayContact(.95f);Stop(true);return;}
    Present(Dt);
    if(Prompt)
    {
        Prompt->Aim=Aim;Prompt->Target=CalibrationTarget;Prompt->CalibrationRadius=Radius;Prompt->CalibrationTime=T;
        Prompt->bInside=Inside;
        Prompt->Markers.Reset();Prompt->Names.Reset();Prompt->Done.Reset();
        for(int32 I=0;I<Parts.Num();++I)
        {FVector2D P;PC->ProjectWorldLocationToScreen(GetActorTransform().TransformPosition(Positions[I]),P);Prompt->Markers.Add(P/FVector2D(W,H));Prompt->Names.Add(System->Recipe().Parts[I].Name);Prompt->Done.Add(System->Installed(I));}
        int32 Guide=Dragged!=INDEX_NONE?Dragged:Hovered;
        if(Guide==INDEX_NONE)for(int32 I=0;I<Parts.Num();++I)if(!System->Installed(I)){Guide=I;break;}
        Prompt->bInstallGuide=false;
        if(Guide!=INDEX_NONE&&!System->Installed(Guide))
        {
            const auto& Part=System->Recipe().Parts[Guide];FVector2D Screen;
            if(PC->ProjectWorldLocationToScreen(GetActorTransform().TransformPosition(Part.Target),Screen))
            {
                Prompt->bInstallGuide=true;Prompt->InstallTarget=Screen/FVector2D(W,H);Prompt->InstallPart=Prompt->Markers[Guide];
                Prompt->InstallName=Part.Name;Prompt->InstallDistance=FVector2D(Positions[Guide]-Part.Target).Size();
                Prompt->InstallAngle=FMath::UnwindDegrees(Angles[Guide]);
                Prompt->bInstallReady=Prompt->InstallDistance<=System->Recipe().PositionTolerance&&FMath::Abs(Prompt->InstallAngle)<=System->Recipe().AngleTolerance;
            }
        }
        RefreshClock+=Dt;if(RefreshClock>=.05f){RefreshClock=0;Prompt->Refresh(System,Clock<FeedbackUntil?Feedback:FString(),Guide,bHeld);}
        Prompt->InvalidateLayoutAndVolatility();
    }
}
void AGunAssemblyInteraction::Present(float Dt)
{
    for(int32 I=0;I<Parts.Num();++I)Parts[I]->SetRelativeTransform(FTransform(FRotator(0,Angles[I],0),Positions[I]));
    Ghost->SetVisibility(Dragged!=INDEX_NONE);
    if(Dragged!=INDEX_NONE)
    {
        Ghost->SetStaticMesh(Parts[Dragged]->GetStaticMesh());for(int I=0;I<Ghost->GetNumMaterials();++I)Ghost->SetMaterial(I,GhostMaterial);
        Ghost->SetRelativeLocation(System->Recipe().Parts[Dragged].Target);Ghost->SetRelativeRotation(FRotator::ZeroRotator);
        const auto& P=System->Recipe().Parts[Dragged];const bool Near=FVector2D(Positions[Dragged]-P.Target).Size()<=System->Recipe().PositionTolerance&&FMath::Abs(Angles[Dragged])<=System->Recipe().AngleTolerance;
        GhostMaterial->SetVectorParameterValue(TEXT("Tint"),Near?FLinearColor(.15f,.8f,.38f):FLinearColor(.65f,.7f,.74f));
    }
    PoseHands(Dt);
}
void AGunAssemblyInteraction::PlayContact(float Pitch)
{if(ContactSound)UGameplayStatics::PlaySound2D(this,ContactSound,.32f,Pitch);}
void AGunAssemblyInteraction::UpdateCalibrationAudio(bool bSuccessful,float DeltaTime)
{
    CalibrationSuccessTime=bSuccessful?FMath::Min(.12f,CalibrationSuccessTime+FMath::Max(0.f,DeltaTime)):0.f;
    const bool Wanted=CalibrationLoop&&CalibrationSuccessTime>=.12f;
    if(Wanted==bCalibrationAudioWanted)return;
    bCalibrationAudioWanted=Wanted;
    // The confirmation delay exceeds the fade-out, so rapid boundary crossings never stack sounds.
    if(Wanted)CalibrationAudio->FadeIn(.04f,1.f);
    else if(CalibrationAudio->IsPlaying())CalibrationAudio->FadeOut(.04f,0.f);
}
void AGunAssemblyInteraction::StopCalibrationAudio()
{
    CalibrationSuccessTime=0.f;bCalibrationAudioWanted=false;
    if(CalibrationAudio)CalibrationAudio->Stop();
}
void AGunAssemblyInteraction::RestorePlayer()
{
    ColdSteelWorkstationView::Restore(PC.Get(),this,WorkingPawn.Get(),PreviousView.Get(),.25f);
    StopCalibrationAudio();
    if(auto* Player=PC.Get())
    {
        if(bInputLocked){Player->SetIgnoreMoveInput(false);Player->SetIgnoreLookInput(false);bInputLocked=false;Player->FlushPressedKeys();}
        if(bHiddenPawn){Player->HiddenActors.Remove(WorkingPawn.Get());bHiddenPawn=false;}
        Player->bShowMouseCursor=false;Player->SetInputMode(FInputModeGameOnly());
    }
    if(Prompt){Prompt->RemoveFromParent();Prompt=nullptr;}
}
void AGunAssemblyInteraction::Stop(bool bReturnPanel)
{
    if(!bRunning)return;bRunning=false;bHeld=false;Dragged=INDEX_NONE;ClearRotationInput();
    StopCalibrationAudio();
    FString Why;if(System&&!System->Pause(Why))Feedback=Why;
    SetActorTickEnabled(false);RestorePlayer();SetActorHiddenInGame(true);
    if(auto* OwnerHUD=HUD.Get())OwnerHUD->CompleteGunAssembly(this,bReturnPanel&&Station.IsValid()&&!Station->IsFalling());
    SetLifeSpan(.3f);
}
void AGunAssemblyInteraction::EndPlay(const EEndPlayReason::Type Reason)
{
    StopCalibrationAudio();
    if(bRunning){bRunning=false;FString Why;if(System)System->Pause(Why);RestorePlayer();}
    if(Load.IsValid())Load->CancelHandle();Super::EndPlay(Reason);
}

void AGunAssemblyInteraction::SetupHands()
{
    const auto& Ref=Arms->GetSkinnedAsset()->GetRefSkeleton();LocalReference=Ref.GetRefBonePose();Reference=LocalReference;
    for(int32 I=0;I<Reference.Num();++I)if(Ref.GetParentIndex(I)>=0)Reference[I]*=Reference[Ref.GetParentIndex(I)];
    Pose=Reference;FString Raw;TSharedPtr<FJsonObject> Data;
    if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/forge-grip.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Data)||!Data)return;
    for(int32 Side=0;Side<2;++Side)
    {
        auto& H=Hands[Side];const FString S=Side?TEXT("r"):TEXT("l");
        H.Clavicle=Arms->GetBoneIndex(*(TEXT("clavicle_")+S));H.Upper=Arms->GetBoneIndex(*(TEXT("upperarm_")+S));H.Lower=Arms->GetBoneIndex(*(TEXT("lowerarm_")+S));H.Hand=Arms->GetBoneIndex(*(TEXT("hand_")+S));
        if(H.Clavicle<0||H.Upper<0||H.Lower<0||H.Hand<0)return;
        const auto J=Data->GetObjectField(TEXT("hands"))->GetObjectField(S);H.Grip=FTransform(GAQuat(J->GetArrayField(TEXT("q"))),GAVector(J->GetArrayField(TEXT("p"))));
        for(int32 I=0;I<Reference.Num();++I)if(I==H.Clavicle||Ref.BoneIsChildOf(I,H.Clavicle)){H.Bones.Add(I);ArmBones.Add(I);}
    }
    for(const auto& Pair:Data->GetObjectField(TEXT("finger_rotations"))->Values)
    {const int32 I=Arms->GetBoneIndex(*Pair.Key);if(I>=0)Fingers.Add(I,GAQuat(Pair.Value->AsArray()));}
    bHandsReady=true;
}
void AGunAssemblyInteraction::PoseHands(float Dt)
{
    if(!bHandsReady)return;
    // Both native arm chains move together; no mesh scaling or isolated wrist teleport.
    const FTransform Torso(FRotator(0,90,0),FVector(5,0,123));Arms->SetRelativeTransform(Torso);
    for(int32 I=0;I<Pose.Num();++I)Pose[I]=Reference[I]*Torso;
    const int32 Held=Dragged!=INDEX_NONE?Dragged:Snapping;
    FVector Right=Held!=INDEX_NONE?Positions[Held]+FVector(-2,0,3):FVector(43,30,105);
    HandPosition=FMath::VInterpTo(HandPosition,Right,Dt,20.f);
    const float Yaw=Held!=INDEX_NONE?Angles[Held]:0;
    const FTransform RightGrip(FRotator(0,Yaw,90),HandPosition);
    const FTransform LeftGrip(FRotator(0,0,-90),System->Recipe().BodyPosition+FVector(-4,13,2));
    SolveHand(1,Hands[1].Grip*RightGrip,Held!=INDEX_NONE?.9f:.35f);
    SolveHand(0,Hands[0].Grip*LeftGrip,.62f);
    Arms->CommitStationPose(Pose,ArmBones);
}
void AGunAssemblyInteraction::SolveHand(int32 Side,const FTransform& Target,float Curl)
{
    const auto& H=Hands[Side];const auto& Ref=Arms->GetSkinnedAsset()->GetRefSkeleton();
    FVector Shoulder=Pose[H.Upper].GetLocation();const FVector Wrist=Target.GetLocation();
    const FVector UpperRef=Reference[H.Lower].GetLocation()-Reference[H.Upper].GetLocation();
    const FVector LowerRef=Reference[H.Hand].GetLocation()-Reference[H.Lower].GetLocation();
    const float A=UpperRef.Size(),B=LowerRef.Size();FVector Axis=(Wrist-Shoulder).GetSafeNormal();
    float D=(Wrist-Shoulder).Size();if(D>A+B-1){Shoulder=Wrist-Axis*(A+B-1);D=A+B-1;}
    D=FMath::Max(D,1.f);const float Along=(D*D+A*A-B*B)/(2*D);
    FVector Pole=FVector(-1,Side?1:-1,-.3);Pole=(Pole-Axis*(Pole|Axis)).GetSafeNormal();
    const FVector Elbow=Shoulder+Axis*Along+Pole*FMath::Sqrt(FMath::Max(0.f,A*A-Along*Along));
    const FQuat HandDelta=Target.GetRotation()*Reference[H.Hand].GetRotation().Inverse();
    const FQuat LowerDelta=FQuat::FindBetweenNormals(HandDelta.RotateVector(LowerRef.GetSafeNormal()),(Wrist-Elbow).GetSafeNormal())*HandDelta;
    const FQuat UpperDelta=FQuat::FindBetweenNormals(LowerDelta.RotateVector(UpperRef.GetSafeNormal()),(Elbow-Shoulder).GetSafeNormal())*LowerDelta;
    Pose[H.Clavicle]=FTransform(UpperDelta*Reference[H.Clavicle].GetRotation(),Shoulder+UpperDelta.RotateVector(Reference[H.Clavicle].GetLocation()-Reference[H.Upper].GetLocation()));
    Pose[H.Upper]=FTransform(UpperDelta*Reference[H.Upper].GetRotation(),Shoulder);
    Pose[H.Lower]=FTransform(LowerDelta*Reference[H.Lower].GetRotation(),Elbow);Pose[H.Hand]=Target;
    for(int32 I:H.Bones)
    {
        if(I==H.Clavicle||I==H.Upper||I==H.Lower||I==H.Hand)continue;
        FTransform Local=LocalReference[I];if(const FQuat* Q=Fingers.Find(I))Local.SetRotation(FQuat::Slerp(Local.GetRotation(),*Q,Curl).GetNormalized());
        Pose[I]=Local*Pose[Ref.GetParentIndex(I)];
    }
}
