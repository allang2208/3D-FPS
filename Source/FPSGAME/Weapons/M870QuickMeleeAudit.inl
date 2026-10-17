// Included in UShotgunAttachmentAuditCommandlet::Main: isolated world/profile,
// real asset routing and real authority entrypoints; no socket/gameplay session.
Model->Current=Base;Model->Current.Stamina=100.f;Model->Current.bQuickCombatReserved=false;
Model->CurrentPawn=Pawn;Pawn->ApplyColdSteelProfile(Model);
auto* Quick=Pawn->QuickCombatPistol.Get();
UAnimSequence* QuickClip=Pawn->QuickCombatAnimation.Get();
Check(QuickClip&&QuickClip->GetPathName()==M870WeaponAssets::AnimationPath(TEXT("quick_melee")),
    TEXT("M870 quick melee routes to its own installed sequence"));
Quick->ConfigureForRifle(QuickClip?QuickClip->GetPlayLength():.9f,true);
Check(FMath::IsNearlyEqual(Quick->GetSourceLength(),.9f,1.e-5f)&&
    FMath::IsNearlyEqual(Quick->GetContactFraction()*Quick->GetSourceLength(),1.f/6.f,1.e-5f),
    FString::Printf(TEXT("M870 melee clock independent of shooting interval: length %.9f contact %.9f"),
        Quick->GetSourceLength(),Quick->GetContactFraction()*Quick->GetSourceLength()));
for(EM4SprintGrip Grip:{EM4SprintGrip::Angled,EM4SprintGrip::Vertical,EM4SprintGrip::Canted,EM4SprintGrip::Prism})
{
    const auto* Profile=Pawn->WeaponGripProfileFor(Grip);
    const auto* Clip=Profile?Profile->Find(QuickClip):nullptr;
    Check(Clip&&Clip->Playback()==QuickClip&&Pawn->RifleQuickCombatClip(Grip)==QuickClip,
        FString::Printf(TEXT("M870 foregrip %d consumes shared quick-melee pose deltas"),int32(Grip)));
}
FVector ActualProbe;
const FTransform RootPose=Pawn->AKMViewmodel->GetSocketTransform(TEXT("WPN_root"),RTS_World);
// Independent native buttpad measurement from stock_contact.json, in cm.
const FVector NativeButtpad=RootPose.GetLocation()+RootPose.TransformVectorNoScale(FVector(.000004,1.538691,50.571123));
const auto* CastingMesh=Cast<UFPSCastingMeshComponent>(Pawn->AKMViewmodel);
Check(CastingMesh&&CastingMesh->GetRifleStockMeleeProbe(ActualProbe,true)&&ActualProbe.Equals(NativeButtpad,.001),
    TEXT("M870 contact probe uses measured native buttpad without double FBX scale"));

Shadow->Current=Base;Shadow->Current.Stamina=100.f;Shadow->Current.bQuickCombatReserved=false;
Remote->ApplyColdSteelProfile(Shadow);PS->QuickCombatUntil=0.;PS->QuickCombatServerSequence=PS->QuickCombatRequestSequence=0;
PS->QuickCombatTargets.Reset();
const float StaminaBefore=Shadow->Stamina(),Cost=Shadow->QuickCombatStaminaCost();
PS->ServerQuickCombat_Implementation(100,Remote,.9f,false);
const double AcceptedUntil=PS->QuickCombatUntil;
Check(PS->QuickCombatServerSequence==100&&PS->IsQuickCombatExecuting(Remote)&&FMath::IsNearlyEqual(Shadow->Stamina(),StaminaBefore-Cost),
    TEXT("M870 remote quick melee commits one authority stamina cost"));
PS->ServerQuickCombat_Implementation(100,Remote,.9f,false);
Check(PS->QuickCombatUntil==AcceptedUntil&&FMath::IsNearlyEqual(Shadow->Stamina(),StaminaBefore-Cost),
    TEXT("replayed quick-melee start cannot spend stamina twice"));
auto* Target=World->SpawnActor<AActor>();
PS->QuickCombatTargets.Add(Target);
PS->ServerQuickCombat_Implementation(101,Remote,.9f,false);
Check(PS->QuickCombatServerSequence==100&&PS->QuickCombatUntil==AcceptedUntil&&PS->QuickCombatTargets.Contains(Target),
    TEXT("rejected overlapping melee preserves accepted serial deadline and hit deduplication"));
PS->ServerQuickCombat_Implementation(101,Remote,0.f,true);
Check(PS->QuickCombatUntil==AcceptedUntil,TEXT("rejected action finish cannot cancel the accepted melee"));

const FVector Eye=Remote->GetPawnViewLocation();
FColdSteelNetHitReport Report;Report.Target=Target;Report.ItemDefinition=M870WeaponAssets::Definition;
Report.AttackMeta=0x80;Report.Flags=(1<<0)|(1<<1);Report.QuickCombatSerial=100;
Report.AimOrigin=Eye;Report.ImpactPoint=Eye+FVector(100,0,0);Report.Direction=FVector::ForwardVector;
PS->FireTokenBucket=6.f;PS->LastFireTokenRefillAt=World->GetTimeSeconds();
FString Reason;const FColdSteelItem* Declared=nullptr;
Check(!PS->ValidateHitReport(Report,Remote,Reason,Declared)&&Reason.Contains(TEXT("duplicate")),
    TEXT("one melee cannot report the same target twice"));
