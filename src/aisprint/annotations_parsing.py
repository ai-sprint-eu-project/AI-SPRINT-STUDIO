import os
import argparse 
import yaml

from .utils import AISPRINT_ANNOTATIONS
from .annotations import annotation_validators
from .annotations.annotations_parser import QoSAnnotationsParser


def parse_aisprint_annotations(src_dir):
    # Get the directories of the components
    components_dirs = next(os.walk(src_dir))[1]

    # For each component dir, find annotations in 'main.py' 
    # First check that a 'main.py' exists for each partition
    missing_mains = []
    for component_dir in components_dirs:
        filenames = next(os.walk(os.path.join(src_dir, component_dir)))[2]

        if 'main.py' not in filenames:
            missing_mains.append(component_dir)
    
    if missing_mains != []:
        error_msg = "'main.py' script missing for the following components: "
        for mm in missing_mains:
            error_msg += "{}; ".format(mm)
        raise RuntimeError(error_msg)

    # Parse
    annotations_dict = {}
    for component_dir in components_dirs:
        main_script = os.path.join(src_dir, component_dir, 'main.py')

        qos_annot_parser = QoSAnnotationsParser(main_script) 
        annotations_dict[main_script] = qos_annot_parser.parse()
    
    return annotations_dict

def store_aisprint_annotations(application_dir):
    ''' Parse AI-SPRINT annotations from the main.py functions of the components.

        Annotations are stored in application_dir/common_config/annotations.yaml file.
    '''

    # Parse annotations
    # --------------------
    print("\n")
    print("[AI-SPRINT]: " + "Parsing AI-SPRINT annotations..")
    src_dir = os.path.join(application_dir , 'src')

    # Parse
    annotations_dict = parse_aisprint_annotations(src_dir) 
    
    # Check all the components have a 'component_name'
    missing_names = []
    for main_script, annotations in annotations_dict.items():
        if 'component_name' not in annotations:
            missing_names.append(main_script) 
    
    if missing_names != []:
        error_msg = "'component_name' is missing in the following scripts"
        for mn in missing_names:
            error_msg += "{}; ".format(mn)
        raise RuntimeError(error_msg)
    
    # Save annotations
    with open(os.path.join(application_dir, 'common_config', 'annotations.yaml'), 'w') as f:
        yaml.dump(annotations_dict, f)
    print("[AI-SPRINT]: " + "Done! Annotations parsed and stored in: {}".format(
        os.path.join(application_dir, 'common_config', 'annotations.yaml')))

    return annotations_dict

def validate_aisprint_annotations(application_dir):
    ''' Validate the AI-SPRINT annotations with the annotation validators.
    '''

    # Load annotations
    with open(os.path.join(application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
        annotations_dict = yaml.safe_load(f)

    dag_file = os.path.join(application_dir, 'common_config', 'application_dag.yaml')
    
    # Validate annotations
    print("\n")
    print("[AI-SPRINT]: " + "Validating AI-SPRINT annotations..")
    for aisprint_annotation in AISPRINT_ANNOTATIONS:
        if aisprint_annotation == 'annotation':
            continue
        validator_module_name = aisprint_annotation + '_validator'
        validator_class_name = "".join([s.capitalize() for s in validator_module_name.split('_')])
        validator_class = getattr(annotation_validators, validator_class_name)
        annotation_validator = validator_class(annotations_dict, dag_file)
        annotation_validator.check_annotation_validity()
    print("[AI-SPRINT]: " + "Done!")
    # -------------------

def run_aisprint_parser(application_dir):
    store_aisprint_annotations(application_dir)
    validate_aisprint_annotations(application_dir)