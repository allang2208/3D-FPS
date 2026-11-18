FSoftObjectPath UMonsterCombatComponent::DefaultStunAnimationPath(const FString& Role)
{
    const FString Name=TEXT("A_")+Role+TEXT("_Dizzy");
    return FSoftObjectPath(TEXT("/Game/Monsters/HumanoidStun/")+Role+TEXT("/")+Name+TEXT(".")+Name);
}


// Replace only the existing !DizzyClip branch inside LoadHumanoidStun.
    if(!DizzyClip)
    {
        const FSoftObjectPath Path=DefaultStunAnimationPath(Role);
        DizzyClip=Cast<UAnimSequence>(Path.ResolveObject());
        // Prepared areas retain this asset before actors enter play. Preserve
        // the fallback for standalone subjects without an area preparation step.
        if(!DizzyClip)DizzyClip=LoadObject<UAnimSequence>(nullptr,*Path.ToString());
    }
