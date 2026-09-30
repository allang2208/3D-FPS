#include "GunAssemblyInteraction.h"
#include "GunAssemblySystem.h"
#include "ForgeArmsMeshComponent.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWorld.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/GunAssemblyActionWidget.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
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
FSoftObjectPath GAPath(const FString& P){return FSoftObjectPath(P+TEXT(".")+FPaths::GetCleanFilename(P));}
template<class T>T* GAResolve(const FString& P){return Cast<T>(GAPath(P).ResolveObject());}
FVector GAVector(const TArray<TSharedPtr<FJsonValue>>& V){return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());}
FQuat GAQuat(const TArray<TSharedPtr<FJsonValue>>& V){return FQuat(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber(),V[3]->AsNumber()).GetNormalized();}
}

AGunAssemblyInteraction::AGunAssemblyInteraction()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("GunWorkbenchFrame"));
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("AssemblyCamera"));Camera->SetupAttachment(RootComponent);Camera->FieldOfView=65;
    Body=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FixedReceiver"));Body->SetupAttachment(RootComponent);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Ghost=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TargetOutline"));Ghost->SetupAttachment(RootComponent);Ghost->SetCollisionEnabled(ECollisionEnabled::NoCollision);Ghost->SetCastShadow(false);Ghost->SetVisibility(false);
    Arms=CreateDefaultSubobject<UForgeArmsMeshComponent>(TEXT("V7AssemblyHands"));Arms->SetupAttachment(RootComponent);Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCastShadow(false);Arms->SetComponentTickEnabled(false);Arms->bReceivesDecals=false;
    SetActorHiddenInGame(true);
}
void AGunAssemblyInteraction::Prepare(APlayerController* Player,AVoxelBuildPrefabActor* Table,UColdSteelHUDWidget* OwnerHUD)
{
    PC=Player;Station=Table;HUD=OwnerHUD;SetOwner(Player);SetActorTransform(Table->Body()->GetComponentTransform());
    System=GetGameInstance()->GetSubsystem<UGunAssemblySystem>();const auto& R=System->Recipe();
    if(R.Id.IsNone()){Error=TEXT("当前工件的拼装配方未就绪");return;}
    if(!System->Job().Id.IsEmpty()&&System->Job().PartCount!=R.Parts.Num())
    {Error=TEXT("工件组件与配方不一致，请恢复原配方配置");return;}
    Camera->SetRelativeLocation(R.Camera);Camera->SetRelativeRotation((R.LookAt-R.Camera).Rotation());
    TArray<FSoftObjectPath> Assets={GAPath(R.BodyMesh),GAPath(GAArms),GAPath(GAGhost),GAPath(GASound)};
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
    ContactSound=GAResolve<USoundBase>(GASound);SetupHands();
    bReady=bHandsReady&&!Parts.IsEmpty()&&Parts.Num()==R.Parts.Num();if(!bReady)Error=TEXT("装配抓握资源未就绪");
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
    if(System->Job().Recipe!=System->Recipe().Id){Reason=TEXT("工件配方不匹配");return false;}
    return true;
}
void AGunAssemblyInteraction::Enter()
{
    auto* Player=PC.Get();if(!Player)return;
    bRunning=true;WorkingPawn=Player->GetPawn();PreviousView=Player->GetViewTarget();bWasCursor=Player->bShowMouseCursor;
    if(auto* Pawn=Cast<AFPSGAMECharacter>(WorkingPawn.Get())){Pawn->SuspendWeaponForMenu();Pawn->GetCharacterMovement()->StopMovementImmediately();}
    Player->FlushPressedKeys();Player->SetIgnoreMoveInput(true);Player->SetIgnoreLookInput(true);bInputLocked=true;
    Player->bShowMouseCursor=false;Player->SetInputMode(FInputModeGameOnly());
    if(WorkingPawn.IsValid()&&!Player->HiddenActors.Contains(WorkingPawn.Get())){Player->HiddenActors.Add(WorkingPawn.Get());bHiddenPawn=true;}
    for(int32 I=0;I<Parts.Num();++I)
    {if(System->Installed(I)){Positions[I]=System->Recipe().Parts[I].Target;Angles[I]=0;}else ResetLoose(I);}
    HandPosition=FVector(43,27,110);Clock=0;FinishAt=System->Job().bFinished?0:-1;
    SetActorHiddenInGame(false);SetActorTickEnabled(true);Present(0);Player->SetViewTargetWithBlend(this,.35f,VTBlend_Cubic);
    Prompt=CreateWidget<UGunAssemblyActionWidget>(Player);Prompt->AddToViewport(80);
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
                Dragged=Hovered;FVector P;if(CursorOnPlane(Positions[Dragged].Z,P))DragOffset=Positions[Dragged]-P;
                PlayContact(.85f);Feedback=System->Recipe().Parts[Dragged].Name+TEXT(" · 拖向安装轮廓");FeedbackUntil=Clock+2;
            }
        }
        if(Dragged!=INDEX_NONE)
        {
            if(E.Key==EKeys::MouseScrollUp||E.Key==EKeys::R)Angles[Dragged]=FMath::UnwindDegrees(Angles[Dragged]+5);
            if(E.Key==EKeys::MouseScrollDown||E.Key==EKeys::Q)Angles[Dragged]=FMath::UnwindDegrees(Angles[Dragged]-5);
        }
    }
    if(E.Key==EKeys::LeftMouseButton&&E.Event==IE_Released){bHeld=false;if(Dragged!=INDEX_NONE)Drop();}
    return true; // No fire, movement, hotbar or menu key can pass into gameplay.
}
void AGunAssemblyInteraction::ResetLoose(int32 I)
{Positions[I]=System->Recipe().Parts[I].Loose;Angles[I]=System->Recipe().Parts[I].Angle;}
void AGunAssemblyInteraction::Drop()
{
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
    {bHeld=false;if(Dragged!=INDEX_NONE){ResetLoose(Dragged);Dragged=INDEX_NONE;}Ghost->SetVisibility(false);return;}
    Clock+=Dt;
    if(Snapping!=INDEX_NONE)
    {
        SnapTime+=Dt;const float A=FMath::SmoothStep(0.f,1.f,FMath::Clamp(SnapTime/.32f,0.f,1.f));
        Positions[Snapping]=FMath::Lerp(SnapFrom,System->Recipe().Parts[Snapping].Target,A);Angles[Snapping]=FMath::Lerp(SnapAngle,0.f,A);
        if(SnapTime>=.28f&&!bContactPlayed){PlayContact(1.15f);bContactPlayed=true;}
        if(SnapTime>=.32f)Snapping=INDEX_NONE;
    }
    if(Dragged!=INDEX_NONE)
    {
        FVector P;const auto& Part=System->Recipe().Parts[Dragged];
        const float Height=Part.Target.Z+3;
        if(CursorOnPlane(Height,P)){P+=DragOffset;Positions[Dragged]=FVector(FMath::Clamp(P.X,53.,113.),FMath::Clamp(P.Y,-60.,60.),Height);}
    }
    Hovered=INDEX_NONE;double Best=MAX_dbl;
    if(Dragged==INDEX_NONE&&!System->Assembled())for(int32 I=0;I<Parts.Num();++I)if(!System->Installed(I))
    {
        FVector P;if(!CursorOnPlane(Positions[I].Z,P))continue;
        const FVector D=FRotator(0,-Angles[I],0).RotateVector(P-Positions[I]);const auto& R=System->Recipe().Parts[I];
        const double Metric=FMath::Square(D.X/FMath::Max(3.5,R.Extent.X+1.5))+FMath::Square(D.Y/FMath::Max(3.5,R.Extent.Y+1.5));
        if(Metric<=1.35&&Metric<Best){Best=Metric;Hovered=I;}
    }
    const float T=System->Job().CalibrationTime;
    CalibrationTarget=FVector2D(.5+.105*FMath::Sin(T*.9),.40+.065*FMath::Sin(T*1.3+.4));
    int32 W=1,H=1;PC->GetViewportSize(W,H);
    const float CalibrationError=((Aim-CalibrationTarget)*FVector2D(W,H)).Size()/(FMath::Min(W,H)*.047f);
    if(System->Assembled()&&!System->Job().bFinished&&Snapping==INDEX_NONE&&bHeld)
    {
        System->Calibrate(Dt,CalibrationError);
        if(System->Job().CalibrationSeconds>=System->Job().CalibrationDuration&&System->Finish(Feedback))
        {FinishAt=Clock;PlayContact(.95f);}else if(System->Job().CalibrationSeconds>=System->Job().CalibrationDuration){bHeld=false;FeedbackUntil=Clock+5;}
    }
    Present(Dt);
    if(Prompt)
    {
        Prompt->Aim=Aim;Prompt->Target=CalibrationTarget;Prompt->bInside=bHeld&&CalibrationError<=1;
        Prompt->Markers.Reset();Prompt->Names.Reset();Prompt->Done.Reset();
        for(int32 I=0;I<Parts.Num();++I)
        {FVector2D P;PC->ProjectWorldLocationToScreen(GetActorTransform().TransformPosition(Positions[I]),P);Prompt->Markers.Add(P/FVector2D(W,H));Prompt->Names.Add(System->Recipe().Parts[I].Name);Prompt->Done.Add(System->Installed(I));}
        RefreshClock+=Dt;if(RefreshClock>=.05f){RefreshClock=0;Prompt->Refresh(System,Clock<FeedbackUntil?Feedback:FString(),Dragged!=INDEX_NONE?Dragged:Hovered,bHeld);}
        Prompt->InvalidateLayoutAndVolatility();
    }
    if(FinishAt>=0&&Clock-FinishAt>4.5f)Stop(true);
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
void AGunAssemblyInteraction::RestorePlayer()
{
    if(auto* Player=PC.Get())
    {
        if(bInputLocked){Player->SetIgnoreMoveInput(false);Player->SetIgnoreLookInput(false);bInputLocked=false;Player->FlushPressedKeys();}
        if(bHiddenPawn){Player->HiddenActors.Remove(WorkingPawn.Get());bHiddenPawn=false;}
        if(Player->GetViewTarget()==this)Player->SetViewTargetWithBlend(PreviousView.IsValid()?PreviousView.Get():Player->GetPawn(),.25f,VTBlend_Cubic);
        Player->bShowMouseCursor=false;Player->SetInputMode(FInputModeGameOnly());
    }
    if(Prompt){Prompt->RemoveFromParent();Prompt=nullptr;}
}
void AGunAssemblyInteraction::Stop(bool bReturnPanel)
{
    if(!bRunning)return;bRunning=false;bHeld=false;Dragged=INDEX_NONE;
    FString Why;if(System&&!System->Pause(Why))Feedback=Why;
    SetActorTickEnabled(false);RestorePlayer();SetActorHiddenInGame(true);
    if(auto* OwnerHUD=HUD.Get())OwnerHUD->CompleteGunAssembly(this,bReturnPanel&&Station.IsValid()&&!Station->IsFalling());
    SetLifeSpan(.3f);
}
void AGunAssemblyInteraction::EndPlay(const EEndPlayReason::Type Reason)
{
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
