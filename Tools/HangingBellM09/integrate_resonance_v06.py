from pathlib import Path
import shutil
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/HangingBellM09Meshy20261003/ResonanceV06/Records/Before'
out.mkdir(parents=True,exist_ok=True)
h=root/'Source/FPSGAME/Monsters/HangingBellM09.h';c=h.with_suffix('.cpp')
for p in (h,c):shutil.copy2(p,out/p.name)
def replace(text,old,new):
 if old not in text:raise RuntimeError('Source context changed: '+old[:100])
 return text.replace(old,new,1)
s=h.read_text(encoding='utf-8-sig')
s=replace(s,'class UMaterialInterface;','class UMaterialInterface;\nclass UMaterialInstanceDynamic;')
s=replace(s,' void ResonancePulse();',' void ResonancePulse();\n void CaptureResonanceAim();\n bool HasResonanceSight(const APawn* Victim,FVector Origin) const;')
s=replace(s,' int32 GripSide=0,NextPulse=0,SwingCount=0;\n};',''' int32 GripSide=0,NextPulse=0,SwingCount=0;
 // Appended V06 state: all three pulses share one locked emission frame.
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TObjectPtr<UMaterialInterface> ResonanceMaterial;
 UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> WaveMaterials;
 UPROPERTY(Replicated) FVector ResonanceOrigin=FVector::ZeroVector;
 UPROPERTY(Replicated) FVector ResonanceDirection=FVector::ForwardVector;
};''')
h.write_text(s,encoding='utf-8')
s=c.read_text(encoding='utf-8-sig')
s=replace(s,'#include "Materials/MaterialInterface.h"','#include "Materials/MaterialInterface.h"\n#include "Materials/MaterialInstanceDynamic.h"')
s=replace(s,'constexpr float StepSeconds=.6f;','''constexpr float StepSeconds=.6f;
constexpr float ResonanceLock=.80f;
constexpr float ResonanceFirstPulse=1.10f;
constexpr float ResonancePulseGap=.35f;
constexpr float ResonanceRange=600.f;
constexpr float ResonanceConeCos=.64278761f; // 50 degree half-angle.''')
s=replace(s,'static ConstructorHelpers::FObjectFinder<UStaticMesh> Wave(TEXT("/Game/Monsters/HangingBellM09/V04/FX/SM_M09_Wave.SM_M09_Wave"));WaveMesh=Wave.Object;',
'''static ConstructorHelpers::FObjectFinder<UStaticMesh> Wave(TEXT("/Game/Monsters/HangingBellM09/V06/FX/SM_M09_ResonanceWave_V06.SM_M09_ResonanceWave_V06"));WaveMesh=Wave.Object;
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> ResonanceMat(TEXT("/Game/Monsters/HangingBellM09/V06/Materials/M_M09_Resonance_V06.M_M09_Resonance_V06"));ResonanceMaterial=ResonanceMat.Object;''')
s=replace(s,' GetCapsuleComponent()->InitCapsuleSize(85.f,137.f);',''' static ConstructorHelpers::FObjectFinder<UAnimSequence> ResonanceClip(TEXT("/Game/Monsters/HangingBellM09/V06/Animations/A_M09_Resonance_V06.A_M09_Resonance_V06"));
 if(ResonanceClip.Object)Clips.Add(TEXT("Resonance"),ResonanceClip.Object);
 static ConstructorHelpers::FObjectFinder<USoundBase> ResonanceSound(TEXT("/Game/Monsters/HangingBellM09/V06/Audio/S_M09_Resonance_V06.S_M09_Resonance_V06"));
 if(ResonanceSound.Object)Sounds.Add(TEXT("Resonance"),ResonanceSound.Object);
 GetCapsuleComponent()->InitCapsuleSize(85.f,137.f);''')
s=replace(s,'for(const auto& Cmp:Waves){Cmp->SetStaticMesh(WaveMesh);Cmp->SetMaterial(0,EnergyMaterial);}',
'for(const auto& Cmp:Waves){Cmp->SetStaticMesh(WaveMesh);Cmp->SetMaterial(0,ResonanceMaterial);}')
s=replace(s,' Super::BeginPlay();AlignVisual();GetCharacterMovement()->DisableMovement();',''' Super::BeginPlay();AlignVisual();GetCharacterMovement()->DisableMovement();
 if(GetNetMode()!=NM_DedicatedServer)
  for(const auto& W:Waves)WaveMaterials.Add(W->CreateDynamicMaterialInstance(0,ResonanceMaterial));''')
s=replace(s,' DOREPLIFETIME(AHangingBellM09,StaggerReleaseSide);DOREPLIFETIME(AHangingBellM09,ReactionSeconds);',
''' DOREPLIFETIME(AHangingBellM09,StaggerReleaseSide);DOREPLIFETIME(AHangingBellM09,ReactionSeconds);
 DOREPLIFETIME(AHangingBellM09,ResonanceOrigin);DOREPLIFETIME(AHangingBellM09,ResonanceDirection);''')
s=replace(s,' if(auto* S=Sounds.Find(StateClip());S&&*S){Voice->SetSound(*S);Voice->Play();}',
''' if(auto* S=Sounds.Find(StateClip());S&&*S)
 {
  Voice->SetWorldLocation(State==EM09State::Resonance?ResonanceOrigin:Eye());
  Voice->SetSound(*S);Voice->Play(StateSeconds);
 }''')
