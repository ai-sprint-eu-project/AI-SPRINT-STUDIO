import os
import shutil
import yaml
import numpy as np

AISPRINT_ANNOTATIONS = ['component_name', 'exec_time', 'expected_throughput', 'model_performance', 
                        'partitionable_model', 'device_constraints', 'early_exits_model', 'detect_metric_drift', 'security', 'annotation']

def parse_dag(dag_file):
    with open(dag_file, 'r') as f:
        dag = yaml.safe_load(f) 
    
    dag = dag['System']
    
    dag_dict = {}

    # These will help to find leaf nodes
    source_components = [] 
    target_components = [] 

    if dag['dependencies'] is not None and dag['dependencies'] != []:
        for idx, dependency in enumerate(dag['dependencies']):

            # Check dependencies are well formatted
            # e.g., we need [['CX', 'CY', p]]
            if len(dependency) != 3:
                raise Exception("Bad dependencies format in the provided DAG file. " + 
                                "Dependencies must be triplets '['CX', 'CY', Prob.]'.")

            # Get source and target components
            source_c = dependency[0]
            target_c = dependency[1]

            # Save source_c in source_components 
            if not source_c in source_components:
                source_components.append(source_c)
            # Save target_c in target_components 
            if not target_c in target_components:
                target_components.append(target_c)

            # Add component in the dag_dict
            if not source_c in dag_dict:
                dag_dict[source_c] = {'next': [target_c]}
            else:
                if not target_c in dag_dict[source_c]['next']:
                    dag_dict[source_c]['next'].append(target_c)
    
        # Find leaf components: 
        # reached by other components but not reaching other components
        for target_c in target_components:
            if target_c not in source_components:
                # Add leaf component as having empty 'next' components 
                if idx == len(dag['dependencies']) - 1:
                    dag_dict[target_c] = {'next': []}
    else:
        target_components.append(dag['components'][0])

        dag_dict[dag['components'][0]] = {'next': []}
        
    
    # Get total number of components
    num_components = len(dag_dict.keys())
    
    # Check dependencies components and DAG components match
    dependencies_components = np.unique(list(dag_dict.keys()))
    dag_components = np.unique(list(dag['components']))
    
    if not np.all(dependencies_components == dag_components):
        raise Exception("Components in 'dependencies' and 'components' in " + 
                        "the DAG YAML file do not match.")

    return dag_dict, num_components
    
