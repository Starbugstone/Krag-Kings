using UnrealBuildTool;
public class KragKingsBenchmark : ModuleRules
{
    public KragKingsBenchmark(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "AnimGraphRuntime", "RHI", "Json", "SlateCore", "AudioMixer" });
    }
}
