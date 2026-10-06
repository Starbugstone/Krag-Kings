"""Prepared strand-breakup study; exact existing 4x4 texture/UV contract.

No scene mutation or new fur coverage. Existing regional colors and shader data
conventions are retained. This texture must be compared on an actual groom.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/nib/v6_groom_wip'))
import atlas


def pattern(seed,short_nap=False):
    rng=np.random.default_rng(seed)
    yy,xx=np.mgrid[0:atlas.TILE,0:atlas.TILE].astype(np.float32)
    y=(yy-atlas.PADDING)/(atlas.TILE-2*atlas.PADDING-1)
    x=(xx-atlas.PADDING)/(atlas.TILE-2*atlas.PADDING-1)*2-1
    alpha=np.zeros_like(x);pigment=np.ones_like(x);height=np.zeros_like(x)
    count=150 if short_nap else 78
    roots=np.linspace(-.88,.88,count)+rng.uniform(-.035,.035,count)
    for i in rng.permutation(count):
        root=roots[i];start=rng.uniform(-.045,.07);end=rng.uniform(.40,.995) if short_nap else rng.uniform(.58,.995)
        t=np.clip((y-start)/(end-start),0,1)
        tip=np.clip(root*rng.uniform(.58,.98)+rng.uniform(-.12,.12),-.94,.94)
        bow=rng.uniform(-.13,.13)*(1.35 if i%11==0 else 1)
        center=root*(1-t)+tip*t+bow*np.sin(np.pi*t)+rng.uniform(-.025,.025)*np.sin(2*np.pi*t)
        radius=rng.uniform(.0035,.0068)*(1-t)**.6+.00055
        distance=np.abs(x-center)
        coverage=(1-atlas.smooth(radius-.0015,radius+.0015,distance))
        coverage*=atlas.smooth(start-.010,start+.018,y)*(1-atlas.smooth(end-.016,end+.002,y))
        shade=rng.uniform(.82,1.10);grain=.989+.018*np.sin(y*rng.uniform(95,160)+rng.uniform(0,6.3))
        pigment=pigment*(1-coverage)+shade*grain*coverage
        height=np.maximum(height,np.sqrt(np.maximum(0,1-(distance/np.maximum(radius,.0005))**2))*coverage)
        alpha=coverage+alpha*(1-coverage)
    # No opaque horizontal root band. Each fiber has its own faded start.
    inside=(xx>=atlas.PADDING)&(xx<atlas.TILE-atlas.PADDING)&(yy>=atlas.PADDING)&(yy<atlas.TILE-atlas.PADDING)
    alpha*=inside
    dy,dx=np.gradient(height);nx=np.clip(-dx*.10,-.12,.12);ny=np.clip(-dy*.10,-.12,.12)
    normal=np.stack((nx*.5+.5,ny*.5+.5,np.sqrt(np.maximum(0,1-nx*nx-ny*ny))*.5+.5),-1)
    normal[alpha<1e-5]=(.5,.5,1)
    return {'alpha':alpha,'pigment':pigment,'normal':normal,'rootToTip':np.clip(y,0,1),'roughness':np.clip(.70-.07*np.clip(y,0,1)+(1-pigment)*.08,.56,.80)}


def generate(output):
    output=Path(output)
    if output.exists():raise RuntimeError('Preserve previous atlas')
    atlas.tile_pattern=pattern
    report=atlas.make_atlas(output)
    for tile in report['tiles']:tile['strandPatterns']=150 if tile['family']=='nap' else 78
    report.update({'status':'Actual deterministic texture study, native groom comparison required','profile':'Independent fine strands, scattered tips, no solid root fill','codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'writerRecipeSha256':hashlib.sha256(Path(atlas.__file__).read_bytes()).hexdigest(),'layoutAndRegionalColorsUnchanged':True,'sharedAssetsChanged':False,'engineIntegrated':False,'artisticAcceptance':False})
    (output.parent/'groom-atlas.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    generate(args.output)
    print('NIB_FINE_STRAND_ATLAS_STUDY_COMPLETE',flush=True)
