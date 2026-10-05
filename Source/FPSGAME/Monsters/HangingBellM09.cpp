#include "HangingBellM09.h"
#include "M09ResonanceDamage.h"
#include "M09GazeParameters.h"
#include "M09ClawParameters.h"
#include "M09CeilingRoute.h"
#include "M09AnimInstance.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "Engine/StaticMesh.h"
#include "Engine/DamageEvents.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
// Translation retains V19's double speed. Turning uses its own faster cadence.
constexpr float CeilingLocomotionRate=2.f;
constexpr float TurnDegreesPerSecond=120.f;
constexpr float CeilingTurnAnimationRate=TurnDegreesPerSecond/30.f;
constexpr float AuthoredGripStepSeconds=.6f;
constexpr float ResonanceLock=.80f;
constexpr float ResonanceFirstPulse=1.10f;
constexpr float ResonancePulseGap=.70f;
constexpr int32 ResonancePulseCount=6;
constexpr float ResonanceDuration=5.60f;
constexpr float ResonanceRange=2000.f;
constexpr float ResonanceConeCos=.64278761f; // 50 degree half-angle.
FName NameFor(EM09State State)
{
 switch(State){
 case EM09State::Travel:case EM09State::Returning:return TEXT("Travel");
 case EM09State::SwingLeft:return TEXT("SwingLeft");case EM09State::SwingRight:return TEXT("SwingRight");
 case EM09State::Resonance:return TEXT("Resonance");case EM09State::Gaze:return TEXT("Gaze");
 case EM09State::Claw:return TEXT("Claw");case EM09State::Stagger:return TEXT("Stagger");
 case EM09State::Dying:case EM09State::Corpse:return TEXT("Death");default:return TEXT("Idle");}
}
float Smooth(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
}
AHangingBellM09::AHangingBellM09()
{
 PrimaryActorTick.bCanEverTick=true;bReplicates=true;SetReplicateMovement(true);
 Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
 Corpse=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
 Corpse->Rig=EMonsterCorpseRig::HangingBell;
 Voice=CreateDefaultSubobject<UAudioComponent>(TEXT("OrganVoice"));Voice->SetupAttachment(GetMesh());Voice->bAutoActivate=false;
 Voice->bOverrideAttenuation=true;Voice->AttenuationOverrides.bAttenuate=true;
 Voice->AttenuationOverrides.bSpatialize=true;Voice->AttenuationOverrides.FalloffDistance=2600.f;
 Beam=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GazeBeam"));
 Charge=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("EyeCharge"));
 for(int32 I=0;I<3;++I)Waves.Add(CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("MembranePulse%d"),I)));
 TArray<UStaticMeshComponent*> FX={Beam,Charge};for(const auto& W:Waves)FX.Add(W);
 for(auto* C:FX){C->SetupAttachment(GetRootComponent());C->SetAbsolute(true,true,true);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);C->SetVisibility(false);}
 static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
 static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
 Beam->SetStaticMesh(Cylinder.Object);Charge->SetStaticMesh(Sphere.Object);
 CreateGazeFX();
 static ConstructorHelpers::FObjectFinder<USkeletalMesh> MeshAsset(TEXT("/Game/Monsters/HangingBellM09/V04/SK_M09.SK_M09"));VisualMesh=MeshAsset.Object;
 static ConstructorHelpers::FObjectFinder<UPhysicsAsset> HitAsset(TEXT("/Game/Monsters/HangingBellM09/V23/PA_M09_HitSurface.PA_M09_HitSurface"));HitSurfacePhysics=HitAsset.Object;
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> Mat(TEXT("/Game/Monsters/HangingBellM09/V04/Materials/M_M09_Energy.M_M09_Energy"));EnergyMaterial=Mat.Object;
 static ConstructorHelpers::FObjectFinder<UStaticMesh> Wave(TEXT("/Game/Monsters/HangingBellM09/V07/FX/SM_M09_ResonanceWave_V07.SM_M09_ResonanceWave_V07"));WaveMesh=Wave.Object;
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> ResonanceMat(TEXT("/Game/Monsters/HangingBellM09/V07/Materials/M_M09_Resonance_V07.M_M09_Resonance_V07"));ResonanceMaterial=ResonanceMat.Object;
 for(const TCHAR* ClipRole:{TEXT("Idle"),TEXT("Travel"),TEXT("SwingLeft"),TEXT("SwingRight"),TEXT("Resonance"),TEXT("Gaze"),TEXT("Claw"),TEXT("Stagger"),TEXT("Death")})
 {
  const FString AssetPath=FString::Printf(TEXT("/Game/Monsters/HangingBellM09/V04/Animations/A_M09_%s.A_M09_%s"),ClipRole,ClipRole);
  ConstructorHelpers::FObjectFinder<UAnimSequence> A(*AssetPath);if(A.Object)Clips.Add(FName(ClipRole),A.Object);
 }
 for(const TCHAR* ClipRole:{TEXT("SwingLeft"),TEXT("SwingRight"),TEXT("Resonance"),TEXT("Gaze"),TEXT("Claw"),TEXT("Stagger"),TEXT("Death")})
 {
  const FString AssetPath=FString::Printf(TEXT("/Game/Monsters/HangingBellM09/V04/Audio/S_M09_%s.S_M09_%s"),ClipRole,ClipRole);
  ConstructorHelpers::FObjectFinder<USoundBase> S(*AssetPath);if(S.Object)Sounds.Add(FName(ClipRole),S.Object);
 }
 static ConstructorHelpers::FObjectFinder<UAnimSequence> ResonanceClip(TEXT("/Game/Monsters/HangingBellM09/V07/Animations/A_M09_Resonance_V07.A_M09_Resonance_V07"));
 if(ResonanceClip.Object)Clips.Add(TEXT("Resonance"),ResonanceClip.Object);
 static ConstructorHelpers::FObjectFinder<USoundBase> ResonanceSound(TEXT("/Game/Monsters/HangingBellM09/V07/Audio/S_M09_Resonance_V07.S_M09_Resonance_V07"));
 if(ResonanceSound.Object)Sounds.Add(TEXT("Resonance"),ResonanceSound.Object);
 static ConstructorHelpers::FObjectFinder<UAnimSequence> GazeClip(TEXT("/Game/Monsters/HangingBellM09/V08/Animations/A_M09_Gaze_V08.A_M09_Gaze_V08"));
 if(GazeClip.Object)Clips.Add(TEXT("Gaze"),GazeClip.Object);
 static ConstructorHelpers::FObjectFinder<USoundBase> GazeSound(TEXT("/Game/Monsters/HangingBellM09/V08/Audio/S_M09_Gaze_V08.S_M09_Gaze_V08"));
 if(GazeSound.Object)Sounds.Add(TEXT("Gaze"),GazeSound.Object);
 GetCapsuleComponent()->InitCapsuleSize(85.f,137.f);
 GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
 GetCapsuleComponent()->SetCanEverAffectNavigation(false);
 GetMesh()->SetCollisionObjectType(ECC_Pawn);GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
 GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
 GetMesh()->SetCanEverAffectNavigation(false);GetMesh()->SetAnimInstanceClass(UM09AnimInstance::StaticClass());
 GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
 GetCharacterMovement()->GravityScale=0;GetCharacterMovement()->bOrientRotationToMovement=false;
 GetCharacterMovement()->DefaultLandMovementMode=MOVE_None;GetCharacterMovement()->DefaultWaterMovementMode=MOVE_None;
 bUseControllerRotationYaw=false;static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));AIControllerClass=AI.Class?AI.Class.Get():AMonsterAIController::StaticClass();
 AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("HangingBellM09"));Tags.Add(TEXT("KnockbackImmune"));
}
void AHangingBellM09::AlignVisual()
{
 if(!VisualMesh)return;GetMesh()->SetSkeletalMeshAsset(VisualMesh);RefreshHitPhysics();
 const auto& Ref=VisualMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
 for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
 const int32 E=Ref.FindBoneIndex(TEXT("eye_04")),F=Ref.FindBoneIndex(TEXT("eye_05")),C=Ref.FindBoneIndex(TEXT("eye_crown"));
 float Yaw=0;if(E>=0&&F>=0&&C>=0)Yaw=-((Frames[E].GetLocation()+Frames[F].GetLocation())*.5-Frames[C].GetLocation()).Rotation().Yaw;
 GetMesh()->SetRelativeRotation(FRotator(0,Yaw,0));
 const auto Bounds=VisualMesh->GetBounds();GetMesh()->SetRelativeLocation(FVector(0,0,142.f-Bounds.Origin.Z-Bounds.BoxExtent.Z));
 for(int32 I=0;I<2;++I)
 {
  const int32 B=Ref.FindBoneIndex(I==0?TEXT("big_hand_L"):TEXT("big_hand_R"));
  if(B>=0){GripRest[I]=GetMesh()->GetRelativeTransform().TransformPosition(Frames[B].GetLocation());GripClearance[I]=143.f-GripRest[I].Z;}
 }
 for(const auto& Cmp:Waves){Cmp->SetStaticMesh(WaveMesh);Cmp->SetMaterial(0,ResonanceMaterial);}
}
void AHangingBellM09::OnConstruction(const FTransform& T){Super::OnConstruction(T);AlignVisual();}
void AHangingBellM09::BeginPlay()
{
 Super::BeginPlay();AlignVisual();GetCharacterMovement()->DisableMovement();
 // Enforce for existing Blueprint instances as well. Skeletal hit queries stay
 // enabled, including V23's membranes; only the locomotion capsule is disabled.
 GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 if(GetNetMode()!=NM_DedicatedServer)
  for(const auto& W:Waves)WaveMaterials.Add(W->CreateDynamicMaterialInstance(0,ResonanceMaterial));
 InitializeGazeFX();
 GetMesh()->AddTickPrerequisiteActor(this);GetMesh()->AddTickPrerequisiteComponent(Combat);
 if(HasAuthority())
 {
  MaxHealth*=float(MonsterCoreStats::HealthMultiplier());Health=MaxHealth;
  FVector Center=CeilingCenter();AM09CeilingRoute* CeilingRoute=nullptr;
  // Keep a valid spawn where it was placed; a missing authored route is not a failed hang.
  bool Placed=AM09CeilingRoute::ClearBody(GetWorld(),Center,this);
  if(Placed)CeilingRoute=AM09CeilingRoute::FindRoute(GetWorld(),Center);
  else Placed=AM09CeilingRoute::FindPlacement(GetWorld(),GetActorLocation()-FVector(0,0,137),this,Center,CeilingRoute);
  if(Placed){SetActorLocation(Center-FVector(0,0,143));InitializeHang(CeilingRoute);}
  else{Health=0;EnterDeath();}
 }
 PresentState();
}
void AHangingBellM09::InitializeHang(AM09CeilingRoute* R)
{
 if(!HasAuthority()||!VisualMesh)return;Route=R;Home=GetActorLocation();DesiredYaw=GetActorRotation().Yaw;
 CeilingSurfaceHeight=CeilingCenter().Z;
 const auto& Ref=VisualMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
 for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
 for(int32 I=0;I<2;++I)
 {
  const int32 B=Ref.FindBoneIndex(I==0?TEXT("big_hand_L"):TEXT("big_hand_R"));
  GripRotations[I]=B>=0?(Frames[B]*GetMesh()->GetComponentTransform()).Rotator():GetActorRotation();
  GripRestRotation[I]=GetActorQuat().Inverse()*GripRotations[I].Quaternion();
  GripTargets[I]=GetActorTransform().TransformPosition(GripRest[I]);
  FQuat Rotation;
  if(ResolveCeilingGrip(GetActorTransform(),I,GripTargets[I],Rotation))GripRotations[I]=Rotation.Rotator();
 }
 bInitialized=true;ForceNetUpdate();
}
void AHangingBellM09::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
 Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AHangingBellM09,Health);DOREPLIFETIME(AHangingBellM09,State);
 DOREPLIFETIME(AHangingBellM09,GripTargets);DOREPLIFETIME(AHangingBellM09,GripRotations);
 DOREPLIFETIME(AHangingBellM09,StateStartedAt);DOREPLIFETIME(AHangingBellM09,LockedAim);
 DOREPLIFETIME(AHangingBellM09,StaggerReleaseSide);DOREPLIFETIME(AHangingBellM09,ReactionSeconds);
 DOREPLIFETIME(AHangingBellM09,ResonanceOrigin);DOREPLIFETIME(AHangingBellM09,ResonanceDirection);
 DOREPLIFETIME(AHangingBellM09,GazeDirection);DOREPLIFETIME(AHangingBellM09,CeilingAnimationRate);
}
void AHangingBellM09::OnRep_State()
{
 StateSeconds=GetWorld()->GetGameState()?FMath::Max(0.,GetWorld()->GetGameState()->GetServerWorldTimeSeconds()-StateStartedAt):0.;
 RefreshHitPhysics();PresentState();
}
UAnimSequence* AHangingBellM09::Clip(FName Key) const{auto* P=Clips.Find(Key);return P?P->Get():nullptr;}
FName AHangingBellM09::StateClip() const{return NameFor(State);}
void AHangingBellM09::Sample(float T){if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->SetCombatTime(T);}
void AHangingBellM09::PresentState()
{
 Voice->Stop();ClearGazeFX();for(const auto& W:Waves)W->SetVisibility(false);
 if((State==EM09State::Dying||State==EM09State::Corpse)&&Corpse->TryStartSoftDeath(GetMesh()))return;
 if(State==EM09State::Corpse)return;
 const bool Loop=State==EM09State::Idle||State==EM09State::Travel||State==EM09State::Returning;
 if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
 {
  const bool Locomotion=State==EM09State::Travel||State==EM09State::Returning;
  FMonsterClipTransition Settings;
  Settings.InitialPlayRate=Locomotion?CeilingAnimationRate:1.f;
  const float BlendSeconds=State==EM09State::Resonance?.06f:Locomotion?.14f/CeilingAnimationRate:.14f;
  A->TransitionTo(Clip(StateClip()),Loop,!Loop,BlendSeconds,Settings);
 }
 if(auto* S=Sounds.Find(StateClip());S&&*S)
 {
  Voice->SetWorldLocation(State==EM09State::Resonance?ResonanceOrigin:Eye());
  Voice->SetSound(*S);Voice->Play(StateSeconds);
 }
}
void AHangingBellM09::SetState(EM09State Next)
{
 State=Next;StateSeconds=0;StateStartedAt=GetWorld()->GetTimeSeconds();
 if(State==EM09State::Resonance)CaptureResonanceAim();
 if(State==EM09State::Gaze){bGazeLocked=false;CaptureGazeAim();}
 PresentState();ForceNetUpdate();
}
FVector AHangingBellM09::Eye() const{return GetMesh()->GetSocketLocation(TEXT("eye_01"));}
FVector AHangingBellM09::GetPawnViewLocation() const{return VisualMesh?Eye():GetActorLocation();}
bool AHangingBellM09::HasAttackSight(const APawn* P) const
{
 if(!IsValid(P))return false;FHitResult H;FCollisionQueryParams Q(SCENE_QUERY_STAT(M09Sight),false,this);Q.AddIgnoredActor(P);
 return !GetWorld()->LineTraceSingleByChannel(H,Eye(),P->GetActorLocation()+FVector(0,0,35),ECC_Visibility,Q);
}
void AHangingBellM09::SetLocomotion(bool Moving,bool Returning)
{
 if(Busy())return;bWantsMove=Moving;bReturning=Returning;
 if(Moving&&!bGripMoving)UpdateCeilingAnimationRate();
 const auto Next=Moving?(Returning?EM09State::Returning:EM09State::Travel):EM09State::Idle;
 if(State!=Next)SetState(Next);
}
void AHangingBellM09::StopCeiling(){bWantsMove=false;Path.Reset();if(!Busy())SetLocomotion(false);}
void AHangingBellM09::NavigateCeiling(FVector Destination,bool Returning)
{
 if(Busy()||!bInitialized)return;
 // Let the current grip land without immediately beginning another step.
 // CanAttack waits for both grips; continuous travel otherwise starves it.
 if(!Returning&&SelectAttack(Target.Get())!=EM09State::Idle){StopCeiling();return;}
 DesiredYaw=(Destination-GetActorLocation()).Rotation().Yaw;
 if(PathAge>=.65f&&(Path.IsEmpty()||FVector::DistSquared2D(Destination,LastDestination)>FMath::Square(90.f)))
 {
  PathAge=0;LastDestination=Destination;
  if(!IsValid(Route)||!Route->FindPath(this,Destination,Path))
   AM09CeilingRoute::FindLocalPath(this,Destination,Path);
 }
 SetLocomotion(!Path.IsEmpty()||FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,DesiredYaw))>4.f,Returning);
}
void AHangingBellM09::UpdateCeilingAnimationRate()
{
 const bool Turning=FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,DesiredYaw))>4.f;
 const float Rate=Turning?CeilingTurnAnimationRate:CeilingLocomotionRate;
 if(CeilingAnimationRate!=Rate){CeilingAnimationRate=Rate;ForceNetUpdate();}
}
bool AHangingBellM09::ResolveCeilingGrip(const FTransform& Frame,int32 Side,FVector& Position,FQuat& Rotation) const
{
 const float SurfaceOffset=CeilingSurfaceHeight-CeilingCenter().Z;
 const FVector Center=Frame.GetLocation()+FVector(0,0,143+SurfaceOffset);
 const FVector Desired=Frame.TransformPosition(GripRest[Side])+FVector(0,0,GripClearance[Side]+SurfaceOffset);
 // Reuse the inward reach used at spawn when turning beside a roof edge or beam.
 for(float Width:{1.f,.75f,.5f,.25f,0.f})
 {
  FVector Contact,Normal;
  if(!AM09CeilingRoute::FindSupport(GetWorld(),FMath::Lerp(Center,Desired,Width),this,Contact,&Normal))continue;
  Position=Contact-FVector(0,0,GripClearance[Side]);
  Rotation=(FQuat::FindBetweenNormals(FVector::DownVector,Normal)*Frame.GetRotation()*GripRestRotation[Side]).GetNormalized();
  return true;
 }
 return false;
}
void AHangingBellM09::FollowCeilingHeight(float Dt)
{
 FVector Position=GetActorLocation();
 // Exponential following avoids frame-rate-dependent snaps at a roof step.
 // Cap the vertical speed while the alternating grips finish their own arcs.
 const float Delta=(CeilingSurfaceHeight-143.f-Position.Z)*(1.f-FMath::Exp(-10.f*FMath::Max(0.f,Dt)));
 if(FMath::Abs(Delta)<KINDA_SMALL_NUMBER)return;
 Position.Z+=FMath::Clamp(Delta,-240.f*Dt,240.f*Dt);
 SetActorLocation(Position,false);
}
void AHangingBellM09::TickGrips(float Dt,bool Moving)
{
 if(!bInitialized)return;
 if(bGripMoving)
 {
  GripClock=FMath::Min(1.f,GripClock+Dt*CeilingAnimationRate/AuthoredGripStepSeconds);
  const float A=Smooth(GripClock);
  GripTargets[GripSide]=FMath::Lerp(GripStart,GripEnd,A)-FVector(0,0,12.f*FMath::Sin(PI*GripClock));
  GripRotations[GripSide]=FQuat::Slerp(GripRotationStart,GripRotationEnd,A).Rotator();
  if(GripClock>=1.f){bGripMoving=false;GripSide=1-GripSide;}
 }
 if(!bGripMoving&&Moving)
 {
  // Pick the rate at grip boundaries so an airborne hand keeps a continuous arc.
  UpdateCeilingAnimationRate();
  const float StepSeconds=AuthoredGripStepSeconds/CeilingAnimationRate;
  const FVector Travel=Path.IsEmpty()?FVector::ZeroVector:((Path[0]-CeilingCenter())*FVector(1,1,0)).GetClampedToMaxSize(CeilingSpeed*CeilingLocomotionRate*StepSeconds);
  const float Yaw=FMath::FixedTurn(GetActorRotation().Yaw,DesiredYaw,TurnDegreesPerSecond*StepSeconds*(4.f/3.f));
  const FTransform Future(FRotator(0,Yaw,0),GetActorLocation()+Travel);
  FVector End;FQuat Rotation;
  if(ResolveCeilingGrip(Future,GripSide,End,Rotation))
  {
   GripStart=GripTargets[GripSide];GripEnd=End;GripClock=0;bGripMoving=true;
   GripRotationStart=GripRotations[GripSide].Quaternion();
   GripRotationEnd=Rotation;
  }
  else{bWantsMove=false;Path.Reset();}
 }
}
void AHangingBellM09::TickCeiling(float Dt)
{
 if(!HasAuthority()||Dead()||!bInitialized)return;PathAge+=Dt;SupportAge+=Dt;
 const FVector Before=GetActorLocation();
 if(SupportAge>=.15f)
 {
  SupportAge=0;bool Valid[2];
  for(int32 I=0;I<2;++I)Valid[I]=HandIKWeight(I)>.9f&&AM09CeilingRoute::Supported(GetWorld(),GripTargets[I]+FVector(0,0,GripClearance[I]),this);
  // A hand in transit does not count as support; the other one must still be attached.
  const bool Support=bGripMoving?Valid[1-GripSide]:(Valid[0]||Valid[1]);
  if(!Support){Health=0;EnterDeath();return;}
 }
 if(Busy())
 {
  TickGrips(Dt,false);FollowCeilingHeight(Dt);
  GetCharacterMovement()->Velocity=(GetActorLocation()-Before)/FMath::Max(.001f,Dt);return;
 }
 TickGrips(Dt,bWantsMove);
 if(!bWantsMove)
 {
  FollowCeilingHeight(Dt);GetCharacterMovement()->Velocity=(GetActorLocation()-Before)/FMath::Max(.001f,Dt);return;
 }
 const float Yaw=FMath::FixedTurn(GetActorRotation().Yaw,DesiredYaw,TurnDegreesPerSecond*Dt);SetActorRotation(FRotator(0,Yaw,0));
 if(!Path.IsEmpty())
 {
  const FVector Old=CeilingCenter(),Delta=(Path[0]-Old)*FVector(1,1,0);
  const float Step=FMath::Min(Delta.Size(),CeilingSpeed*CeilingLocomotionRate*Dt);
  FVector Next=Old+Delta.GetSafeNormal()*Step;Next.Z=CeilingSurfaceHeight;
  FVector Contact;
  if(AM09CeilingRoute::FindSupport(GetWorld(),Next,this,Contact))
  {
   CeilingSurfaceHeight=Contact.Z;
   // Never sweep the hanging body's capsule against beams, walls or scenery.
   SetActorLocation(FVector(Next.X,Next.Y,Before.Z),false);
   if(FVector::DistSquared2D(CeilingCenter(),Path[0])<FMath::Square(5.f))Path.RemoveAt(0);
  }
  else StopCeiling();
 }
 FollowCeilingHeight(Dt);
 GetCharacterMovement()->Velocity=(GetActorLocation()-Before)/FMath::Max(.001f,Dt);
 if(Path.IsEmpty()&&FMath::Abs(FMath::FindDeltaAngleDegrees(Yaw,DesiredYaw))<4.f)SetLocomotion(false);
}
float AHangingBellM09::HandIKWeight(int32 Side) const
{
 if(State==EM09State::Corpse)return 0;
 if(State==EM09State::Dying)return 1.f-Smooth((StateSeconds-(Side==0?.18f:.34f))/.15f);
 if(State==EM09State::Stagger&&Side==StaggerReleaseSide)return 1.f-Smooth(StateSeconds/.18f)*(1.f-Smooth((StateSeconds-FMath::Max(.2f,ReactionSeconds-.35f))/.35f));
 return 1.f;
}
bool AHangingBellM09::CanAttack(APawn* P) const
{
 if(Busy()||bGripMoving||GlobalCooldown>0||!bInitialized)return false;
 return SelectAttack(P)!=EM09State::Idle;
}
bool AHangingBellM09::CanGazeReach(const APawn* P) const
{
 return IsValid(P)&&Clip(TEXT("Gaze"))&&!InClawRange(P)&&
  FVector::DistSquared2D(GetActorLocation(),P->GetActorLocation())>=FMath::Square(M09Gaze::MinimumRange)&&
  FVector::DistSquared(Eye(),P->GetActorLocation()+FVector(0,0,35))<=FMath::Square(M09Gaze::Range);
}
EM09State AHangingBellM09::SelectAttack(APawn* P) const
{
 if(!IsValid(P)||!HasAttackSight(P))return EM09State::Idle;
 if(auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return EM09State::Idle;
 // Face the target from the actor centre, including one directly below us.
 const FVector Facing=P->GetActorLocation()-GetActorLocation();
 if(Facing.SizeSquared2D()>FMath::Square(50.f)&&
    FVector::DotProduct(Facing.GetSafeNormal2D(),GetActorForwardVector())<.45f)return EM09State::Idle;
 const FVector Origin=GetMesh()->GetSocketLocation(TEXT("spine_03"));
 const FVector D=P->GetActorLocation()+FVector(0,0,35)-Origin;
 const bool ResonanceReady=Cooldown[1]<=0&&Clip(TEXT("Resonance"))&&D.SizeSquared()<=FMath::Square(ResonanceRange)&&HasResonanceSight(P,Origin);
 if(InClawRange(P))
 {
  if(Cooldown[3]<=0&&CanClawReach(P))return EM09State::Claw;
  return ResonanceReady?EM09State::Resonance:EM09State::Idle;
 }
 const bool GazeReady=Cooldown[2]<=0&&CanGazeReach(P);
 // Use both ranged attacks when ready; gaze takes the first distant opening.
 if(GazeReady&&(!ResonanceReady||LastProductionAttack!=EM09State::Gaze))return EM09State::Gaze;
 return ResonanceReady?EM09State::Resonance:EM09State::Idle;
}
bool AHangingBellM09::StartAttack(APawn* P)
{
 if(!HasAuthority()||Busy()||bGripMoving||GlobalCooldown>0||!bInitialized)return false;
 const EM09State Attack=SelectAttack(P);
 if(Attack==EM09State::Idle)return false;
 Target=P;StopCeiling();HitVictims.Reset();NextPulse=0;bGazeLocked=false;
 Cooldown[Attack==EM09State::Claw?3:Attack==EM09State::Gaze?2:1]=Attack==EM09State::Claw?M09Claw::Cooldown:Attack==EM09State::Gaze?M09Gaze::Cooldown:8.f;
 LockedAim=P->GetActorLocation()+FVector(0,0,35);
 if(Attack!=EM09State::Claw)LastProductionAttack=Attack;
 SetState(Attack);
 if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
 return true;
}
void AHangingBellM09::CaptureResonanceAim()
{
 ResonanceOrigin=GetMesh()->GetSocketLocation(TEXT("spine_03"));
 if(Target.IsValid())LockedAim=Target->GetActorLocation()+FVector(0,0,35);
 ResonanceDirection=(LockedAim-ResonanceOrigin).GetSafeNormal();
 if(ResonanceDirection.IsNearlyZero())ResonanceDirection=GetActorForwardVector();
}
bool AHangingBellM09::HasResonanceSight(const APawn* P,FVector Origin) const
{
 if(!IsValid(P))return false;
 FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(M09ResonanceSight),false,this);Q.AddIgnoredActor(P);
 return !GetWorld()->LineTraceSingleByChannel(Hit,Origin,P->GetActorLocation()+FVector(0,0,35),ECC_Visibility,Q);
}
void AHangingBellM09::Deal(APawn* P,float Damage,bool Magic,FVector Point)
{
 if(!HasAuthority()||Dead()||!IsValid(P)||!P->IsPlayerControlled())return;
 FHitResult H;H.ImpactPoint=H.Location=Point;const FVector D=(P->GetActorLocation()-Eye()).GetSafeNormal();
 UGameplayStatics::ApplyPointDamage(P,Damage,D,H,GetController(),this,Magic?UStatusMagicDamage::StaticClass():UEnemyMeleeDamage::StaticClass());
}
void AHangingBellM09::SweepContact(FVector From,FVector To,float Radius,float Damage)
{
 TArray<FHitResult> Hits;FCollisionQueryParams Q(SCENE_QUERY_STAT(M09OrganStrike),false,this);
 GetWorld()->SweepMultiByChannel(Hits,From,To,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeSphere(Radius),Q);
 for(const auto& H:Hits)
  if(auto* P=Cast<APawn>(H.GetActor());P&&P->IsPlayerControlled()&&!HitVictims.Contains(P)&&HasAttackSight(P))
  {HitVictims.Add(P);Deal(P,Damage,false,H.ImpactPoint);if(Dead()||State==EM09State::Stagger)return;}
}
void AHangingBellM09::ResonancePulse()
{
 // One server-side damage application per player per pulse. Cover is traced from
 // the same locked torso origin that drives the visible shock wave.
 for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=It->Get())if(APawn* P=PC->GetPawn())
 {
  if(auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())continue;
  const FVector Point=P->GetActorLocation()+FVector(0,0,35),D=Point-ResonanceOrigin;
  if(D.SizeSquared()>FMath::Square(ResonanceRange)||
     FVector::DotProduct(D.GetSafeNormal(),ResonanceDirection)<ResonanceConeCos||!HasResonanceSight(P,ResonanceOrigin))continue;
  FHitResult Hit;Hit.Location=Hit.ImpactPoint=Point;
  UGameplayStatics::ApplyPointDamage(P,MagicAttack*.45f,ResonanceDirection,Hit,GetController(),this,UM09ResonanceDamage::StaticClass());
  if(Dead()||State!=EM09State::Resonance)return;
 }
}
void AHangingBellM09::TickAttack(float Previous)
{
 if(!HasAuthority()||State<EM09State::SwingLeft||State>EM09State::Claw)return;
 if(State==EM09State::Gaze&&Target.IsValid()&&
    FVector::DistSquared2D(GetActorLocation(),Target->GetActorLocation())<FMath::Square(M09Gaze::MinimumRange))
 {
  // Close approaches cancel charging/firing before any further damage pulse.
  // The next BT decision chooses claw or resonance using the same near band.
  NextPulse=M09Gaze::PulseCount;GlobalCooldown=.15f;SetState(EM09State::Idle);
  if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
  return;
 }
 const EM09State Attack=State;const float Duration=State==EM09State::Resonance?ResonanceDuration:State==EM09State::Gaze?M09Gaze::Duration:State==EM09State::Claw?M09Claw::Duration:(Clip(StateClip())?Clip(StateClip())->GetPlayLength():3.f);
 const float Lock=State==EM09State::Gaze?M09Gaze::Lock:State==EM09State::Resonance?ResonanceLock:.60f;
 if(State==EM09State::Resonance)
 {
  if(Previous<Lock){CaptureResonanceAim();if(StateSeconds>=Lock)ForceNetUpdate();}
 }
 else if(State==EM09State::Gaze&&!bGazeLocked)
 {
  CaptureGazeAim();
  if(StateSeconds>=M09Gaze::Lock){bGazeLocked=true;ForceNetUpdate();}
 }
 else if(StateSeconds<Lock&&Target.IsValid())LockedAim=Target->GetActorLocation()+FVector(0,0,35);
 if(State==EM09State::Resonance||State==EM09State::Gaze)
 {
  const float First=State==EM09State::Resonance?ResonanceFirstPulse:M09Gaze::FirstPulse;
  const float Gap=State==EM09State::Resonance?ResonancePulseGap:M09Gaze::PulseGap;
  const int32 PulseCount=State==EM09State::Resonance?ResonancePulseCount:M09Gaze::PulseCount;
  while(NextPulse<PulseCount&&StateSeconds>=First+NextPulse*Gap)
  {
   ++NextPulse;if(State==EM09State::Resonance)ResonancePulse();else GazePulse();
   if(State!=Attack||Dead())return;
  }
 }
 else
 {
  const bool Claw=State==EM09State::Claw;
  const float Begin=Claw?M09Claw::ContactBegin:.85f,End=Claw?M09Claw::ContactEnd:1.20f;
  if(StateSeconds>=Begin&&Previous<End)
  {
   // Bounded temporal substeps use the animation clock for actual organ sweeps.
   const float A=FMath::Max(Previous,Begin),B=FMath::Min(StateSeconds,End);
   const int32 Steps=FMath::Clamp(FMath::CeilToInt((B-A)*90),1,12);
   for(int32 I=0;I<=Steps;++I)
   {
    Sample(FMath::Lerp(A,B,float(I)/Steps));GetMesh()->TickAnimation(0,false);GetMesh()->RefreshBoneTransforms();
    for(int32 Hand=0;Hand<(Claw?2:1);++Hand)
    {
     if(Claw)SweepClawContact(Hand,I==0);
     else
     {
      const FVector P=GetMesh()->GetSocketLocation(TEXT("eye_crown"));
      if(I==0)PreviousContact[Hand]=P;
      SweepContact(PreviousContact[Hand],P,35.f,PhysicalAttack*1.25f);
      PreviousContact[Hand]=P;
     }
     if(State!=Attack||Dead())return;
    }
   }
   Sample(StateSeconds);
  }
 }
 if(StateSeconds>=Duration){GlobalCooldown=.55f;SetState(EM09State::Idle);if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();}
}
void AHangingBellM09::UpdateFX()
{
 if(GetNetMode()==NM_DedicatedServer)return;
 UpdateGazeFX();
 if(State==EM09State::Resonance)Voice->SetWorldLocation(ResonanceOrigin);
 for(int32 I=0;I<3;++I)
 {
  // Reuse the three existing components for six pulses, with no runtime spawning.
  const int32 Pulse=StateSeconds>=ResonanceFirstPulse+(I+3)*ResonancePulseGap?I+3:I;
  const float Age=StateSeconds-(ResonanceFirstPulse+ResonancePulseGap*Pulse);
  const bool Active=State==EM09State::Resonance&&Age>=0.f&&Age<.90f;
  Waves[I]->SetVisibility(Active);
  if(Active)
  {
   const float Radius=FMath::Lerp(55.f,ResonanceRange,Smooth(Age/.32f));
   Waves[I]->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(ResonanceDirection).ToQuat(),ResonanceOrigin,FVector(Radius/100.f)));
   if(WaveMaterials.IsValidIndex(I)&&WaveMaterials[I])
   {
    const float FadeIn=Smooth(Age/.14f),FadeOut=1.f-Smooth((Age-.24f)/.66f);
    WaveMaterials[I]->SetScalarParameterValue(TEXT("PulseAlpha"),FadeIn*FadeOut);
    WaveMaterials[I]->SetScalarParameterValue(TEXT("PulsePhase"),Pulse*1.7f+Age*3.5f);
   }
  }
 }
}
void AHangingBellM09::Tick(float Dt)
{
 Super::Tick(Dt);const float Previous=StateSeconds;StateSeconds+=Dt;
 if(HasAuthority()){for(float& C:Cooldown)C=FMath::Max(0.f,C-Dt);GlobalCooldown=FMath::Max(0.f,GlobalCooldown-Dt);TickCeiling(Dt);}
 if(State==EM09State::Travel||State==EM09State::Returning)
  if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->SetLocomotionRate(CeilingAnimationRate);
 if(State>=EM09State::SwingLeft&&State<=EM09State::Claw){Sample(StateSeconds);TickAttack(Previous);}
 if(State==EM09State::Stagger&&HasAuthority()&&StateSeconds>=ReactionSeconds)Combat->FinishReaction();
 if(State==EM09State::Dying)
 {
  Sample(FMath::Min(StateSeconds,.6f));
  if(HasAuthority())
  {
   Corpse->RecordDeathPose(GetMesh(),Dt);
   if(StateSeconds>=.6f&&!Corpse->WasAttempted())
   {
    if(Corpse->Start(GetMesh(),FVector(0,0,-110))){SetState(EM09State::Corpse);SetActorTickEnabled(false);}
    else
    {
     // With the shared physics budget exhausted, fall the frozen body to real support.
     GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
     GetCharacterMovement()->DefaultLandMovementMode=MOVE_Walking;
     GetCharacterMovement()->GravityScale=1;GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    }
   }
   if(Corpse->WasAttempted()&&!GetMesh()->IsSimulatingPhysics()&&GetCharacterMovement()->IsMovingOnGround())
   {Corpse->FreezeAnimatedPose(GetMesh());SetState(EM09State::Corpse);GetCharacterMovement()->DisableMovement();SetActorTickEnabled(false);}
  }
 }
 UpdateFX();
}
void AHangingBellM09::InterruptAttack(float Seconds)
{
 if(!HasAuthority()||Dead())return;StopCeiling();HitVictims.Reset();NextPulse=ResonancePulseCount;
 StaggerReleaseSide=bGripMoving?GripSide:0;
 ReactionSeconds=FMath::Max(.2f,Seconds);SetState(EM09State::Stagger);Combat->BeginReaction(ReactionSeconds);
}
void AHangingBellM09::StartHitPresentation(){if(!Dead())if(auto* A=Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))A->TransitionTo(Clip(TEXT("Stagger")),false,true,.08f);}
void AHangingBellM09::SetHitPresentationTime(float Elapsed,float Remaining)
{
 if(!Dead())Sample(Elapsed<.25f?Elapsed:Remaining>.4f?.25f:1.4f-FMath::Max(0.f,Remaining));
}
void AHangingBellM09::FinishHitReaction(){if(!Dead()&&State==EM09State::Stagger){GlobalCooldown=.55f;SetState(EM09State::Idle);}}
void AHangingBellM09::EnterDeath()
{
 StopCeiling();HitVictims.Reset();NextPulse=ResonancePulseCount;Target.Reset();
 // Death must hand back to the original constrained body asset before capture.
 if(VisualMesh&&GetMesh()->GetPhysicsAsset()!=VisualMesh->GetPhysicsAsset())GetMesh()->SetPhysicsAsset(VisualMesh->GetPhysicsAsset());
 Corpse->PrepareDeath(GetMesh());
 SetState(EM09State::Dying);GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);SetLifeSpan(CorpseSeconds);
 if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