PS->QuickCombatTargets.Reset();
Check(Remote->ProjectileSpeedCM>0.f&&PS->ValidateHitReport(Report,Remote,Reason,Declared),
    TEXT("ballistic M870 accepts a clear authorized melee contact"));
Report.QuickCombatSerial=99;
Check(!PS->ValidateHitReport(Report,Remote,Reason,Declared),TEXT("old melee serial cannot report damage"));
Report.QuickCombatSerial=100;PS->QuickCombatPawn=Pawn;
Check(!PS->ValidateHitReport(Report,Remote,Reason,Declared),TEXT("melee contact must belong to the accepted pawn"));
PS->QuickCombatPawn=Remote;
Report.AimOrigin=Eye+FVector(2000,0,0);
Check(!PS->ValidateHitReport(Report,Remote,Reason,Declared)&&Reason==TEXT("origin drift"),
    TEXT("M870 melee retains origin validation despite gun projectile speed"));
Report.AimOrigin=Eye;

auto* Wall=World->SpawnActor<AActor>();
auto* Box=NewObject<UBoxComponent>(Wall);Wall->SetRootComponent(Box);Wall->AddInstanceComponent(Box);
Box->SetBoxExtent(FVector(6,100,100));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
Box->SetCollisionObjectType(ECC_WorldStatic);Box->SetCollisionResponseToAllChannels(ECR_Ignore);
Box->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);Box->RegisterComponent();Wall->SetActorLocation(Eye+FVector(50,0,0));
Check(!PS->ValidateHitReport(Report,Remote,Reason,Declared)&&Reason==TEXT("los blocked"),
    TEXT("server rejects an M870 gun-bash contact through a wall"));
Wall->Destroy();
PS->ServerQuickCombat_Implementation(100,Remote,0.f,true);
Check(!PS->IsQuickCombatExecuting(Remote)&&!PS->ValidateHitReport(Report,Remote,Reason,Declared),
    TEXT("finished melee cannot submit another contact"));
const float AfterFinish=Shadow->Stamina();
PS->ServerQuickCombat_Implementation(101,Remote,.9f,false);
Check(!PS->IsQuickCombatExecuting(Remote)&&Shadow->Stamina()==AfterFinish,
    TEXT("previously rejected sequence cannot be replayed after recovery"));
PS->ServerQuickCombat_Implementation(102,Remote,.9f,false);
Check(PS->QuickCombatServerSequence==102&&PS->IsQuickCombatExecuting(Remote),TEXT("new melee starts normally after recovery"));
PS->ServerQuickCombat_Implementation(102,Remote,0.f,true);
Shadow->Current.Stamina=0.f;PS->ServerQuickCombat_Implementation(103,Remote,.9f,false);
Check(!PS->IsQuickCombatExecuting(Remote)&&Shadow->Stamina()==0.f,TEXT("insufficient stamina rejects quick melee without committing"));

// The actual client rejection must also release the firearm state/pose on its
// next update, not leave the rejected first-person action running for 0.9 s.
Pawn->WeaponState=EAKMWeaponState::Idle;Quick->Cancel();
Model->Current=Base;Model->Current.Stamina=100.f;Model->Current.bQuickCombatReserved=false;
const bool Began=Quick->BeginAction();
Pawn->WeaponState=EAKMWeaponState::QuickCombat;Pawn->WeaponStateDuration=.9f;
Pawn->WeaponActionStartedAt=World->GetTimeSeconds();Pawn->ActiveActionAnimation=QuickClip;
Pawn->NextAllowedShotTime=0.;
auto* OwnerPS=PC->GetPlayerState<AColdSteelPlayerState>();OwnerPS->QuickCombatSequence=500;
OwnerPS->QuickCombatPawn=Pawn;OwnerPS->QuickCombatPredictedCosts.Add(500,Cost);
OwnerPS->ClientQuickCombatRejected_Implementation(500);Pawn->UpdateWeaponState(.001f);
Check(Began&&!Quick->IsOccupyingLeftHand()&&Pawn->WeaponState==EAKMWeaponState::Idle&&!Pawn->ActiveActionAnimation
    &&Pawn->NextAllowedShotTime<=World->GetTimeSeconds()+.001,
    TEXT("client melee rejection releases both action ownership and firearm playback"));
Quick->ConfigureForUnarmedPunch();Model->Current.Stamina=100.f;
const bool PunchBegan=Quick->BeginAction();
OwnerPS->QuickCombatPredictedCosts.Add(500,Cost);
OwnerPS->ClientQuickCombatRejected_Implementation(500);
Check(PunchBegan&&Quick->IsOccupyingLeftHand()&&Quick->GetStyle()==EQuickCombatStyle::UnarmedPunch,
    TEXT("late gun-melee rejection does not cancel a subsequent ordinary punch"));
Quick->Cancel();
Target->Destroy();
