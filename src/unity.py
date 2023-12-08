import os
import UnityPy

def load_assetbundle(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path {path} does not exist. Cannot load assetbundle.")
    asset = UnityPy.load(path)

    return list(asset.container.values())[0].get_obj()

def load_asset(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path {path} does not exist. Cannot load asset.")
    asset = UnityPy.load(path)

    return asset