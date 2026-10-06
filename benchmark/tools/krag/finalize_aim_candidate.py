"""Record the isolated aim candidate after actual roundtrip and failed art review."""
from pathlib import Path
import csv,hashlib,json

ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/krag'
CANDIDATE=ROOT/'benchmark/local/candidates/krag-v7-aim';SHARED=ROOT/'benchmark/shared/characters/krag'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def relative(path):return path.relative_to(ROOT).as_posix()
def record(path):return {'path':relative(path),'bytes':path.stat().st_size,'sha256':sha(path)}
def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n',newline='\n')

source=ART/'Krag_Runtime_Optimized_v7_Aim.blend';source_sha=sha(source)
proof=json.loads((ART/'weapon-aim-payload-validation-v7.json').read_text())
roundtrip=json.loads((ART/'weapon-aim-roundtrip-v7.json').read_text())
if not roundtrip['actualBlenderRoundtripPassed']:raise AssertionError('Roundtrip has not passed')
if len(proof['files'])!=5 or not all(f['unchangedAllOtherTreeProperties'] and f['changedRotationArrays']==9 for f in proof['files']):
    raise AssertionError('Raw nine-array preservation proof missing')
repair={'kind':'Shoot right-arm aim only','sourceRuntimeSha256':source_sha,
    'changedBones':['UpperArm_R','LowerArm_R','Hand_R'],'changedChannel':'Shoot / Lcl Rotation / XYZ KeyValueFloat',
    'rawPreservationEvidence':'benchmark/art/krag/weapon-aim-payload-validation-v7.json',
    'actualRoundtripEvidence':'benchmark/art/krag/weapon-aim-roundtrip-v7.json','artisticAcceptance':False,
    'remainingPoseDefects':['Open right fingers do not wrap firearm grip','Severe right axillary/chest skin stretching in raised-arm pose']}
for filename in ['manifest.json','krag_asset_contract.json']:
    path=CANDIDATE/filename;data=json.loads(path.read_text());data['animationRepair']=repair
    if filename=='manifest.json':
        data['runtimeDerivative']['sha256']=source_sha;data['status']='Bounded aim correction; geometry/pose artistic acceptance still failed'
    else:data['runtime_derivative_sha256']=source_sha
    write(path,data)
telemetry={}
jobs=['fix-aim-v7','export-aim-v7','patch-aim-v7','roundtrip-aim-markers-v7',
      'review-aim-v7-Natural_ActionFront','review-aim-v7-Natural_RightGrip']
for name in jobs:
    path=ROOT/'benchmark/local'/('krag-'+name+'-memory.csv')
    rows=list(csv.DictReader(path.open(encoding='utf-8-sig')))
    telemetry[name]={'exitCode':0,'peakPrivateMB':max(int(r['privateMB']) for r in rows),
        'minAvailableMB':min(int(r['availableMB']) for r in rows),
        'maxCommitPercent':max(int(r['commitPercent']) for r in rows),'evidence':record(path)}
files=[{'path':p.relative_to(CANDIDATE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
       for p in sorted(CANDIDATE.rglob('*')) if p.is_file()]
changed=[f['path'] for f in files if f['sha256']!=sha(SHARED/f['path'])]
expected={'Krag_Natural.fbx','Krag_Crusher.fbx','Krag_IronJaw.fbx','Krag_Piston.fbx',
          'animations/Shoot.fbx','manifest.json','krag_asset_contract.json'}
if set(changed)!=expected:raise AssertionError('Unexpected candidate changes: '+str(changed))
renders=[ART/'renders/Krag_Natural_ActionFront_Runtime_Shoot_f13_v7-aim-review.png',
         ART/'renders/Krag_Natural_RightGrip_Runtime_Shoot_f13_v7-aim-review.png']
proof_paths=[ART/name for name in ['weapon-aim-payload-validation-v7.json','weapon-aim-roundtrip-v7.json',
    'weapon-aim-exported-v7.json','weapon-aim-correction-v7.json','weapon-aim-donor-v7.json','weapon-aim-raw-v7.json']]
tools=[Path(__file__).parent/name for name in ['fix_krag_aim.py','krag_weapon_pose.py','krag_locomotion.py',
    'export_aim_clip.py','patch_fbx_shoot_curves.py','validate_aim_clip.py','review_krag.py','finalize_aim_candidate.py']]
receipt={'status':'Validated bounded weapon-direction correction; open grip and shoulder deformation still fail pose/art acceptance',
    'artisticAcceptance':False,'poseAcceptance':False,'functionalAimCorrectionPassed':True,
    'baselineReceipt':'benchmark/art/krag/delivery-v7-triangulated.json',
    'baselineRuntimeSha256':'87c4d751a5710029949c29ad0475f6596de4141134849b8792d982498e1b6c12',
    'sourceRuntime':relative(source),'source':record(source),'runtimeDerivativeSha256':source_sha,
    'candidateDirectory':relative(CANDIDATE),'sourceAndProofArtifacts':[record(p) for p in proof_paths],
    'toolArtifacts':[record(p) for p in tools],
    'reproductionJobArtifacts':[record(Path(__file__).parent/(name+'-job.json')) for name in jobs],
    'renderArtifacts':[record(p) for image in renders for p in [image,image.with_suffix('.meta.json')]],
    'geometryMorphUVNormalWeightAndBindPayloadsUnchanged':True,'otherAnimationsUnchanged':True,
    'texturesUnchanged':True,'knownPoseDefects':repair['remainingPoseDefects'],'changedFiles':changed,
    'telemetry':telemetry,'fileCountNote':'Includes the already-existing unchanged historical shared delivery-v7.json as well as 71 runtime inputs.',
    'validationImplementationFindings':[
        'Model defaults reflect selected action; actual named BindPose matrices used for compatibility gate',
        'Assembled FBX has mesh-only and full skin BindPose nodes; merge requires consistent duplicate matrices',
        'Embedded takes start at0, standalone at1/30s; donor relative times differ by <=1 FBX integer tick (21.65ps); all target timestamps preserved'],
    'promotion':{'status':'Awaiting root coordination; shared unchanged'},'files':files}
write(ART/'delivery-v7-aim.json',receipt)
print(json.dumps({'files':len(files),'changedFiles':changed,'artisticAcceptance':False,'poseAcceptance':False},indent=2))
