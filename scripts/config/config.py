import os
from shutil import copyfile
import yaml

this_dirname = os.path.dirname(os.path.realpath(__file__))
config_fn = os.path.join(this_dirname, 'config.yaml')

def get_config():
    with open(config_fn) as f:
        config = yaml.safe_load(f)
    return config

def copy_config(outdir):
    copyfile(config_fn, os.path.join(outdir, 'config.yaml'))


config = get_config()