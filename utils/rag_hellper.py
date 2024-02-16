def flatten_dict(*vars):
    flat = {}
    for var in vars:
        keys = [k for k in var]
        for key in keys:
            if isinstance(var[key], dict):
                flat.update(var[key])
            else:
                flat[key] = var[key]
    return flat
