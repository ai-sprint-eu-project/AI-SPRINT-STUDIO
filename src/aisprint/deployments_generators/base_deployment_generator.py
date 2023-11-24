import os
import shutil
import yaml

from .deployment_generator import DeploymentGenerator


class BaseDeploymentGenerator(DeploymentGenerator): 

    def __init__(self, application_dir):
        
        self.application_dir = application_dir
    
    def component_is_partition(self, component_name, list_components):
        if not '_partitionX' in component_name:
            return False
        splitted_name = component_name.rsplit('_partitionX', 1)[0] 
        if splitted_name in list_components:
            return True
        return False
    
    def component_is_alternative(self, component_name, list_components):
        if not '_alternative' in component_name:
            return False
        splitted_name = component_name.rsplit('_alternative', 1)[0]
        if splitted_name in list_components:
            return True
        return False
    
    def create_deployment(self, deployment_name, dag_filename):
        ''' Create base deployment.

            Parameters:
                - deployment_name: name of the new deployment
                - dag: application dag of the current deployment 
        '''
        super().create_deployment(deployment_name, dag_filename)
    
        print("\n")
        print("[AI-SPRINT]: " + "Starting creating base application deployment..")

        # Copy original DAG
        shutil.copyfile(os.path.join(self.application_dir, 'common_config', 'application_dag.yaml'),
                        os.path.join(self.deployment_dir, 'application_dag.yaml'))

        # Copy tools directory
        shutil.copytree(os.path.join(self.application_dir, 'space4ai-d'), 
                        os.path.join(self.deployment_dir, 'space4ai-d'))
        shutil.copytree(os.path.join(self.application_dir, 'space4ai-r'), 
                        os.path.join(self.deployment_dir, 'space4ai-r'))
        shutil.copytree(os.path.join(self.application_dir, 'oscar'), 
                        os.path.join(self.deployment_dir, 'oscar'))
        shutil.copytree(os.path.join(self.application_dir, 'oscarp'), 
                        os.path.join(self.deployment_dir, 'oscarp'))
        shutil.copytree(os.path.join(self.application_dir, 'pycompss'), 
                        os.path.join(self.deployment_dir, 'pycompss'))
        shutil.copytree(os.path.join(self.application_dir, 'im'), 
                        os.path.join(self.deployment_dir, 'im'))
        shutil.copytree(os.path.join(self.application_dir, 'ams'), 
                        os.path.join(self.deployment_dir, 'ams'))

        # Create 'src' with symbolic links to base designs
        os.makedirs(os.path.join(self.deployment_dir, 'src'))

        designs_dir = '../../../designs'
        for component_name in self.dag_dict['System']['components']:
            source_design = os.path.join(designs_dir, component_name, 'base')
            symlink = os.path.join(
                os.path.abspath(self.deployment_dir), 'src', component_name)
            os.symlink(source_design, symlink)

        # Create production deployment #
        # ---------------------------- #
        candidate_resources_file = os.path.join(
            self.application_dir, 'common_config', 'candidate_resources.yaml')
        candidate_deployments_file = os.path.join(
            self.application_dir, 'common_config', 'candidate_deployments.yaml')
        production_deployment_file = os.path.join(
            self.deployment_dir, 'production_deployment.yaml')
        # Check candidate deployments and candidate resources exist
        if not os.path.exists(candidate_deployments_file):
            raise Exception(
                "No 'candidate_deployments.yaml' file exists in '{}/common_config' folder".format(self.application_dir))
        if not os.path.exists(candidate_resources_file):
            raise Exception(
                "No 'candidate_resources.yaml' file exists in '{}/common_config' folder".format(self.application_dir))
        with open(candidate_deployments_file, 'r') as f:
            candidate_deployments = yaml.safe_load(f)
        with open(candidate_resources_file, 'r') as f:
            candidate_resources = yaml.safe_load(f)
        
        production_deployment = {}
        production_deployment['System'] = {}
        production_deployment['System']['name'] = candidate_resources['System']['name']
        
        temp_dict = {}
        selected_execution_layers = []
        selected_resources = []
        for component_name, component_dict in candidate_deployments['Components'].items():
            if self.component_is_partition(
                    component_name, list(candidate_deployments['Components'].keys())):
                continue
            if self.component_is_alternative(
                    component_name, list(candidate_deployments['Components'].keys())):
                continue
        
            temp_dict[component_name] = {}
            temp_dict[component_name]['name'] = component_dict['name']

            # Select first execution layer
            execution_layer = component_dict['candidateExecutionLayers'][0]
            temp_dict[component_name]['executionLayer'] = execution_layer
            selected_execution_layers.append(execution_layer)
        
            # Get first container and resource
            container1 = candidate_deployments['Components'][component_name]['Containers']['container1'] 
            temp_dict[component_name]['Containers'] = {'container1': {}}
            for k, v in container1.items():
                if k == 'candidateExecutionResources':
                    k = 'selectedExecutionResource'
                    v = v[0]
                    selected_resources.append(v)
                temp_dict[component_name][
                    'Containers']['container1'][k] = v
        
        # Get only the reference to selected resources
        net_temp_dict = {}
        for k, v in candidate_resources['System']['NetworkDomains'].items():
            subkeys = list(v.keys())
            if not 'ComputationalLayers' in subkeys:
                # Copy entire
                net_temp_dict[k] = v
            else:
                # computational_layers = candidate_resources[
                #     'System']['NetworkDomains']['ComputationalLayers']
                net_temp_dict[k] = {}
                for sk, sv in v.items():
                    if sk != 'ComputationalLayers':
                        net_temp_dict[k][sk] = sv
                computational_layers = v['ComputationalLayers']
                net_temp_dict[k]['ComputationalLayers'] = {}
                at_least_one = False
                for cl_k, cl_v in computational_layers.items():
                    layer_number = int(cl_k.split('computationalLayer')[1])
                    if layer_number in selected_execution_layers:
                        at_least_one = True
                        if not cl_k in net_temp_dict[k]['ComputationalLayers']:
                            net_temp_dict[k]['ComputationalLayers'][cl_k] = {}
                        for cl_v_k, cl_v_v in cl_v.items():
                            if cl_v_k != 'Resources':
                                net_temp_dict[k][
                                    'ComputationalLayers'][cl_k][cl_v_k] = cl_v_v
                            else:
                                net_temp_dict[k][
                                    'ComputationalLayers'][cl_k][cl_v_k] = {} 
                                for rk, rv in cl_v_v.items():
                                    name = rv['name']
                                    if name in selected_resources:
                                        net_temp_dict[k][
                                            'ComputationalLayers'][cl_k][cl_v_k][rk] = rv
                if not at_least_one:
                    del net_temp_dict[k]
        
        production_deployment['System']['NetworkDomains'] = net_temp_dict 
        production_deployment['System']['Components'] = temp_dict 
        production_deployment['System']['DeploymentName'] = 'base' 
        
        # Save the production_deployment.yaml file in optimal_deployment 
        optimal_deployment_path = os.path.join(
            os.path.abspath(self.application_dir), 'aisprint', 'deployments', 'optimal_deployment')
        if not os.path.exists(optimal_deployment_path):
            os.makedirs(optimal_deployment_path)
        with open(os.path.join(optimal_deployment_path, 'production_deployment.yaml'), 'w') as f:
            yaml.dump(production_deployment, f, sort_keys=False)
        print("             " + "Done! Current optimal deployment is '{}'".format(deployment_name))