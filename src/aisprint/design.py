from email.mime import application
import os
import argparse 
import yaml

from aisprint.application_preprocessing import ApplicationPreprocessor
from aisprint.deployments_generators import DeploymentsGenerator

from .utils import parse_dag, get_annotation_manager, print_header
from .annotations_parsing import run_aisprint_parser

def run_design(application_dir):

    """ Execute the AI-SPRINT pipeline to create the possible application designs:
        
        1. Read DAG file
        2. Parse AI-SPRINT annotations
        3. Create components' designs 
        4. Create AI-SPRINT possible deployments 
    """

    # print("\n")
    # print("# --------- #")
    # print("# AI-SPRINT #")
    # print("# --------- #")
    # print("# --------- #")
    # print("#   Design  #")
    # print("# --------- #")
    # print("\n")
    print_header()

    print("\n")
    print("[AI-SPRINT]: " + "Starting the design of the AI-SPRINT application: {}".format(
        os.path.basename(os.path.normpath(application_dir))))

    # 1) Read DAG file
    # ----------------
    # DAG filename: 'application_dag.yaml' 
    dag_file = os.path.join(application_dir, 'common_config', 'application_dag.yaml')
    dag_dict, num_components = parse_dag(dag_file)
    
    print("\n")
    print("[AI-SPRINT]: " + "Found {} components in the DAG with the following dependencies:".format(num_components))
    for component, next_component in dag_dict.items():
        if next_component['next'] != []:
            print("             " + "- {} -> {}".format(component, next_component['next']))
    
    # Get the directories of the components
    components_dirs = next(os.walk(os.path.join(application_dir, 'src')))[1]

    # TODO: CORRECT THIS CONSYTAINT FOR THE ALTERNATIVES
    # Check number of directories is equal to the number of components in the DAG
    # if len(components_dirs) != num_components:
    #     raise RuntimeError(
    #         "Number of components in the DAG does not match the number of directories in 'src'")

    # ----------------

    # 2) Parse and validate AI-SPRINT annotations
    # -------------------------------------------
    run_aisprint_parser(application_dir=application_dir)
    # -------------------------------------------

    # 3) Create AI-SPRINT base design with the Application Pre-Processor 
    # ------------------------------------------------------------------
    application_preprocessor = ApplicationPreprocessor(application_dir=application_dir)
    application_preprocessor.create_base_design()
    # ---------------------------------------
    
    # 4) Run partitionable_model annotation manager 
    # ---------------------------------------------
    # Run partitionable_model annotation manager
    annotation_manager = get_annotation_manager(
        application_dir=application_dir, which_annotation='detect_metric_drift')
    annotation_manager.process_annotations()
    # ---------------------------------------------

    # 5) Run partitionable_model annotation manager 
    # ---------------------------------------------
    # Run partitionable_model annotation manager
    annotation_manager = get_annotation_manager(
        application_dir=application_dir, which_annotation='partitionable_model')
    annotation_manager.process_annotations()
    # ---------------------------------------------
    
    # 6) Run early_exits_model annotation manager 
    # ---------------------------------------------
    # Run early_exits_model annotation manager
    annotation_manager = get_annotation_manager(
        application_dir=application_dir, which_annotation='early_exits_model')
    annotation_manager.process_annotations()
    # ---------------------------------------------
    
    # 7) Run model_performance annotation manager 
    # ---------------------------------------------
    # Run model_performance annotation manager
    annotation_manager = get_annotation_manager(
        application_dir=application_dir, which_annotation='model_performance')
    alternative_deployments = annotation_manager.process_annotations()
    # ---------------------------------------------

    # 8) Create all possible deployments (empty) with multi-cluster QoS constraints
    deployments_generator = DeploymentsGenerator(application_dir, alternative_deployments)
    deployments_dict = deployments_generator.create_deployments()
    # deployments_dict contains the deployments and the components-layers associations
    # 'base': 
    #   'c1': '1'
    #   'c2': '2'
    #   ...
    # 'deployment1':
    #   'c1': '1'
    #   'c2': '3'
    #   ...
    # ...
    
    # 9) Run annotation managers for optimal deployment
    # (e.g., exec_time to generate the constraints)
    # -------------------------------------------------

    # Run exec_time annotation manager for base deployment 
    annotation_manager = get_annotation_manager(
        application_dir=application_dir, which_annotation='exec_time')
    print("\n")
    print("[AI-SPRINT]: " + "Generating QoS constraints {} deployments..".format(len(deployments_dict.keys())))
    input_args = {'deployment_name': 'base', 'layers_assignment': deployments_dict['base']} 
    multi_cluster_dict = {} 
    multi_cluster_dict['System'] = {}
    multi_cluster_dict['System']['Deployments'] = {} 
    curr_qos_dict = annotation_manager.process_annotations(input_args)
    multi_cluster_dict['System']['Deployments']['base'] = curr_qos_dict

    for num_deployment in range(len(deployments_dict.keys())-1):
        deployment_name = 'deployment{}'.format(num_deployment+1)
        input_args = {'deployment_name': deployment_name, 'layers_assignment': deployments_dict[deployment_name]}
        curr_qos_dict = annotation_manager.process_annotations(input_args)
        multi_cluster_dict['System']['Deployments'][deployment_name] = curr_qos_dict
    # Save multi_cluster_dict
    qos_filename = os.path.join(
        application_dir, 'aisprint/deployments', 'multi_cluster_qos_constraints.yaml')
    with open(qos_filename, 'w') as f:
        yaml.dump(multi_cluster_dict, f, sort_keys=False) 

    print("             " + "Done! QoS constraints generated.\n")
    # -------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--application_dir", help="Path to the AI-SPRINT application.", required=True)
    args = vars(parser.parse_args())

    application_dir = args['application_dir']

    run_design(application_dir=application_dir)
    