import yaml

conf = None

with open('config.yaml', 'r') as file:
    conf = yaml.safe_load(file)   