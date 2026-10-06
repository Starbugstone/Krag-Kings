using UnrealBuildTool;
public class GroomProbeEditorTarget : TargetRules
{
    public GroomProbeEditorTarget(TargetInfo Target) : base(Target)
    {
        Type=TargetType.Editor;
        DefaultBuildSettings=BuildSettingsVersion.Latest;
        IncludeOrderVersion=EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("GroomProbe");
    }
}
