"""Original deterministic fur-clump RGBA/PBR atlas; no external images.

Prepared for the isolated groom job. Uses NumPy and OpenImageIO, available in
Blender's Python. Pixel patterns are authoring proposals, not scanned hair or
evidence of the final character's appearance.
"""
import hashlib,json
from pathlib import Path
import numpy as np

SIZE=2048
TILE=512
PADDING=8
CUTOFF=.45
REGIONS={
    'head':('Nib_v6_HeadFurCards',(.48,.39,.29),(.80,.74,.63)),
    'innerWisps':('Nib_v6_InnerEarWispsCards',(.56,.45,.34),(.88,.82,.71)),
    'outerEar':('Nib_v6_TawnyEarFurCards',(.36,.22,.13),(.67,.46,.25)),
}

def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1)
    return t*t*(3-2*t)

def tile_pattern(seed,short_nap=False):
    rng=np.random.default_rng(seed)
    # Row zero is the root in UV space. Output is flipped for PNG top-left.
    yy,xx=np.mgrid[0:TILE,0:TILE].astype(np.float32)
    y=(yy-PADDING)/(TILE-2*PADDING-1)
    x=(xx-PADDING)/(TILE-2*PADDING-1)*2-1
    alpha=np.zeros((TILE,TILE),np.float32)
    pigment=np.ones_like(alpha)
    height=np.zeros_like(alpha)
    strand_count=104 if short_nap else 46
    roots=np.linspace(-.93,.93,strand_count)+rng.uniform(-.035,.035,strand_count)
    order=rng.permutation(strand_count)
    for number in order:
        root=roots[number]
        start=rng.uniform(-.07,.012)
        end=rng.uniform(.85,.998) if short_nap else rng.uniform(.68,.99)
        if number%13==0:end=.998
        t=np.clip((y-start)/(end-start),0,1)
        loose=number%9==0
        tip=root*(.48 if loose else .22)+rng.uniform(-.16,.16)
        bow=rng.uniform(-.10,.10) if short_nap else rng.uniform(-.19,.19)*(1.35 if loose else 1)
        curl=rng.uniform(-.045,.045)
        center=root*(1-t)+tip*t+bow*np.sin(np.pi*t)+curl*np.sin(2*np.pi*t)
        # Fine fibers within a millimetre-scale clump; irregular staggered ends.
        radius=rng.uniform(.008,.015)*(1-t)**.55+.001
        distance=np.abs(x-center)
        coverage=1-smooth(radius-.0028,radius+.0028,distance)
        coverage*=smooth(start-.010,start+.005,y)*(1-smooth(end-.010,end+.003,y))
        shade=rng.uniform(.84,1.10)
        grain=.985+.025*np.sin(y*rng.uniform(90,180)+rng.uniform(0,6.3))
        pigment=pigment*(1-coverage)+shade*grain*coverage
        fiber_height=np.sqrt(np.maximum(0,1-(distance/np.maximum(radius,.001))**2))
        height=np.maximum(height,fiber_height*coverage)
        alpha=coverage+alpha*(1-coverage)
    # Small clustered root fill creates a soft undercoat without a solid tip.
    root_fill=(1-smooth(.015,.17,y))*(1-smooth(.62,.91,np.abs(x)))*.88
    alpha=root_fill+alpha*(1-root_fill)
    domain=(xx>=PADDING)&(xx<TILE-PADDING)&(yy>=PADDING)&(yy<TILE-PADDING)
    alpha*=domain
    dy,dx=np.gradient(height)
    nx=np.clip(-dx*.20,-.18,.18)
    ny=np.clip(-dy*.20,-.18,.18)
    nz=np.sqrt(np.maximum(0,1-nx*nx-ny*ny))
    normal=np.stack((nx*.5+.5,ny*.5+.5,nz*.5+.5),axis=-1)
    normal[alpha<1e-5]=(.5,.5,1)
    return {'alpha':alpha,'pigment':pigment,'normal':normal,
            'rootToTip':np.clip(y,0,1),'roughness':np.clip(.66-.09*np.clip(y,0,1)+(1-pigment)*.12,.48,.76)}

