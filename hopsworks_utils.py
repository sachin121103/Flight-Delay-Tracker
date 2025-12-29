import hopsworks
from config import hopsworks_api_key

def get_feature_store():
    project = hopsworks.login(api_key_value=hopsworks_api_key)
    return project.get_feature_store()

def get_or_create_feature_group(fs, name, version, primary_key, description, online_enabled=False):
    try:
        fg = fs.get_feature_group(name=name, version=version)
        print(f"Existing Feature Group Found: {name}")
    except:
        fg = fs.create_feature_group(name=name, version=version, 
                                     primary_key=primary_key, description=description, online_enabled=online_enabled)
        print(f"Created feature group: {name}")
    
    return fg

