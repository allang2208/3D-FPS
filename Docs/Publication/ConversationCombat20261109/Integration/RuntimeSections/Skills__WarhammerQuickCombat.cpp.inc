// Integration reference only: preserve shared host declarations and prerequisites.

// Source line 17
void UFPSQuickCombatComponent::ConfigureForWarhammer(bool bHeadThrust)
{
    Style=EQuickCombatStyle::Warhammer;
    bWarhammerHeadThrust=bHeadThrust;
    ClipLength=AttackEnd=bHeadThrust?WarhammerConicalThrust::Length:WarhammerQuickCombat::Length;
    ReleaseEnd=.035f;CockEnd=bHeadThrust?WarhammerConicalThrust::Prepare:WarhammerQuickCombat::Prepare;
    ContactTime=bHeadThrust?WarhammerConicalThrust::Contact:WarhammerQuickCombat::Contact;
    FollowEnd=bHeadThrust?WarhammerConicalThrust::Follow:WarhammerQuickCombat::Follow;
}
