"""Authoring-only changes after actual mesh review; no Blender launch here."""
from pathlib import Path
p=Path(__file__).with_name('build_krag.py');s=p.read_text()
# Mechanical materials are worn metal, not chrome or bright plastic.
s=s.replace("(.13,.135,.13),.85,.32,'metal'", "(.074,.075,.070),.82,.51,'metal'")
s=s.replace("(.48,.285,.10),.78,.36,'metal'", "(.31,.166,.047),.72,.49,'metal'")
s=s.replace("(.052,.136,.13),.7,.47,'paint'", "(.046,.104,.101),.72,.58,'paint'")
# Slightly wider low jaw, nasal muzzle angled over closed lip.
s=s.replace("(0,-.132,1.785),(.113,.061,.057)", "(0,-.145,1.788),(.121,.061,.060)")
s=s.replace("(0,-.128,1.87),(.123,.071,.060)", "(0,-.139,1.870),(.125,.070,.054)")
s=s.replace("(s*.109,-.088,1.914),(.064,.078,.051)", "(s*.111,-.084,1.914),(.059,.071,.053)")
s=s.replace("(s*.076,-.128,1.988),(.088,.065,.033)", "(s*.076,-.126,1.988),(.083,.055,.030)")
s=s.replace("(s*.121,-.020,1.973),(.045,.111,.083)", "(s*.121,-.011,1.968),(.045,.102,.083)")
# Hand silhouette: visible finger phalanges below the palm; opposable thumb curls inward.
s=s.replace("('Palm',(s*.621,-.038,.959),(.077,.048,.087))", "('Palm',(s*.621,-.033,.963),(.084,.050,.078))")
s=s.replace("x=s*(.573+j*.032);z=.939+(abs(j-1.5)*.004)", "x=s*(.570+j*.035);z=.901+(abs(j-1.5)*.012)")
s=s.replace("(x+s*.014,-.064,z-.068),(x+s*.008,-.092,z-.100),(x-s*.002,-.113,z-.111)", "(x+s*.009,-.053,z-.048),(x+s*.006,-.078,z-.081),(x-s*.002,-.111,z-.091)")
s=s.replace("[.021,.019,.016,.011]", "[.022,.020,.017,.012]")
s=s.replace("(x-s*.002,-.117,z-.103)", "(x-s*.002,-.113,z-.083)")
s=s.replace("[(s*.566,-.051,.982),(s*.539,-.085,.954),(s*.542,-.115,.926)]", "[(s*.555,-.038,.986),(s*.522,-.074,.953),(s*.523,-.112,.919),(s*.542,-.128,.905)]")
s=s.replace("[.031,.026,.019],skin", "[.033,.027,.022,.016],skin")
# Correct toe cap burial and sole profile.
s=s.replace("(s*.19,-.160,.099),(.114,.083,.051)", "(s*.19,-.173,.109),(.123,.109,.067)")
s=s.replace("(.232,.325,.040)","(.224,.321,.041)")
# Split lower trousers so piston replacement actually removes natural lower leg geometry.
s=s.replace("loft('Trousers_'+side,rings,cloth,'TrouserLeg_'+side,n=64,fold=.055)", "loft('Trousers_upper_'+side,[r for r in rings if r[0]>=.55],cloth,'TrouserLeg_'+side,n=64,fold=.055)\n    loft('Trousers_lower_'+side,[r for r in rings if r[0]<=.60],cloth,'BioLowerLeg_'+side,n=64,fold=.055)")
s=s.replace("elif g.startswith('TrouserLeg_'):", "elif g.startswith('TrouserLeg_') or g.startswith('BioLowerLeg_'):")
s=s.replace("'BionicEye_L','Boot_R','Weapon_R'", "'BionicEye_L','Boot_R','BioLowerLeg_R','Weapon_R'")
# Fuller protected upper arm housing, keeping the asymmetric machinery structure readable.
needle="# Forearm central barrel with cut armor plates, dual cylinders and ribbed hoses."
insert="""# Upper-arm protective plates over the working hydraulic bundle.
for xx,yy in [(.465,-.073),(.449,.086)]:
    o=box('Crusher upper-arm armored casing',(xx,yy,1.43),(.118,.023,.156),paint,G,'UpperArm_L',bevel=.019);o.rotation_euler.y=.32
    for dx in [-.046,.046]:
        for dz in [-.056,.056]:uvball('Upper casing bolt',(xx+dx,yy+(-.017 if yy<0 else .017),1.43+dz),(.008,.006,.008),brass,G,'UpperArm_L',seg=12,rings=8)
"""
s=s.replace(needle,insert+needle)
# Fine pores/cloth fibres contribute real normal detail separately from large cracks.
s=s.replace("bump=n.new('ShaderNodeBump');", "bump=n.new('ShaderNodeBump');")
s=s.replace("bump.inputs['Distance'].default_value=.003", "bump.inputs['Distance'].default_value=.0012 if kind in ('metal','paint') else .0018")
s=s.replace("if kind=='skin':\n        vor=", "if kind=='skin':\n        pore=n.new('ShaderNodeTexNoise');pore.inputs['Scale'].default_value=370;pore.inputs['Detail'].default_value=3;l.new(tex.outputs['Object'],pore.inputs['Vector']);fine=n.new('ShaderNodeBump');fine.inputs['Strength'].default_value=.30;fine.inputs['Distance'].default_value=.0008;l.new(pore.outputs['Fac'],fine.inputs['Height']);l.new(fine.outputs['Normal'],bump.inputs['Normal'])\n        vor=")
# Review small CPU-only preview first; full evidence views queued explicitly.
s=s.replace("scene.cycles.samples=40", "scene.cycles.samples=16")
s=s.replace("scene.render.resolution_x=1200;scene.render.resolution_y=1200", "scene.render.resolution_x=900;scene.render.resolution_y=900")
s=s.replace("variant('Krag_Crusher')", "variant('Krag_Natural')")
s=s.replace("Krag_Crusher_Perspective.png", "Krag_Natural_Perspective.png")
p.write_text(s)
# All reviews CPU; no background EEVEE initialization while system diagnostics are unresolved.
r=Path(__file__).with_name('review_krag.py');t=r.read_text().replace("scene.render.engine='BLENDER_EEVEE'", "scene.render.engine='CYCLES'").replace("scene.cycles.samples=24", "scene.cycles.samples=16");r.write_text(t)
