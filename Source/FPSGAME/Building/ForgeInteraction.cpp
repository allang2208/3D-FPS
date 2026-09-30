#include "ForgeInteraction.h"
#include "ForgeArmsMeshComponent.h"
#include "ForgingSystem.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWorld.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/ColdSteelForgeActionWidget.h"
#include "Camera/CameraComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "GameFramework/InputSettings.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "InputKeyEventArgs.h"

namespace
{
const FString AssetRoot=TEXT("/Game/Props/ForgeInteraction20260927/");
const FString ArmsPath=TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7");
FSoftObjectPath Asset(const FString& Name)
{const FString Path=Name.StartsWith(TEXT("/"))?Name:AssetRoot+Name;return FSoftObjectPath(Path+TEXT(".")+FPaths::GetCleanFilename(Path));}
template<class T> T* Loaded(const FString& Name){return Cast<T>(Asset(Name).ResolveObject());}
FVector Vector(const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());}
FQuat Quat(const TArray<TSharedPtr<FJsonValue>>& A){return FQuat(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber(),A[3]->AsNumber()).GetNormalized();}
float Ease(float X){return FMath::SmoothStep(0.f,1.f,X);}
}

AForgeInteraction::AForgeInteraction()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("StationFrame"));
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("ForgeCamera"));Camera->SetupAttachment(RootComponent);Camera->FieldOfView=67;
    Camera->SetRelativeLocation(FVector(29,-43,148));Camera->SetRelativeRotation((FVector(29,22,92)-Camera->GetRelativeLocation()).Rotation());
    Arms=CreateDefaultSubobject<UForgeArmsMeshComponent>(TEXT("NativeV7ForgeArms"));Arms->SetupAttachment(RootComponent);
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCastShadow(false);Arms->SetComponentTickEnabled(false);
    Arms->bReceivesDecals=false;Arms->SetOwnerNoSee(false);Arms->SetVisibility(true);
    auto Make=[this](const TCHAR* Name){auto* C=CreateDefaultSubobject<UStaticMeshComponent>(Name);C->SetupAttachment(RootComponent);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);return C;};
    Hammer=Make(TEXT("ForgingHammer"));Tongs=Make(TEXT("HandheldTongs"));Blank=Make(TEXT("SwordBlank"));
    HeatRing=Make(TEXT("HeatSpot"));AimRing=Make(TEXT("HammerAim"));HeatRing->SetCastShadow(false);AimRing->SetCastShadow(false);
    ScaleSparks=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("HotScale"));ScaleSparks->SetupAttachment(RootComponent);
    ScaleSparks->SetCollisionEnabled(ECollisionEnabled::NoCollision);ScaleSparks->SetCastShadow(false);
    ScaleSparks->NumCustomDataFloats=2;ScaleSparks->bReceivesDecals=false;
    HeatVeil=Make(TEXT("LocalHeatVeil"));HeatVeil->SetCastShadow(false);HeatVeil->bReceivesDecals=false;
    HeatFumes=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("ForgeFumes"));HeatFumes->SetupAttachment(RootComponent);
    HeatFumes->SetCollisionEnabled(ECollisionEnabled::NoCollision);HeatFumes->SetCastShadow(false);
    HeatFumes->NumCustomDataFloats=3;HeatFumes->bReceivesDecals=false;
    HotLight=CreateDefaultSubobject<UPointLightComponent>(TEXT("HotSteelBounce"));HotLight->SetupAttachment(RootComponent);
    HotLight->SetCastShadows(false);HotLight->SetIntensityUnits(ELightUnits::Lumens);
    HotLight->SetIntensity(0);HotLight->SetAttenuationRadius(85);HotLight->SetSourceRadius(3);
    HotLight->SetLightColor(FLinearColor(1.f,.24f,.035f));
    SetActorHiddenInGame(true);
}
void AForgeInteraction::Prepare(APlayerController* Player,AVoxelBuildPrefabActor* InStation,UColdSteelHUDWidget* InHUD)
{
    PC=Player;Station=InStation;HUD=InHUD;SetOwner(Player);
    System=GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>();
    SetActorTransform(InStation->Body()->GetComponentTransform());
    TArray<FSoftObjectPath> Paths={Asset(ArmsPath)};
    for(const TCHAR* N:{TEXT("SM_ForgeHammer"),TEXT("SM_ForgeTongs"),TEXT("SM_ForgeBlank0"),TEXT("SM_ForgeBlank1"),TEXT("SM_ForgeBlank2"),TEXT("SM_ForgeRing"),TEXT("SM_ForgeSpark"),TEXT("SW_ForgeHammerImpact")})Paths.Add(Asset(N));
    for(const TCHAR* N:{TEXT("M_ForgeScaleSpark"),TEXT("M_ForgeFume"),TEXT("M_ForgeHeatVeil"),TEXT("/Engine/BasicShapes/Plane")})Paths.Add(Asset(N));
    Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateUObject(this,&ThisClass::AssetsLoaded));
}
void AForgeInteraction::AssetsLoaded()
{
    auto* Mesh=Loaded<USkeletalMesh>(ArmsPath);if(!Mesh){LoadError=TEXT("锻造手臂未就绪");return;}
    Arms->SetSkinnedAssetAndUpdate(Mesh,true);
    Hammer->SetStaticMesh(Loaded<UStaticMesh>(TEXT("SM_ForgeHammer")));Tongs->SetStaticMesh(Loaded<UStaticMesh>(TEXT("SM_ForgeTongs")));
    for(int32 I=0;I<3;++I)Blanks.Add(Loaded<UStaticMesh>(FString::Printf(TEXT("SM_ForgeBlank%d"),I)));
    HeatRing->SetStaticMesh(Loaded<UStaticMesh>(TEXT("SM_ForgeRing")));AimRing->SetStaticMesh(HeatRing->GetStaticMesh());
    ScaleSparks->SetStaticMesh(Loaded<UStaticMesh>(TEXT("SM_ForgeSpark")));ImpactSound=Loaded<USoundBase>(TEXT("SW_ForgeHammerImpact"));
    auto* EffectPlane=Loaded<UStaticMesh>(TEXT("/Engine/BasicShapes/Plane"));
    auto* SparkSurface=Loaded<UMaterialInterface>(TEXT("M_ForgeScaleSpark"));
    auto* FumeSurface=Loaded<UMaterialInterface>(TEXT("M_ForgeFume"));
    auto* VeilSurface=Loaded<UMaterialInterface>(TEXT("M_ForgeHeatVeil"));
    if(!Hammer->GetStaticMesh()||!Tongs->GetStaticMesh()||Blanks.Contains(nullptr)||!HeatRing->GetStaticMesh()||!ScaleSparks->GetStaticMesh()||!ImpactSound)
    {LoadError=TEXT("锻造工具资源未就绪");return;}
    if(!EffectPlane||!SparkSurface||!FumeSurface||!VeilSurface){LoadError=TEXT("锻造热效资源未就绪");return;}
    Blank->SetStaticMesh(Blanks[0]);BlankMaterial=Blank->CreateDynamicMaterialInstance(0);
    BlankMaterial->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.045f,.004f));
    HeatMaterial=HeatRing->CreateDynamicMaterialInstance(0);AimMaterial=AimRing->CreateDynamicMaterialInstance(0);
    HeatMaterial->SetVectorParameterValue(TEXT("Tint"),FLinearColor(.015f,.65f,1.f));HeatMaterial->SetScalarParameterValue(TEXT("Heat"),1.4f);
    ScaleSparks->SetMaterial(0,SparkSurface);
    HeatVeil->SetStaticMesh(EffectPlane);HeatFumes->SetStaticMesh(EffectPlane);
    VeilMaterial=HeatVeil->CreateDynamicMaterialInstance(0,VeilSurface);
    FumeMaterial=HeatFumes->CreateDynamicMaterialInstance(0,FumeSurface);
    AimMaterial->SetVectorParameterValue(TEXT("Tint"),FLinearColor(.68f,.76f,.78f));AimMaterial->SetScalarParameterValue(TEXT("Heat"),.12f);
    AimRing->SetRelativeScale3D(FVector(.35f));
    VisualRandom.Initialize(int32(GetUniqueID()));
    SparkPool.SetNum(72);for(int32 I=0;I<SparkPool.Num();++I)ScaleSparks->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
    FumePool.SetNum(56);for(int32 I=0;I<FumePool.Num();++I)HeatFumes->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
    const auto& Ref=Mesh->GetRefSkeleton();LocalReference=Ref.GetRefBonePose();Reference=LocalReference;
    for(int32 I=0;I<Reference.Num();++I)if(Ref.GetParentIndex(I)>=0)Reference[I]*=Reference[Ref.GetParentIndex(I)];
    Pose=Reference;bReady=LoadGrip();
    if(!bReady)LoadError=TEXT("锻造抓握数据未就绪");
}
bool AForgeInteraction::LoadGrip()
{
    FString Raw;TSharedPtr<FJsonObject> Data;
    if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/forge-grip.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Data)||!Data)return false;
    const TSharedPtr<FJsonObject>* HandData=nullptr,*DigitData=nullptr;
    if(!Data->TryGetObjectField(TEXT("hands"),HandData)||!Data->TryGetObjectField(TEXT("finger_rotations"),DigitData))return false;
    for(int32 Side=0;Side<2;++Side)
    {
        auto& H=Hands[Side];const FString S=Side?TEXT("r"):TEXT("l");
        H.Clavicle=Arms->GetBoneIndex(*(TEXT("clavicle_")+S));H.Upper=Arms->GetBoneIndex(*(TEXT("upperarm_")+S));H.Lower=Arms->GetBoneIndex(*(TEXT("lowerarm_")+S));H.Hand=Arms->GetBoneIndex(*(TEXT("hand_")+S));
        if(H.Clavicle<0||H.Upper<0||H.Lower<0||H.Hand<0)return false;
        const auto& Ref=Arms->GetSkinnedAsset()->GetRefSkeleton();
        for(int32 I=0;I<Reference.Num();++I)if(I==H.Clavicle||Ref.BoneIsChildOf(I,H.Clavicle))
        {
            H.Bones.Add(I);ArmBoundsBones.Add(I);
        }
        const auto& J=(*HandData)->GetObjectField(S);H.Grip=FTransform(Quat(J->GetArrayField(TEXT("q"))),Vector(J->GetArrayField(TEXT("p"))));
    }
    for(const auto& Pair:(*DigitData)->Values)
    {const int32 I=Arms->GetBoneIndex(*Pair.Key);if(I>=0)Fingers.Add(I,Quat(Pair.Value->AsArray()));}
    HammerContact=Vector(Data->GetArrayField(TEXT("hammer_contact_cm")));
    ContactSeconds=Data->GetNumberField(TEXT("contact_seconds"));StrokeSeconds=Data->GetNumberField(TEXT("stroke_seconds"));
    const TSharedPtr<FJsonObject>* Layout=nullptr;
    if(Data->TryGetObjectField(TEXT("station_layout"),Layout))
    {
        BodyOrigin=Vector((*Layout)->GetArrayField(TEXT("body_origin_cm")));ImpactAxis=Vector((*Layout)->GetArrayField(TEXT("hammer_axis")));
        TongAxis=Vector((*Layout)->GetArrayField(TEXT("tong_axis")));ElbowPole=Vector((*Layout)->GetArrayField(TEXT("elbow_pole_cm")));
        QuenchOrigin=Vector((*Layout)->GetArrayField(TEXT("quench_origin_cm")));
        WorkYaw=(*Layout)->GetNumberField(TEXT("work_yaw"));QuenchPitch=(*Layout)->GetNumberField(TEXT("quench_pitch"));
    }
    const TArray<TSharedPtr<FJsonValue>>* Keys=nullptr;if(!Data->TryGetArrayField(TEXT("stroke"),Keys))return false;
    for(const auto& Key:*Keys){const auto& K=Key->AsObject();Stroke.Add({float(K->GetNumberField(TEXT("t"))),float(K->GetNumberField(TEXT("angle"))),Vector(K->GetArrayField(TEXT("offset")))});}
    return Stroke.Num()>=2;
}
bool AForgeInteraction::Ready(FString& Reason) const
{if(!LoadError.IsEmpty()){Reason=LoadError;return false;}if(!bReady){Reason=TEXT("正在准备锻造工具…");return false;}return true;}
bool AForgeInteraction::Start(FName Recipe,FString& Reason)
{
    if(!Ready(Reason)||!PC.IsValid()||!Station.IsValid()||Station->IsFalling())return false;
    if(!System->Start(Recipe,Reason))return false;
    // Inventory drawer is retracted by the caller before Enter takes its own input lock.
    return true;
}
void AForgeInteraction::Enter()
{
    auto* Player=PC.Get();if(!Player)return;
    bRunning=true;WorkingPawn=Player->GetPawn();PreviousView=Player->GetViewTarget();
    if(Station.IsValid())
    {
        auto* Body=Station->Body();
        if(Body->DoesSocketExist(TEXT("QuenchSurface")))QuenchSurface=Body->GetSocketTransform(TEXT("QuenchSurface"),RTS_Component).GetLocation();
        QuenchWaterSlot=Body->GetMaterialIndex(TEXT("Water"));
        if(QuenchWaterSlot!=INDEX_NONE)
        {
            PreviousWaterMaterial=Body->GetMaterial(QuenchWaterSlot);
            QuenchWaterMaterial=Body->CreateDynamicMaterialInstance(QuenchWaterSlot);
            if(QuenchWaterMaterial){QuenchWaterMaterial->SetScalarParameterValue(TEXT("QuenchTime"),-10000);QuenchWaterMaterial->SetScalarParameterValue(TEXT("Immersion"),0);}
        }
    }
    if(auto* Pawn=Cast<AFPSGAMECharacter>(WorkingPawn.Get())){Pawn->SuspendWeaponForMenu();Pawn->GetCharacterMovement()->StopMovementImmediately();}
    Player->FlushPressedKeys();Player->SetIgnoreMoveInput(true);Player->SetIgnoreLookInput(true);bHeldInput=true;
    Player->bShowMouseCursor=false;Player->SetInputMode(FInputModeGameOnly());
    if(WorkingPawn.IsValid()&&!Player->HiddenActors.Contains(WorkingPawn.Get())){Player->HiddenActors.Add(WorkingPawn.Get());bHidPawn=true;}
    SetActorHiddenInGame(false);SetActorTickEnabled(true);Present(0);
    Player->SetViewTargetWithBlend(this,.35f,VTBlend_Cubic);
    Prompt=CreateWidget<UColdSteelForgeActionWidget>(Player);Prompt->AddToViewport(80);
}
bool AForgeInteraction::HandleInput(const FInputKeyEventArgs& Event)
{
    if(!bRunning)return false;
    if(Event.Key==EKeys::MouseX||Event.Key==EKeys::MouseY)
    {
        if(StrikeAt<0&&FinishAt<0)
        {
            MoveAim(Event);
        }
        return true;
    }
    if(Event.Event==IE_Pressed)
    {
        if(Event.Key==EKeys::Escape||Event.Key==EKeys::Tab){Stop(true);return true;}
        if(Event.Key==EKeys::LeftMouseButton&&FinishAt<0&&StrikeAt<0&&System->Active())
        {
            const int32 Target=System->TargetIndex();
            if(System->BeginStrike(Target,ContactSeconds,StrokeSeconds-ContactSeconds+.25))
            {StrikeAt=FPlatformTime::Seconds();StrikeAim=Aim;StrikeIndex=Target;bContact=false;}
        }
    }
    return true;
}
void AForgeInteraction::MoveAim(const FInputKeyEventArgs& Event)
{
    auto* Player=PC.Get();if(!Player||!Player->PlayerInput)return;
    FInputAxisProperties Properties;if(!Player->PlayerInput->GetAxisProperties(Event.Key,Properties))return;
    float Amount=Event.AmountDepressed;
    if(Properties.DeadZone>0)
        Amount=FMath::Sign(Amount)*FMath::Max(0.f,FMath::Abs(Amount)-Properties.DeadZone)/FMath::Max(.001f,1-Properties.DeadZone);
    Amount=FMath::Sign(Amount)*FMath::Pow(FMath::Abs(Amount),Properties.Exponent)*Properties.Sensitivity;
    if(Properties.bInvert)Amount=-Amount;
    const bool Horizontal=Event.Key==EKeys::MouseX;
    for(const auto& Mapping:Player->PlayerInput->GetKeysForAxis(Horizontal?TEXT("Turn"):TEXT("LookUp")))
        if(Mapping.Key==Event.Key){Amount*=FMath::Abs(Mapping.Scale);break;}
    const auto* Settings=GetDefault<UInputSettings>();
    if(Settings->bEnableLegacyInputScales)
    {
        PRAGMA_DISABLE_DEPRECATION_WARNINGS
        Amount*=FMath::Abs(Horizontal?Player->GetDeprecatedInputYawScale():Player->GetDeprecatedInputPitchScale());
        PRAGMA_ENABLE_DEPRECATION_WARNINGS
    }
    const auto* Pawn=Cast<AFPSGAMECharacter>(WorkingPawn.Get());
    const float GameplayFOV=Pawn?Pawn->BaseLookHorizontalFOV():90.f;
    if(Settings->bEnableFOVScaling)Amount*=Settings->FOVScale*GameplayFOV;
    // Preserve normal hip-look screen travel at the forge camera's narrower FOV.
    // Intersect the moved view ray with the face; no axis-dependent cm multiplier.
    const double FOVRatio=FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView)*.5)/FMath::Tan(FMath::DegreesToRadians(GameplayFOV)*.5);
    const FQuat View=Camera->GetRelativeRotation().Quaternion();const FVector Origin=Camera->GetRelativeLocation();
    const FVector Local=View.UnrotateVector(Point(Aim)-Origin);if(Local.X<=0)return;
    FVector Ray(1,Local.Y/Local.X,Local.Z/Local.X);
    const double Delta=FMath::DegreesToRadians(Amount)*FOVRatio;
    if(Horizontal)Ray.Y+=Delta;else Ray.Z+=Delta;
    Ray=View.RotateVector(Ray);if(Ray.Z>=-KINDA_SMALL_NUMBER)return;
    const FVector Hit=Origin+Ray*((Point(Aim).Z-Origin.Z)/Ray.Z);
    Aim.Y=FMath::Clamp(.375+(Hit.X-29)/60.,.1,.65);
    Aim.X=FMath::Clamp(.5+(Hit.Y-22)/24.,.37,.63);
}
FVector AForgeInteraction::Point(const FVector2D& UV) const
{const double Across=(UV.X-.5)*24;return FVector(29+(UV.Y-.375)*60,22+Across,FMath::Abs(Across)<=2.5?91.95:91.0);}
FTransform AForgeInteraction::HammerFrame(const FVector& Hit,double Age) const
{
    const float T=Age<0?0:float(Age);FStrokeKey K=Stroke.Last();
    for(int32 I=1;I<Stroke.Num();++I)if(T<=Stroke[I].Time)
    {const float A=Ease((T-Stroke[I-1].Time)/(Stroke[I].Time-Stroke[I-1].Time));K.Angle=FMath::Lerp(Stroke[I-1].Angle,Stroke[I].Angle,A);K.Offset=FMath::Lerp(Stroke[I-1].Offset,Stroke[I].Offset,A);break;}
    const FQuat ContactRotation=FRotationMatrix::MakeFromXZ(FVector(0,0,-1),ImpactAxis).ToQuat();
    return FTransform(ContactRotation*FQuat(FVector::YAxisVector,FMath::DegreesToRadians(K.Angle)),Hit-ContactRotation.RotateVector(HammerContact)+K.Offset);
}
FTransform AForgeInteraction::TongFrame(const FTransform& Work) const
{
    const FQuat Q=FRotationMatrix::MakeFromXZ(FVector(0,0,-1),TongAxis).ToQuat();
    const FQuat Tilt=Work.GetRotation()*FQuat(FVector::UpVector,FMath::DegreesToRadians(WorkYaw)).Inverse();
    // Flat jaws enclose the tang; the paired reins remain inside the accepted cylindrical grasp.
    const FVector Jaw=Work.TransformPosition(FVector(-24,0,.475));
    return FTransform(Tilt*Q,Jaw-Tilt.RotateVector(Q.RotateVector(FVector(0,0,25.4))));
}
void AForgeInteraction::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);if(!bRunning)return;
    auto* World=Station.IsValid()?Cast<AVoxelBuildWorld>(Station->GetOwner()):nullptr;
    if(!PC.IsValid()||PC->GetPawn()!=WorkingPawn.Get()||!Station.IsValid()||Station->IsFalling()||!World||!World->HasPrefabAt(Station->AnchorCell())){Stop(false);return;}
    const double Now=FPlatformTime::Seconds();
    if(!System->Active()&&FinishAt<0)FinishAt=Now;
    if(StrikeAt>=0&&Now-StrikeAt>=ContactSeconds&&!bContact){bContact=true;Contact();}
    if(StrikeAt>=0&&Now-StrikeAt>=StrokeSeconds)StrikeAt=-100;
    Present(DeltaTime);Sparks(DeltaTime);
    DisplayClock+=DeltaTime;
    if(Prompt&&DisplayClock>=.05f)
    {
        DisplayClock=0;Prompt->Refresh(System,FinishAt>=0,Now-LastFeedback<.5,bLastHit);
    }
    if(FinishAt>=0&&Now-FinishAt>=5.8)Stop(true);
}
void AForgeInteraction::Present(float DeltaTime)
{
    const double Now=FPlatformTime::Seconds();
    const int32 Stage=FMath::Clamp(System->Job().Hits/7,0,2);
    if(Stage!=BlankStage){BlankStage=Stage;Blank->SetStaticMesh(Blanks[Stage]);Blank->SetMaterial(0,BlankMaterial);}
    const FQuat WorkRotation(FVector::UpVector,FMath::DegreesToRadians(WorkYaw));
    FTransform Work(WorkRotation,FVector(29,22,91));
    FTransform Tool=HammerFrame(Point(StrikeAt>=0?StrikeAim:Aim),StrikeAt>=0?Now-StrikeAt:-1);
    float Heat=.95f+.25f*(1.f-float(System->ResolvedTargets())/System->TargetCount);
    if(FinishAt>=0)
    {
        PresentQuench(float(Now-FinishAt),Work,Tool);
        UpdateQuenchContact(Work,Now);
        if(QuenchContactAt>=0)Heat*=FMath::Exp(-1.7f*float(Now-QuenchContactAt));
    }
    Blank->SetRelativeTransform(Work);BlankMaterial->SetScalarParameterValue(TEXT("Heat"),Heat);
    UpdateThermalEffects(DeltaTime,Heat,Work,Now);
    const FTransform Tong=TongFrame(Work);Hammer->SetRelativeTransform(Tool);Tongs->SetRelativeTransform(Tong);PoseArms(Tool,Tong);
    FVector2D UV;float Life=0;const bool bTarget=FinishAt<0&&System->Target(UV,Life);
    HeatRing->SetVisibility(bTarget);if(bTarget){HeatRing->SetRelativeLocation(Point(UV)+FVector(0,0,.10));HeatRing->SetRelativeScale3D(FVector(Life));}
    AimRing->SetVisibility(FinishAt<0);AimRing->SetRelativeLocation(Point(Aim)+FVector(0,0,.16));
}
void AForgeInteraction::Contact()
{
    const FVector Hit=Point(StrikeAim);bLastHit=System->Strike(StrikeIndex,StrikeAim,FVector2D(1.85/24.,1.85/60.));LastFeedback=FPlatformTime::Seconds();
    // A failed timed strike can still physically touch the blank/anvil and make a quieter knock.
    const bool OnBlade=FMath::Abs(Hit.Y-22)<=2.5;
    const FVector Surface(Hit.X,Hit.Y,OnBlade?91.95:91.0);
    if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,GetActorTransform().TransformPosition(Surface),bLastHit?.6f:.3f,bLastHit?1.f:.86f);
    if(OnBlade)
    {
        EmitHotImpact(Surface);
    }
}
void AForgeInteraction::PoseArms(const FTransform& RightTool,const FTransform& LeftTool)
{
    // Native +X is anatomical right. The camera looks along station +Y, so its
    // screen-right is -X. Rotate the BODY, keeping both hands' native handedness.
    const FTransform Torso(FQuat(FVector::UpVector,PI),BodyOrigin);
    Arms->SetRelativeTransform(Torso);
    for(int32 I=0;I<Reference.Num();++I)Pose[I]=Reference[I]*Torso;
    SolveArm(true,Hands[1].Grip*RightTool);SolveArm(false,Hands[0].Grip*LeftTool);
    Arms->CommitStationPose(Pose,ArmBoundsBones);
}
void AForgeInteraction::SolveArm(bool Right,const FTransform& Hand)
{
    auto& H=Hands[Right?1:0];const auto& Ref=Arms->GetSkinnedAsset()->GetRefSkeleton();
    const FVector Target=Hand.GetLocation();FVector Shoulder=Pose[H.Upper].GetLocation();
    const float L1=FVector::Distance(Reference[H.Upper].GetLocation(),Reference[H.Lower].GetLocation());
    const float L2=FVector::Distance(Reference[H.Lower].GetLocation(),Reference[H.Hand].GetLocation());
    const FQuat HandDeform=Hand.GetRotation()*Reference[H.Hand].GetRotation().Inverse();
    const FVector RefUpper=Reference[H.Lower].GetLocation()-Reference[H.Upper].GetLocation();
    const FVector RefLower=Reference[H.Hand].GetLocation()-Reference[H.Lower].GetLocation();
    // The native shoulder openings extend 9.32 cm from their joints. Keep their
    // complete surfaces outside the corresponding camera side plane, with margin.
    const FQuat View=Camera->GetRelativeRotation().Quaternion();
    const FVector CameraOrigin=Camera->GetRelativeLocation();
    const FVector Outward=View.RotateVector(FVector::YAxisVector)*(Right?1.0:-1.0);
    const FVector Forward=View.RotateVector(FVector::XAxisVector);
    const FVector Clearance=(Outward-Forward*FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView)*.5)).GetSafeNormal();
    constexpr double ShoulderMargin=10.5,ElbowReserve=1.0;
    FVector Elbow,LowerDirection;
    FQuat LowerDeform,UpperDeform;
    constexpr double HammerPronation=PI*.5;
    if(Right)
    {
        const FVector NativeLower=RefLower.GetSafeNormal();
        const FVector NativeHinge=(RefUpper^RefLower).GetSafeNormal();
        const FVector WristBendAxis=HandDeform.RotateVector(FQuat(NativeLower,FMath::DegreesToRadians(15.0)).RotateVector(NativeHinge));
        const FQuat WristAligned=FQuat(WristBendAxis,FMath::DegreesToRadians(30.0))*HandDeform;
        LowerDirection=WristAligned.RotateVector(NativeLower);
        // Separate forearm pronation from elbow flexion. The old shortest swing
        // could put the humerus on the hyperextended side of the native hinge.
        LowerDeform=FQuat(LowerDirection,HammerPronation)*WristAligned;
        const FVector Hinge=LowerDeform.RotateVector(NativeHinge);
        Elbow=Target-LowerDirection*L2;
        const FVector WantedUpper=(Elbow-Shoulder).GetSafeNormal();
        const FVector FlexTangent=LowerDirection^Hinge;
        const double WantedFlex=FMath::Atan2(WantedUpper|FlexTangent,WantedUpper|LowerDirection);
        // Reserve enough shoulder-to-wrist reach for the camera clearance before
        // flexing. This changes flexion, never bone length or the hinge's side.
        const double RequiredReach=FMath::Max(0.0,ShoulderMargin-((Target-CameraOrigin)|Clearance))+ElbowReserve;
        const double ReachFlex=FMath::Acos(FMath::Clamp((RequiredReach*RequiredReach-L1*L1-L2*L2)/(2.0*L1*L2),-1.0,1.0));
        const double MaxFlex=FMath::Min(FMath::DegreesToRadians(110.0),ReachFlex);
        const double Flex=FMath::Clamp(WantedFlex,FMath::Min(FMath::DegreesToRadians(45.0),MaxFlex),MaxFlex);
        const double NativeFlex=FMath::Acos(FMath::Clamp(RefUpper.GetSafeNormal()|NativeLower,-1.0,1.0));
        UpperDeform=FQuat(Hinge,NativeFlex-Flex)*LowerDeform;
        Shoulder=Elbow-UpperDeform.RotateVector(RefUpper);

        // If the open shoulder reaches the view, swing the WHOLE bent chain
        // around the fixed wrist. Moving its shoulder independently would break
        // the shared hinge frame again and twist the elbow blend weights.
        const FVector Support=Shoulder-Target;
        const FVector SupportDirection=Support.GetSafeNormal();
        const double SideLimit=FMath::Clamp((ShoulderMargin-((Target-CameraOrigin)|Clearance))/Support.Size(),-1.0,1.0);
        if((SupportDirection|Clearance)<SideLimit)
        {
            const FVector Tangent=(SupportDirection-Clearance*(SupportDirection|Clearance)).GetSafeNormal();
            const FVector SafeDirection=Clearance*SideLimit+Tangent*FMath::Sqrt(FMath::Max(0.0,1.0-SideLimit*SideLimit));
            const FQuat ChainSwing=FQuat::FindBetweenNormals(SupportDirection,SafeDirection);
            Shoulder=Target+ChainSwing.RotateVector(Support);
            Elbow=Target+ChainSwing.RotateVector(Elbow-Target);
            LowerDirection=ChainSwing.RotateVector(LowerDirection);
            LowerDeform=ChainSwing*LowerDeform;UpperDeform=ChainSwing*UpperDeform;
        }
    }
    else
    {
        // Preserve the existing tong-arm solve.
        const FVector NeutralForearm=HandDeform.RotateVector(RefLower.GetSafeNormal());
        const FVector ReachAxis=(Target-Shoulder).GetSafeNormal();
        const float Bend=FMath::Acos(FMath::Clamp(float(NeutralForearm|ReachAxis),-1.f,1.f));
        const float BendShare=Bend>KINDA_SMALL_NUMBER?FMath::Min(1.f,FMath::DegreesToRadians(12.f)/Bend):0;
        LowerDirection=FQuat::Slerp(FQuat::Identity,FQuat::FindBetweenNormals(NeutralForearm,ReachAxis),BendShare).RotateVector(NeutralForearm);
        const double ReachLimit=FMath::Clamp((((Target-CameraOrigin)|Clearance)+L1-ShoulderMargin-ElbowReserve)/L2,-1.0,1.0);
        if((LowerDirection|Clearance)>ReachLimit)
        {
            const FVector Tangent=(LowerDirection-Clearance*(LowerDirection|Clearance)).GetSafeNormal();
            LowerDirection=Clearance*ReachLimit+Tangent*FMath::Sqrt(FMath::Max(0.0,1.0-ReachLimit*ReachLimit));
        }
        Elbow=Target-LowerDirection*L2;
        FVector Support=(Shoulder-Elbow).GetSafeNormal();
        const double SideLimit=FMath::Clamp((ShoulderMargin-((Elbow-CameraOrigin)|Clearance))/L1,-1.0,1.0);
        if((Support|Clearance)<SideLimit)
        {
            const FVector Tangent=(Support-Clearance*(Support|Clearance)).GetSafeNormal();
            Support=Clearance*SideLimit+Tangent*FMath::Sqrt(FMath::Max(0.0,1.0-SideLimit*SideLimit));
        }
        Shoulder=Elbow+Support*L1;
        LowerDeform=FQuat::FindBetweenNormals(NeutralForearm,LowerDirection)*HandDeform;
        UpperDeform=FQuat::FindBetweenNormals(LowerDeform.RotateVector(RefUpper.GetSafeNormal()),(Elbow-Shoulder).GetSafeNormal())*LowerDeform;
    }
    // Shoulder skin also blends clavicle and upper-arm helpers. Translating the
    // clavicle while leaving its old rotation tears this blend around the opening.
    const FVector ClavicleOffset=Reference[H.Clavicle].GetLocation()-Reference[H.Upper].GetLocation();
    Pose[H.Clavicle]=FTransform((UpperDeform*Reference[H.Clavicle].GetRotation()).GetNormalized(),Shoulder+UpperDeform.RotateVector(ClavicleOffset),Reference[H.Clavicle].GetScale3D());
    Pose[H.Upper]=FTransform((UpperDeform*Reference[H.Upper].GetRotation()).GetNormalized(),Shoulder,Reference[H.Upper].GetScale3D());
    Pose[H.Lower]=FTransform((LowerDeform*Reference[H.Lower].GetRotation()).GetNormalized(),Elbow,Reference[H.Lower].GetScale3D());
    Pose[H.Hand]=FTransform(Hand.GetRotation(),Target,Reference[H.Hand].GetScale3D());
    static const FName RightLowerTwist01(TEXT("lowerarm_twist_01_r")),RightLowerTwist02(TEXT("lowerarm_twist_02_r"));
    for(int32 I:H.Bones)
    {
        if(I==H.Clavicle||I==H.Upper||I==H.Lower||I==H.Hand)continue;
        const int32 Parent=Ref.GetParentIndex(I);FTransform Local=LocalReference[I];
        if(Right&&Parent==H.Lower&&(Ref.GetBoneName(I)==RightLowerTwist01||Ref.GetBoneName(I)==RightLowerTwist02))
        {
            // Only the axial pronation is distributed, in component space.
            // Never fractionally blend the wrist bend or multiply cumulative
            // twist by an already twisted parent (these helpers are siblings).
            const FVector Offset=Reference[I].GetLocation()-Reference[H.Lower].GetLocation();
            const double Along=FMath::Clamp((Offset|RefLower)/RefLower.SizeSquared(),0.0,1.0);
            const FQuat Deform=FQuat(LowerDirection,-HammerPronation*Along)*LowerDeform;
            Pose[I]=FTransform((Deform*Reference[I].GetRotation()).GetNormalized(),Elbow+Deform.RotateVector(Offset),Reference[I].GetScale3D());
            continue;
        }
        if(const FQuat* Finger=Fingers.Find(I))Local.SetRotation(*Finger);
        Pose[I]=Local*Pose[Parent];
    }
}
void AForgeInteraction::RestorePlayer()
{
    RestoreQuenchWater();
    if(auto* Player=PC.Get())
    {
        if(bHeldInput){Player->SetIgnoreMoveInput(false);Player->SetIgnoreLookInput(false);bHeldInput=false;Player->FlushPressedKeys();}
        if(bHidPawn){Player->HiddenActors.Remove(WorkingPawn.Get());bHidPawn=false;}
        if(Player->GetViewTarget()==this)Player->SetViewTargetWithBlend(PreviousView.IsValid()?PreviousView.Get():Player->GetPawn(),.25f,VTBlend_Cubic);
    }
    if(Prompt){Prompt->RemoveFromParent();Prompt=nullptr;}
}
void AForgeInteraction::Stop(bool bReturnPanel)
{
    if(!bRunning)return;bRunning=false;bReturning=true;
    if(System&&System->Active()){FString Reason;System->Finish(Reason);}
    SetActorTickEnabled(false);RestorePlayer();
    if(auto* OwnerHUD=HUD.Get())OwnerHUD->CompleteWorldForging(this,bReturnPanel&&Station.IsValid()&&!Station->IsFalling());
    SetLifeSpan(.3f);
}
void AForgeInteraction::EndPlay(const EEndPlayReason::Type Reason)
{
    RestoreQuenchWater();
    if(bRunning){bRunning=false;if(System&&System->Active()){FString Why;System->Finish(Why);}RestorePlayer();}
    if(Load.IsValid())Load->CancelHandle();Super::EndPlay(Reason);
}