def get_component_folder(application_dir, dag, component_name):
    with open(os.path.join(application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
        annotations_dict = yaml.safe_load(f)
    
    for main_path, annotations in annotations_dict.items():
        if annotations['component_name']['name'] == component_name:
            return main_path.split('main.py')[0] 
        else:
            if 'alternative_components' in dag['System']:
                if annotations['component_name']['name'] in dag['System']['alternative_components']:
                    if component_name in dag['System']['alternative_components'][annotations['component_name']['name']]:
                        # remove basename 
                        no_basename = main_path.rsplit(os.path.basename(os.path.normpath(
                            main_path.split('main.py')[0])), 1)[0]
                        return os.path.join(no_basename, component_name)


def get_annotation_managers(application_dir):
    ''' Return annotation managers dictionary with items
        annotation: AnnotationManager
    '''

    from .annotations import annotation_managers

    with open(os.path.join(application_dir, 'common_config', 'application_dag.yaml'), 'r') as f:
        dag_dict = yaml.safe_load(f)
    application_name = dag_dict['System']['name'] 

    annotation_managers_dict = {}
    for aisprint_annotation in AISPRINT_ANNOTATIONS:
        if aisprint_annotation == 'annotation':
            continue
        manager_module_name = aisprint_annotation + '_manager'
        manager_class_name = "".join([s.capitalize() for s in manager_module_name.split('_')])
        manager_class = getattr(annotation_managers, manager_class_name)
        annotation_managers_dict[aisprint_annotation] = manager_class(
            application_name=application_name, application_dir=application_dir)
    return annotation_managers_dict

def get_annotation_manager(application_dir, which_annotation):
    ''' Return AnnotationManager of 'which_annotation'. 
    '''

    from .annotations import annotation_managers

    with open(os.path.join(application_dir, 'common_config', 'application_dag.yaml'), 'r') as f:
        dag_dict = yaml.safe_load(f)
    application_name = dag_dict['System']['name'] 

    manager_module_name = which_annotation + '_manager'
    manager_class_name = "".join([s.capitalize() for s in manager_module_name.split('_')])
    manager_class = getattr(annotation_managers, manager_class_name)
    annotation_manager = manager_class(
        application_name=application_name, application_dir=application_dir)
    return annotation_manager 

def run_annotation_managers(annotation_managers, deployment_name):
    # Run the annotation manager corresponding to each annotation
    for aisprint_annotation in AISPRINT_ANNOTATIONS:
        if aisprint_annotation == 'annotation':
            continue
        annotation_manager = annotation_managers[aisprint_annotation]
        annotation_manager.generate_configuration_files(deployment_name)

def search_image(component_name, docker_images):
    base_docker_images = []
    segm1_docker_images = []
    segm2_docker_images = []
    
    for docker_image in docker_images:
        # This will find "NAME_base" in strings with "NAME_base_amd64:latest"
        name = os.path.basename(docker_image).split(':')[0].rsplit('_', 1)[0]
        if component_name == name.rsplit("_", 1)[0]:
            base_docker_images.append(docker_image)
        else:
            # Check for partitionX_P
            if 'partition' in name.rsplit('_', 1)[0]:
                which_segment = name.rsplit('_', 1)[1]
                if int(which_segment) == 1:
                    segm1_docker_images.append(docker_image) 
                elif int(which_segment) == 2:
                    segm2_docker_images.append(docker_image) 
    return base_docker_images, segm1_docker_images, segm2_docker_images

def complete_candidate_deployments(application_dir, candidate_deployments):
    print("\n")
    print("[AI-SPRINT]: " + "Completing {} with docker images names..".format(candidate_deployments))
    
    with open(candidate_deployments, 'r') as f:
        candidate_deployment_dict = yaml.safe_load(f) 
    with open(os.path.join(application_dir, 'aisprint','designs', 'containers.yaml'), 'r') as f:
        containers_dict = yaml.safe_load(f)
    
    components = candidate_deployment_dict['Components']
    containers_components = containers_dict['components'].keys()
    for component in components:
        component_name = components[component]['name']
        if component_name not in containers_components:
            continue
        # get corresponding image name
        base_image_names, segm1_image_names, segm2_image_names = search_image(
            component_name, containers_dict['components'][component_name]['docker_images'])
        
        container_names = list(components[component]['Containers'].keys())
        for container_name in container_names:
            if len(base_image_names) == 1:
                candidate_deployment_dict['Components'][component]['Containers'][container_name][
                    'image'] = base_image_names[0] 
            else:
                candidate_deployment_dict['Components'][component]['Containers'][container_name][
                    'image'] = base_image_names
        if len(segm1_image_names) > 0 and len(segm2_image_names) > 0:
            partition_component = component + '_partitionX_1'
            container_names = list(components[partition_component]['Containers'].keys())
            for container_name in container_names:
                candidate_deployment_dict['Components'][partition_component]['Containers'][container_name]['image'] = [] 
                for image_name in segm1_image_names:
                    candidate_deployment_dict['Components'][partition_component]['Containers'][container_name]['image'].append(image_name)
            partition_component = component + '_partitionX_2'
            container_names = list(components[partition_component]['Containers'].keys())
            for container_name in container_names:
                candidate_deployment_dict['Components'][partition_component]['Containers'][container_name]['image'] = [] 
                for image_name in segm2_image_names:
                    candidate_deployment_dict['Components'][partition_component]['Containers'][container_name]['image'].append(image_name)
    
    with open(candidate_deployments, 'w') as f:
        yaml.dump(candidate_deployment_dict, f, sort_keys=False)

def get_architecture(execution_layer, selected_resource, resources_dict):
    for network_domain in resources_dict['NetworkDomains'].keys():
        for computational_layer in resources_dict['NetworkDomains'][network_domain]['ComputationalLayers'].keys():
            if int(computational_layer.rsplit('computationalLayer')[1]) == int(execution_layer):
                resources = (resources_dict['NetworkDomains'][network_domain]['ComputationalLayers'][computational_layer]['Resources'].keys())
                for resource in resources:
                    if resources_dict['NetworkDomains'][network_domain]['ComputationalLayers'][computational_layer]['Resources'][resource]['name'] == selected_resource:
                        processors = list(resources_dict['NetworkDomains'][network_domain]['ComputationalLayers'][computational_layer]['Resources'][resource]['processors'].keys())
                        for processor in processors:
                            architecture = resources_dict['NetworkDomains'][network_domain]['ComputationalLayers'][computational_layer]['Resources'][resource]['processors'][processor]['architecture']
                        return architecture

def complete_production_deployment(application_dir, production_deployment):
    print("\n")
    print("[AI-SPRINT]: " + "Completing {} with docker images names..".format(production_deployment))
    
    with open(production_deployment, 'r') as f:
        production_deployment_dict = yaml.safe_load(f) 
    with open(os.path.join(application_dir, 'aisprint','designs', 'containers.yaml'), 'r') as f:
        containers_dict = yaml.safe_load(f)
    with open(os.path.join(application_dir, 'common_config', 'candidate_resources.yaml'), 'r') as f:
        resources_dict = yaml.safe_load(f)
    resources_dict = resources_dict['System']
    
    components = production_deployment_dict['System']['Components']
    containers_components = containers_dict['components'].keys()
    for component in components:
        component_name = components[component]['name']
        if component_name not in containers_components:
            continue
        # get corresponding image name
        base_image_names, _, _ = search_image(
            component_name, containers_dict['components'][component_name]['docker_images'])
        
        container_names = list(components[component]['Containers'].keys())
        execution_layer = components[component]['executionLayer']
        for container_name in container_names:
            selected_resource = components[component]['Containers'][container_name]['selectedExecutionResource']
            architecture = get_architecture(execution_layer, selected_resource, resources_dict)
            base_image_name = [b for b in base_image_names if architecture in b][0]
            production_deployment_dict['System']['Components'][component]['Containers'][container_name][
                'image'] = base_image_name 
        
    with open(production_deployment, 'w') as f:
        yaml.dump(production_deployment_dict, f, sort_keys=False)
    
def print_header():
    print('             _____      _____ _____  _____  _____ _   _ _______   _____            _             ')
    print('       /\   |_   _|    / ____|  __ \|  __ \|_   _| \ | |__   __| |  __ \          (_)            ')
    print('      /  \    | |_____| (___ | |__) | |__) | | | |  \| |  | |    | |  | | ___  ___ _  __ _ _ __  ')
    print('     / /\ \   | |______\___ \|  ___/|  _  /  | | | . ` |  | |    | |  | |/ _ \/ __| |/ _` | \'_ \ ')
    print('    / ____ \ _| |_     ____) | |    | | \ \ _| |_| |\  |  | |    | |__| |  __/\__ \ | (_| | | | |')
    print('   /_/    \_\_____|   |_____/|_|    |_|  \_\_____|_| \_|  |_|    |_____/ \___||___/_|\__, |_| |_|')
    print('                                                                                      __/ |      ')
    print('                                                                                     |___/       ')
    print('                                                                                                 ')