float AHangingBellM09::TakeDamage(float D,const FDamageEvent& E,AController* EventInstigator,AActor* Causer)
{
 if(!HasAuthority()||Dead()||D<=0)return 0;
 // Shared weapon/spell transactions apply the guaranteed head critical once,
 // including the critical receipt and hit feedback. Do not add a second 1.5x here.
 const UDamageType* Type=E.DamageTypeClass?E.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr;
 const float Reduced=CombatFormulaRuntime::MitigateMonster(this,D,Type,Causer);
 const float Applied=UDevelopmentTuningSubsystem::ShouldOneHitKill(this,EventInstigator,Causer)?Health:FMath::Min(Health,Reduced);
 if(Applied<=0)return 0;Health-=Applied;Super::TakeDamage(Applied,E,EventInstigator,Causer);
 if(Health<=0)
 {
  EnterDeath();
  if(!bRewarded)
  {
   bRewarded=true;ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),EventInstigator,this);
   if(auto* PC=Cast<APlayerController>(EventInstigator);PC&&PC->IsLocalController()&&GetGameInstance())
    GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
  }
 }
 else Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(E.DamageTypeClass));
 return Applied;
}
bool AHangingBellM09::TriggerAttack(FName Attack)
{
 if(!HasAuthority()||Dead())return false;
 if(Attack==TEXT("Death")){Health=0;EnterDeath();return true;}
 if(Attack==TEXT("Stagger")){InterruptAttack(1.4f);return true;}
 APawn* Player=UGameplayStatics::GetPlayerPawn(this,0);if(!Player||!HasAttackSight(Player))return false;
 if(Attack==TEXT("Gaze")&&!CanGazeReach(Player))return false;
 for(auto S:{EM09State::SwingLeft,EM09State::SwingRight,EM09State::Resonance,EM09State::Gaze,EM09State::Claw})
  if(NameFor(S)==Attack)
  {StopCeiling();Target=Player;LockedAim=Player->GetActorLocation()+FVector(0,0,35);HitVictims.Reset();NextPulse=0;
   if(S==EM09State::Gaze)Cooldown[2]=M09Gaze::Cooldown;
   if(S==EM09State::Resonance)Cooldown[1]=8.f;
   if(S==EM09State::Claw)Cooldown[3]=M09Claw::Cooldown;
   SetState(S);return true;}
 return false;
}
void AHangingBellM09::EndPlay(const EEndPlayReason::Type Reason){Voice->Stop();ClearGazeFX();Super::EndPlay(Reason);}
