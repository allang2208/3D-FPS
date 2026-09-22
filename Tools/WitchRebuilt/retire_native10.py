"""Remove obsolete presentation code while retaining the Witch combat base."""
from pathlib import Path
import shutil,json,hashlib
root=Path('D:/FPS3D/FPSGAME').resolve();out=root/'SourceAssets/WitchRebuilt20260921/Revision10'
before=out/'Before';before.mkdir(parents=True,exist_ok=True)
path=root/'Source/FPSGAME/Monsters/WitchMonster.cpp'
shutil.copy2(path,before/path.name)
text=path.read_text(encoding='utf-8')
start=text.index('#if WITH_EDITOR');end=text.index('AWitchMonster::AWitchMonster',start)
text=text[:start]+text[end:]
start=text.index('bool AWitchMonster::PrepareCombatPhysics')
text=text[:start]
start=text.index('void AWitchMonster::AttachProps()');end=text.index('bool AWitchMonster::CanCast',start)
text=text[:start]+text[end:]
start=text.index('    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(')
end=text.index('    static ConstructorHelpers::FObjectFinder<UStaticMesh> StaffAsset(',start)
text=text[:start]+text[end:]
text=text.replace('    static ConstructorHelpers::FObjectFinder<UStaticMesh> BottleAsset(TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_PoisonBottle.SM_Witch_PoisonBottle"));\n','')
text=text.replace('    VisualMesh = Model.Object; IdleClip = Idle.Object; WalkClip = Walk.Object;\n    CastClip = Cast.Object; ThrowClip = Throw.Object; DeathClip = Death.Object; AttackClip = CastClip;',
 '    // Concrete presentation resolves its own assets; do not load retired Witch variants.\n    VisualMesh = nullptr; IdleClip = nullptr; WalkClip = nullptr; AttackClip = nullptr;\n    GetMesh()->SetSkeletalMeshAsset(nullptr);')
text=text.replace('Staff->SetupAttachment(GetMesh(), TEXT("LeftHand"))','Staff->SetupAttachment(GetMesh(), TEXT("hand_l"))')
text=text.replace('Bottle->SetupAttachment(GetMesh(), TEXT("RightHand")); Bottle->SetStaticMesh(BottleAsset.Object);','Bottle->SetupAttachment(GetMesh(), TEXT("hand_r"));')
text=text.replace('    // V05 retains the donor\'s 3.2667 s stride and its 73.16 cm travel.\n','')
text=text.replace('WalkSpeed = 22.3955f;','WalkSpeed = 82.5f;')
start=text.index('    const auto& Ref = VisualMesh->GetRefSkeleton();');end=text.index('\n}\n\nvoid AWitchMonster::OnConstruction',start)
text=text[:start]+'''    // The rebuilt authoring source places the soles at zero.
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()));'''+text[end:]
start=text.index('    // Editor imports may complete after the native CDO was loaded.')
end=text.index('    AttackClip = CastClip; AlignVisual();',start)
text=text[:start]+text[end:]
text=text.replace('#include "PhysicsEngine/PhysicsAsset.h"\n','').replace('#include "PhysicsEngine/SkeletalBodySetup.h"\n','')
path.write_text(text,encoding='utf-8')

archive=(root/'trash/witch-variants-20260922').resolve();rows=[]
for name in ('WitchMotionCandidate.cpp','WitchMotionCandidate.h','WitchFoundationAnimInstance.cpp','WitchFoundationAnimInstance.h'):
 src=(root/'Source/FPSGAME/Monsters'/name).resolve();dst=(archive/src.relative_to(root)).resolve()
 if not src.is_relative_to(root/'Source/FPSGAME/Monsters') or not dst.is_relative_to(archive):raise RuntimeError('Archive path outside scope')
 if dst.exists():raise RuntimeError('Archive destination already exists; source preserved')
 data=src.read_bytes();sha=hashlib.sha256(data).hexdigest();dst.parent.mkdir(parents=True,exist_ok=True)
 src.rename(dst)
 if hashlib.sha256(dst.read_bytes()).hexdigest()!=sha:raise RuntimeError('Archive differs')
 rows.append({'source':str(src.relative_to(root)),'destination':str(dst.relative_to(root)),'bytes':len(data),'sha256':sha,
  'reason':'User retired the independent Foundation Witch variant','replacement':'AWitchRebuiltMonster / UWitchRebuiltAnimInstance'})
receipt=root/'Docs/AssetArchives/witch-variants-native-20260922.json';receipt.parent.mkdir(exist_ok=True)
receipt.write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('Retired four Foundation runtime source files; Witch combat base retained')
