"""Exact migration of existing transform-driven corrective expressions."""
POINT_FIELDS=['interpolation','handle_left_type','handle_right_type','easing','amplitude','back','period','type']

def point_contract(point):
    return {'co':list(point.co),'handle_left':list(point.handle_left),'handle_right':list(point.handle_right),**{name:getattr(point,name) for name in POINT_FIELDS}}

TARGET_FIELDS=['id_type','bone_target','data_path','transform_type','transform_space','rotation_mode','use_fallback_value','fallback_value']

def contract(keys):
    rows=[]
    if not keys.animation_data:return rows
    for curve in keys.animation_data.drivers:
        variables=[]
        for var in curve.driver.variables:
            targets=[]
            for target in var.targets:
                fields={name:getattr(target,name) for name in TARGET_FIELDS if hasattr(target,name)}
                fields['id']=target.id.name_full if target.id else None;targets.append(fields)
            variables.append({'name':var.name,'type':var.type,'targets':targets})
        modifiers=[]
        for mod in curve.modifiers:
            if mod.type!='GENERATOR':raise RuntimeError('Unaccounted corrective-driver modifier '+mod.type)
            modifiers.append({'type':mod.type,'mode':mod.mode,'poly_order':mod.poly_order,'coefficients':list(mod.coefficients),'use_additive':mod.use_additive,'mute':mod.mute})
        rows.append({'path':curve.data_path,'index':curve.array_index,'mute':curve.mute,'extrapolation':curve.extrapolation,'type':curve.driver.type,'expression':curve.driver.expression,'use_self':curve.driver.use_self,'variables':variables,'modifiers':modifiers,'keyframes':[point_contract(point) for point in curve.keyframe_points]})
    return sorted(rows,key=lambda row:(row['path'],row['index']))

def migrate(source,target):
    expected=contract(source)
    if not source.animation_data:return expected
    key_paths={key.path_from_id('value'):key.name for key in source.key_blocks}
    for old in source.animation_data.drivers:
        if old.data_path not in key_paths:raise RuntimeError('Unexpected source corrective path '+old.data_path)
        curve=target.key_blocks[key_paths[old.data_path]].driver_add('value')
        curve.mute=old.mute;curve.extrapolation=old.extrapolation;driver=curve.driver
        driver.type=old.driver.type;driver.expression=old.driver.expression;driver.use_self=old.driver.use_self
        for existing in list(driver.variables):driver.variables.remove(existing)
        for original in old.driver.variables:
            var=driver.variables.new();var.name=original.name;var.type=original.type
            for a,b in zip(original.targets,var.targets):
                # id_type is readonly for transform variables; its default and
                # all final target properties are verified by the contract.
                if hasattr(b,'id_type') and b.id_type!=a.id_type and not b.bl_rna.properties['id_type'].is_readonly:b.id_type=a.id_type
                b.id=a.id
                for name in TARGET_FIELDS:
                    if name=='id_type' or not hasattr(a,name):continue
                    prop=b.bl_rna.properties.get(name)
                    if prop and not prop.is_readonly and getattr(b,name)!=getattr(a,name):setattr(b,name,getattr(a,name))
        while len(curve.keyframe_points):curve.keyframe_points.remove(curve.keyframe_points[-1],fast=True)
        if len(old.keyframe_points):
            curve.keyframe_points.add(len(old.keyframe_points))
            for a,b in zip(old.keyframe_points,curve.keyframe_points):
                b.co=a.co
                for name in POINT_FIELDS:setattr(b,name,getattr(a,name))
                b.handle_left=a.handle_left;b.handle_right=a.handle_right
        for mod in list(curve.modifiers):curve.modifiers.remove(mod)
        for original in old.modifiers:
            mod=curve.modifiers.new(original.type);mod.mode=original.mode;mod.poly_order=original.poly_order;mod.coefficients=list(original.coefficients);mod.use_additive=original.use_additive;mod.mute=original.mute
    if contract(target)!=expected:raise RuntimeError('Corrective-driver migration differs from actual source')
    return expected
