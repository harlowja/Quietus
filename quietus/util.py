import yaml


def load_yaml(path):
    with open(path, 'rb') as fh:
        return load_yaml_text(fh.read())


def load_yaml_text(text):
    return yaml.safe_load(text)
