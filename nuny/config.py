import yaml

conf = None


def load_conf():
    global conf
    with open('config.yaml', 'r') as file:
        conf = yaml.safe_load(file)