def write_png(path,pixels,srgb=False):
    import OpenImageIO as oiio
    if pixels.ndim==2:pixels=pixels[:,:,None]
    data=(np.clip(pixels,0,1)*255+.5).astype(np.uint8)
    spec=oiio.ImageSpec(data.shape[1],data.shape[0],data.shape[2],oiio.UINT8)
    if srgb:spec.attribute('oiio:ColorSpace','sRGB')
    if data.shape[2]==4:
        spec.alpha_channel=3
        spec.attribute('oiio:UnassociatedAlpha',1)
    output=oiio.ImageOutput.create(str(path))
    if not output or not output.open(str(path),spec):raise RuntimeError('Cannot open atlas '+str(path))
    if not output.write_image(data):raise RuntimeError(output.geterror())
    output.close()
    return hashlib.sha256(path.read_bytes()).hexdigest()

def make_atlas(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    alpha=np.zeros((SIZE,SIZE),np.float32)
    pigment=np.ones_like(alpha);gradient=np.zeros_like(alpha);rough=np.zeros_like(alpha)
    normal=np.zeros((SIZE,SIZE,3),np.float32);tiles=[]
    for number in range(16):
        short_nap=number>=12
        pattern=tile_pattern(89100+number,short_nap)
        sl=np.s_[number//4*TILE:(number//4+1)*TILE,number%4*TILE:(number%4+1)*TILE]
        for target,key in [(alpha,'alpha'),(pigment,'pigment'),(gradient,'rootToTip'),(rough,'roughness'),(normal,'normal')]:target[sl]=pattern[key]
        tiles.append({'tile':number,'seed':89100+number,'family':'nap' if short_nap else 'long',
                      'coverageAtCutoff':float(np.mean(pattern['alpha']>=CUTOFF)),
                      'coverageInContentAtCutoff':float(np.mean(pattern['alpha'][PADDING:-PADDING,PADDING:-PADDING]>=CUTOFF)),
                      'strandPatterns':104 if short_nap else 46,'paddedBorderAlphaMax':float(max(pattern['alpha'][:PADDING].max(),pattern['alpha'][-PADDING:].max(),pattern['alpha'][:,:PADDING].max(),pattern['alpha'][:,-PADDING:].max()))})
    maps={};materials=[]
    for region,(name,root,tip) in REGIONS.items():
        t=smooth(.03,.96,gradient)
        color=np.asarray(root,dtype=np.float32)[None,None,:]*(1-t[:,:,None])+np.asarray(tip,dtype=np.float32)[None,None,:]*t[:,:,None]
        color*=pigment[:,:,None]
        rgba=np.concatenate((color,alpha[:,:,None]),axis=-1)
        path=directory/(name+'_BaseColor.png')
        maps[path.name]={'sha256':write_png(path,rgba[::-1],True),'colorSpace':'sRGB RGB; linear unassociated coverage alpha','channels':4}
        materials.append({'name':name,'baseColor':'textures/'+path.name,
            'normal':'textures/Nib_v6_FurCards_Normal.png','roughness':'textures/Nib_v6_FurCards_Roughness.png',
            'metallic':'textures/Nib_v6_FurCards_Metallic.png','alphaMode':'MASK','alphaSource':'baseColor.a',
            'alphaClipThreshold':CUTOFF,'doubleSided':True,'doubleSidedNormalMode':'Flip','normalConvention':'OpenGL +Y'})
    for suffix,pixels in [('Normal',normal),('Roughness',rough),('Metallic',np.zeros_like(alpha))]:
        path=directory/('Nib_v6_FurCards_'+suffix+'.png')
        maps[path.name]={'sha256':write_png(path,pixels[::-1]),'colorSpace':'Non-Color linear','channels':3 if pixels.ndim==3 else 1}
    if any(t['paddedBorderAlphaMax']!=0 for t in tiles):raise RuntimeError('Atlas bleed reaches a tile border')
    result={'status':'Generated original procedural texture candidate; character/engine appearance still requires review',
            'size':SIZE,'tileSize':TILE,'paddingPixels':PADDING,'alphaClipThreshold':CUTOFF,
            'alphaIsUnassociated':True,'tiles':tiles,'files':maps,'materials':materials,
            'normalDetail':'Restrained tangent-space fiber relief, no generic skin bump; OpenGL positive Y',
            'artisticAcceptance':False,'externalInputs':[],
            'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (directory.parent/'groom-atlas.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=make_atlas(args.output)
    print('NIB_GROOM_ATLAS_COMPLETE',len(result['files']),flush=True)