s=replace(s,' State=Next;StateSeconds=0;StateStartedAt=GetWorld()->GetTimeSeconds();PresentState();ForceNetUpdate();',
''' State=Next;StateSeconds=0;StateStartedAt=GetWorld()->GetTimeSeconds();
 if(State==EM09State::Resonance)CaptureResonanceAim();
 PresentState();ForceNetUpdate();''')
start=s.index('bool AHangingBellM09::CanAttack(');end=s.index('void AHangingBellM09::Deal(',start)
s=s[:start]+'''bool AHangingBellM09::CanAttack(APawn* P) const
{
 if(!IsValid(P)||Busy()||bGripMoving||GlobalCooldown>0||!bInitialized||!HasAttackSight(P))return false;
 if(auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return false;
 const FVector Origin=GetMesh()->GetSocketLocation(TEXT("spine_03"));
 const FVector D=P->GetActorLocation()+FVector(0,0,35)-Origin;
 if(!D.IsNearlyZero()&&D.SizeSquared2D()>FMath::Square(50.f)&&
    FVector::DotProduct(D.GetSafeNormal2D(),GetActorForwardVector())<.45f)return false;
 // First attack production stage. Other prototypes remain available via m09.Attack.
 return Cooldown[1]<=0&&D.SizeSquared()<=FMath::Square(ResonanceRange)&&HasResonanceSight(P,Origin);
}
bool AHangingBellM09::StartAttack(APawn* P)
{
 if(!HasAuthority()||!CanAttack(P))return false;
 Target=P;StopCeiling();HitVictims.Reset();NextPulse=0;bGazeLocked=false;Cooldown[1]=8.f;
 LockedAim=P->GetActorLocation()+FVector(0,0,35);
 SetState(EM09State::Resonance);
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
''' + s[end:]
start=s.index('void AHangingBellM09::ResonancePulse()');end=s.index('void AHangingBellM09::GazePulse()',start)
s=s[:start]+'''void AHangingBellM09::ResonancePulse()
{
 // One server-side damage application per player per pulse. Cover is traced from
 // the same locked torso origin that drives the visible shock wave.
 for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=It->Get())if(APawn* P=PC->GetPawn())
 {
  if(auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())continue;
  const FVector Point=P->GetActorLocation()+FVector(0,0,35),D=Point-ResonanceOrigin;
  if(D.SizeSquared()>FMath::Square(ResonanceRange)||
     FVector::DotProduct(D.GetSafeNormal(),ResonanceDirection)<ResonanceConeCos||!HasResonanceSight(P,ResonanceOrigin))continue;
  Deal(P,MagicAttack*.30f,true,Point);
  if(auto* S=P->FindComponentByClass<UCombatStatusFormula>())S->AddSlow(.45f,.15f);
  if(Dead()||State!=EM09State::Resonance)return;
 }
}
''' +s[end:]
s=replace(s,''' const float Lock=State==EM09State::Gaze?.90f:State==EM09State::Resonance?.80f:.60f;
 if(StateSeconds<Lock&&Target.IsValid())LockedAim=Target->GetActorLocation()+FVector(0,0,35);''',
''' const float Lock=State==EM09State::Gaze?.90f:State==EM09State::Resonance?ResonanceLock:.60f;
 if(State==EM09State::Resonance)
 {
  if(Previous<Lock){CaptureResonanceAim();if(StateSeconds>=Lock)ForceNetUpdate();}
 }
 else if(StateSeconds<Lock&&Target.IsValid())LockedAim=Target->GetActorLocation()+FVector(0,0,35);''')
s=replace(s,'const float First=State==EM09State::Resonance?1.10f:1.25f;','const float First=State==EM09State::Resonance?ResonanceFirstPulse:1.25f;')
s=replace(s,'const float Gap=State==EM09State::Resonance?.35f:.20f;','const float Gap=State==EM09State::Resonance?ResonancePulseGap:.20f;')
start=s.index(' for(int32 I=0;I<3;++I)',s.index('void AHangingBellM09::UpdateFX()'))
end=s.index('\n}\nvoid AHangingBellM09::Tick(',start)
s=s[:start]+''' if(State==EM09State::Resonance)Voice->SetWorldLocation(ResonanceOrigin);
 for(int32 I=0;I<3;++I)
 {
  const float Age=StateSeconds-(ResonanceFirstPulse+ResonancePulseGap*I);
  const bool Active=State==EM09State::Resonance&&Age>=0&&Age<.26f;
  Waves[I]->SetVisibility(Active);
  if(Active)
  {
   const float T=FMath::Clamp(Age/.16f,0.f,1.f);
   const float Radius=FMath::Lerp(55.f,ResonanceRange,T);
   // Unit spherical cap: all visible bands remain inside the six metre range.
   Waves[I]->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(ResonanceDirection).ToQuat(),ResonanceOrigin,FVector(Radius/100.f)));
   if(WaveMaterials.IsValidIndex(I)&&WaveMaterials[I])
   {
    WaveMaterials[I]->SetScalarParameterValue(TEXT("PulseAlpha"),.68f*(1.f-Smooth(Age/.26f)));
    WaveMaterials[I]->SetScalarParameterValue(TEXT("PulsePhase"),I*2.1f+Age*12.f);
   }
  }
 }''' +s[end:]
c.write_text(s,encoding='utf-8')
config=root/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig')
old='+DirectoriesToAlwaysCook=(Path="/Game/Monsters/HangingBellM09/V04")'
text=replace(text,old,old+'\n+DirectoriesToAlwaysCook=(Path="/Game/Monsters/HangingBellM09/V06")')
config.write_text(text,encoding='utf-8')
print('M09_V06_RUNTIME_WRITTEN')
