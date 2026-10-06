"""Unaccepted sewn sleeveless pattern; four actual openings, no skin crop.

The front/back panels connect below the axilla and across narrow shoulder
bridges. Points are provisional fit guides; the native builder must project
onto the actual anatomical torso, settle fabric, and review Front/Back/Shoot.
"""
import numpy as np
from cloth_patterns import boundary_loops, smooth


def pattern():
    columns=49;rows=49;side_top=23;bridge_steps=10;neck_half_columns=12
    points=[];faces=[];uv=[];directions=[];pins=[];regions=[]
    grids=[]
    for back in [False,True]:
        grid=[]
        for row in range(rows):
            t=row/(rows-1);width=float(np.interp(t,[0,.35,.50,.70,1],[.095,.107,.113,.082,.078]))
            line=[]
            for col in range(columns):
                u=col/(columns-1);s=2*u-1;x=s*width
                # Low front neckline and higher rear neck, with a narrow
                # shoulder strip inside the actual deltoid rather than a cap.
                neck=float(1-smooth(.35,.78,abs(s)))
                top=1.000-neck*(.039 if not back else .018)
                z=.668+t*(top-.668)
                y=(.072 if back else -.076)+.003*np.sin(t*np.pi*2.1+s)*np.sin(t*np.pi)
                line.append(len(points));points.append((x,y,z));directions.append((0,1 if back else -1,0))
                uv.append(((u*.45+.55) if back else u*.45,t))
                support=float(smooth(.90,1,t))*(.45+.55*float(smooth(.35,.75,abs(s))))
                pins.append(support);regions.append('back' if back else 'front')
            grid.append(line)
        for row in range(rows-1):
            for col in range(columns-1):
                f=[grid[row][col],grid[row][col+1],grid[row+1][col+1],grid[row+1][col]]
                faces.append(f[::-1] if back else f)
        grids.append(grid)
    front,back=grids
    # Sew lower side panels only; the unconnected upper side is a true armhole.
    for sign,col in [(-1,0),(1,columns-1)]:
        strip=[]
        for row in range(side_top+1):
            a=np.asarray(points[front[row][col]]);b=np.asarray(points[back[row][col]])
            line=[front[row][col]]
            for step in range(1,bridge_steps):
                t=step/bridge_steps;p=a*(1-t)+b*t
                # Slight torso ease, not a cylindrical sleeve extension.
                p[0]+=sign*.004*np.sin(np.pi*t)
                line.append(len(points));points.append(tuple(p));directions.append((sign*np.sin(np.pi*t),-np.cos(np.pi*t),0))
                uv.append((1.10+t*.28,row/(rows-1)));pins.append(0.);regions.append('side')
            line.append(back[row][col]);strip.append(line)
        for row in range(side_top):
            for step in range(bridge_steps):
                f=[strip[row][step],strip[row][step+1],strip[row+1][step+1],strip[row+1][step]]
                faces.append(f if sign>0 else f[::-1])
    # Two shoulder bridges connect the panels, leaving the central neckline.
    for indices in [range(0,columns//2-neck_half_columns+1),range(columns//2+neck_half_columns,columns)]:
        strip=[]
        for col in indices:
            a=np.asarray(points[front[-1][col]]);b=np.asarray(points[back[-1][col]])
            line=[front[-1][col]]
            for step in range(1,bridge_steps):
                t=step/bridge_steps;p=a*(1-t)+b*t;p[2]+=.006*np.sin(np.pi*t)
                line.append(len(points));points.append(tuple(p));directions.append((0,-np.cos(np.pi*t),np.sin(np.pi*t)))
                uv.append((col/(columns-1)*.45,1.1+t*.35));pins.append(1.);regions.append('shoulder')
            line.append(back[-1][col]);strip.append(line)
        for col in range(len(strip)-1):
            for step in range(bridge_steps):
                faces.append([strip[col][step],strip[col+1][step],strip[col+1][step+1],strip[col][step+1]])
    points=np.asarray(points,dtype=np.float64);faces=np.asarray(faces,dtype=np.int32)
    loops=boundary_loops(faces.tolist())
    if len(loops)!=4:raise RuntimeError('Sewn shirt must have waist, neck and two armholes')
    directions=np.asarray(directions,dtype=np.float64);directions/=np.linalg.norm(directions,axis=1)[:,None]
    # Patchwise UVs are intermediate construction coordinates; source atlas
    # packing must follow once actual garment geometry is accepted.
    return {'points':points,'faces':faces.tolist(),'uv':np.asarray(uv),'pins':np.asarray(pins),
            'directions':directions,'regions':regions,'loops':loops,
            'status':'Prepared sewn panel layout; native fitting and visual review pending'}
