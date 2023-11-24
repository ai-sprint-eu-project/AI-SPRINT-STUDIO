import os
import shutil
import yaml

import numpy as np
import itertools

from .deployment_generator import DeploymentGenerator
from .base_deployment_generator import BaseDeploymentGenerator
from .empty_deployment_generator import EmptyDeploymentGenerator
from .alternative_deployment_generator import AlternativeDeploymentGenerator


class DeploymentsGenerator(): 

    def __init__(self, application_dir, alternative_deployments=None):
        
        self.application_dir = application_dir
        
        design_dir = os.path.join(self.application_dir, 'aisprint', 'designs') 
        with open(os.path.join(application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
            self.annotations = yaml.safe_load(f)
        if os.path.exists(os.path.join(design_dir, 'component_partitions.yaml')):
            with open(os.path.join(design_dir, 'component_partitions.yaml'), 'r') as f:
                self.partition_dict = yaml.safe_load(f)
        
        self.alternative_deployments = alternative_deployments

        with open(os.path.join(self.application_dir, 'common_config', 'candidate_deployments.yaml'), 'r') as f:
            self.candidate_deployments = yaml.safe_load(f)
        self.candidate_deployments = self.candidate_deployments['Components']
    
    def get_combinations(self):
        components = self.partition_dict['components']
        combinations = []
        for component in components:
            partitions = components[component]['partitions']
            filtered_partitions = np.unique([component + '_' + p.split('_')[0] for p in partitions])
            combinations.append(filtered_partitions)
        return list(itertools.product(*combinations))
    
    def get_layer_combinations(self, combination):
        combinations = []
        components_combination = []
        for component in combination:
            if 'base' == component.rsplit('_', 1)[1]:
                for component_k in self.candidate_deployments:
                    if self.candidate_deployments[component_k]['name'] == component.rsplit('_', 1)[0]:
                        components_combination.append(component.rsplit('_', 1)[0])
                        combinations.append(self.candidate_deployments[component_k]['candidateExecutionLayers'])
            elif 'partition' in component.rsplit('_', 1)[1]:
                for component_k in self.candidate_deployments:
                    if self.candidate_deployments[component_k]['name'] == component.rsplit(
                            '_partition', 1)[0] + '_partitionX_1':
                        components_combination.append(component + '_1')
                        combinations.append(self.candidate_deployments[component_k]['candidateExecutionLayers'])
                for component_k in self.candidate_deployments:
                    if self.candidate_deployments[component_k]['name'] == component.rsplit(
                            '_partition', 1)[0] + '_partitionX_2':
                        components_combination.append(component + '_2')
                        combinations.append(self.candidate_deployments[component_k]['candidateExecutionLayers'])
        return list(itertools.product(*combinations)), components_combination
                
    def create_deployments(self):
        assignments_dict = {}
        num_deployment = 0
        if self.alternative_deployments is None:
            # No components alternatives
            combinations = self.get_combinations()
            for combination in combinations:
                layer_combinations, components_combination = self.get_layer_combinations(combination)
                
                num_base = len([c for c in combination if 'base' in c])
                
                for lc_idx, layer_combination in enumerate(layer_combinations):
                    if len(combination) == num_base and lc_idx == 0:
                        base_deployment_generator = BaseDeploymentGenerator(self.application_dir)
                        base_deployment_generator.create_deployment(
                            deployment_name='base', 
                            dag_filename=os.path.join(
                                self.application_dir, 'common_config', 'application_dag.yaml'))
                        assignments_dict['base'] = {k: v for k,v in zip(components_combination, layer_combination)}
                    else:
                        num_deployment += 1
                        empty_deployment_generator = EmptyDeploymentGenerator(self.application_dir)
                        empty_deployment_generator.create_deployment(
                            deployment_name='deployment{}'.format(num_deployment), 
                            dag_filename=os.path.join(self.application_dir, 'common_config', 'application_dag.yaml'), 
                            partitions_dict=self.partition_dict, components_combination=combination)
                        assignments_dict['deployment{}'.format(num_deployment)] = {k: v for k,v in zip(components_combination, layer_combination)}
            return assignments_dict 
        else:
            # Components alternatives
            for deployment in self.alternative_deployments:
                components_combination = self.alternative_deployments[deployment]['components']
                components_combination = [p + '_base' for p in components_combination]
                layer_combinations, components_combination = self.get_layer_combinations(components_combination)
                    
                for lc_idx, layer_combination in enumerate(layer_combinations):
                    if deployment == 'base' and lc_idx == 0:
                        base_deployment_generator = BaseDeploymentGenerator(self.application_dir)
                        base_deployment_generator.create_deployment(deployment_name='base', 
                            dag_filename=os.path.join(self.application_dir, 'common_config', 'application_dag.yaml'))
                        assignments_dict['base'] = {k: v for k,v in zip(components_combination, layer_combination)}
                    else:
                        num_deployment += 1
                        empty_deployment_generator = AlternativeDeploymentGenerator(self.application_dir)
                        empty_deployment_generator.create_deployment(deployment_name='deployment{}'.format(num_deployment), 
                            dag_filename=os.path.join(self.application_dir, 'common_config', 'application_dag.yaml'), 
                            deployment=self.alternative_deployments[deployment])
                        assignments_dict['deployment{}'.format(num_deployment)] = {k: v for k,v in zip(components_combination, layer_combination)}

            return assignments_dict 