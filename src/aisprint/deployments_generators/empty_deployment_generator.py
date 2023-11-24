import os
import shutil
import yaml

from .deployment_generator import DeploymentGenerator


class EmptyDeploymentGenerator(DeploymentGenerator): 

    def __init__(self, application_dir):
        
        self.application_dir = application_dir
    
    def component_has_early_exits(self, component):
        with open(os.path.join(self.application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
            annotations = yaml.safe_load(f)
        
        for _, item_dict in annotations.items():
            if (item_dict['component_name']['name'] == component and 'early_exits_model' in list(item_dict.keys())):
                return True
        return False
    
    def get_transition_probability(self, dependencies, component1, component2):
        for dependency in dependencies:
            if dependency[0] == component1 and dependency[1] == component2:
                return dependency[2]
        return 1
    
    def get_ee_transition_probability(self, component, idx):
        with open(os.path.join(self.application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
            annotations = yaml.safe_load(f)
        
        for _, item_dict in annotations.items():
            if (item_dict['component_name']['name'] == component and 'early_exits_model' in list(item_dict.keys())):
                return item_dict['early_exits_model']['transition_probabilities'][idx]
    
    def create_dag(self, partitions_dict, components_combination):

        def is_the_first_in_a_dependency(component_name):
            base_dependencies = self.dag_dict['System']['dependencies']
            if base_dependencies is not None and base_dependencies != []:
                for d in base_dependencies:
                    if d[0] == component_name:
                        return True
            else:
                if self.dag_dict['System']['components'] == component_name:
                    return True
            return False
        
        components = partitions_dict['components']
        # filtered_dict contains the partitions for each component
        filtered_dict = {}
        # ee_components is a list contains all the names of the components having early exits
        ee_components = []
        for component in components:
            combination = [c for c in components_combination if (
                c.rsplit('_partition', 1)[0] == component or c.rsplit('_base', 1)[0] == component)][0]
            combination = combination.split(component + '_')[1]
            partitions = components[component]['partitions']
            filtered_partitions = [p for p in partitions if combination in p]
            filtered_partitions = sorted(filtered_partitions)
            filtered_dict[component] = filtered_partitions
            if self.component_has_early_exits(component):
                ee_components.append(component)
        
        base_dependencies = self.dag_dict['System']['dependencies']
        new_dependencies = []
        new_components = []
        design_dict = {}

        if base_dependencies is None or base_dependencies == []:
            # Only one component
            component1 = self.dag_dict['System']['components'][0]
            num_partitions = len(filtered_dict[component1])
            if num_partitions > 1:
                # Only one component partitioned

                # Loop over the partitions
                # At each iteration we add the following dependency c1_partitionX_idx -> c1_partitionX_idx+1
                for idx in range(num_partitions-1):
                    new_dependency = []
                    segm1 = filtered_dict[component1][idx]
                    new_dependency.append(component1 + '_' + segm1)
                    if component1 + '_' + segm1 not in new_components:
                        new_components.append(component1 + '_' + segm1)
                    if component1 not in design_dict:
                        design_dict[component1] = []
                    if segm1 not in design_dict[component1]:
                        design_dict[component1].append(segm1)
                        
                    segm2 = filtered_dict[component1][idx+1]
                    new_dependency.append(component1 + '_' + segm2)
                    new_dependency.append(1)
                    if new_dependency not in new_dependencies:
                        new_dependencies.append(new_dependency)
                    if component1 + '_' + segm2 not in new_components:
                        new_components.append(component1 + '_' + segm2)
                    if segm2 not in design_dict[component1]:
                        design_dict[component1].append(segm2)
            else:
                # Only one component NOT partitioned
                # dependency will be empty (as in the original DAG)
                new_dependency = []
                if component1 not in new_components:
                    new_components.append(component1)
                if component1 not in design_dict:
                    design_dict[component1] = []
                if 'base' not in design_dict[component1]:
                    design_dict[component1].append('base')
        else:
            # At least two components

            # Loop over the depndencies [c1, c2, p]
            for dependency in base_dependencies:
                component1 = dependency[0]
                component2 = dependency[1]

                num_partitions = len(filtered_dict[component1])
                if num_partitions > 1:
                    # c1 is partitioned

                    # Loop over the partitions
                    # At each iteration we add the following dependency c1_partitionX_idx -> c1_partitionX_idx+1
                    # At the last iteration we add the c1_partitionX_idx+N -> c2_partitionX_idx if c2 is partitioned
                    # c1_partitionX_idx+N -> c2 otherwise
                    for idx in range(num_partitions):
                        new_dependency = []
                        segm1 = filtered_dict[component1][idx]
                        new_dependency.append(component1 + '_' + segm1)
                        if component1 + '_' + segm1 not in new_components:
                            new_components.append(component1 + '_' + segm1)
                        if component1 not in design_dict:
                            design_dict[component1] = []
                        if segm1 not in design_dict[component1]:
                            design_dict[component1].append(segm1)
                        if idx == num_partitions-1: 
                            num_partitions2 = len(filtered_dict[component2])
                            if num_partitions2 > 1:
                                new_dependency.append(component2 + '_' + filtered_dict[component2][0])
                            else:
                                new_dependency.append(component2)
                                if component2 not in new_components:
                                    new_components.append(component2)
                                if component2 not in design_dict:
                                    design_dict[component2] = []
                                if 'base' not in design_dict[component2]:
                                    design_dict[component2].append('base')
                        else:
                            segm2 = filtered_dict[component1][idx+1]
                            new_dependency.append(component1 + '_' + segm2)

                        # This part is needed in the case of early exits
                        # If it is not the last partition then, we must take as 
                        # transition probability the user-defined one 
                        if component1 in ee_components and idx < num_partitions-1:
                            new_dependency.append(self.get_ee_transition_probability(component1, idx))
                        else:
                            if idx == num_partitions-1:
                                new_dependency.append(self.get_transition_probability(base_dependencies, component1, component2))
                            else:
                                new_dependency.append(1) # NOTE: in the case they are normal partitions, we assume always 1 as transition probability

                        if new_dependency not in new_dependencies:
                            new_dependencies.append(new_dependency)
                        
                        if idx < num_partitions-1:
                            # This part is needed in the case of early exits
                            # If it is not the last partition then, we must add 
                            # the dependency from the partition to the next component
                            if component1 in ee_components:
                                new_dependency = [new_dependency[0]]
                                num_partitions2 = len(filtered_dict[component2])
                                if num_partitions2 > 1:
                                    new_dependency.append(component2 + '_' + filtered_dict[component2][0])
                                else:
                                    new_dependency.append(component2)
                                    if component2 not in new_components:
                                        new_components.append(component2)
                                    if component2 not in design_dict:
                                        design_dict[component2] = []
                                    if 'base' not in design_dict[component2]:
                                        design_dict[component2].append('base')
                                # User-defined ee probabilities are the transition probability between partitions.
                                # Thus, the probability from one partition to the next component is 1-p
                                new_dependency.append(1-self.get_ee_transition_probability(component1, idx))  # use the original transition probability

                                if new_dependency not in new_dependencies:
                                    new_dependencies.append(new_dependency)
                else:
                    # c1 is not partitioned
                    # Add c1 -> c2_partitionX_idx if c2 is partitioned
                    # c1 -> c2 otherwise
                    new_dependency = []
                    new_dependency.append(component1)
                    if component1 not in new_components:
                        new_components.append(component1)
                    if component1 not in design_dict:
                        design_dict[component1] = []
                    if 'base' not in design_dict[component1]:
                        design_dict[component1].append('base')

                    num_partitions2 = len(filtered_dict[component2])
                    if num_partitions2 > 1:
                        new_dependency.append(component2 + '_' + filtered_dict[component2][0])
                    else:
                        new_dependency.append(component2)
                        if component2 not in new_components:
                            new_components.append(component2)
                        if component2 not in design_dict:
                            design_dict[component2] = []
                        if 'base' not in design_dict[component2]:
                            design_dict[component2].append('base')
                    new_dependency.append(self.get_transition_probability(base_dependencies, component1, component2))  # use the original transition probability
                    new_dependencies.append(new_dependency)
                
                # Add new dependency due to the partitioned c2
                num_partitions2 = len(filtered_dict[component2])
                if not is_the_first_in_a_dependency(component2) and num_partitions2 > 1:
                    # Loop over the partitions

                    # At each iteration we add the following dependency c2_partitionX_idx -> c2_partitionX_idx+1
                    for idx in range(num_partitions2-1):
                        new_dependency = []
                        segm1 = filtered_dict[component2][idx]
                        new_dependency.append(component2 + '_' + segm1)
                        if component2 + '_' + segm1 not in new_components:
                            new_components.append(component2 + '_' + segm1)
                        if component2 not in design_dict:
                            design_dict[component2] = []
                        if segm1 not in design_dict[component2]:
                            design_dict[component2].append(segm1)
                        segm2 = filtered_dict[component2][idx+1]
                        new_dependency.append(component2 + '_' + segm2)
                        if idx == num_partitions2-2: 
                            if component2 + '_' + segm2 not in new_components:
                                new_components.append(component2 + '_' + segm2)
                            if component2 not in design_dict:
                                design_dict[component2] = []
                            if not segm2 in design_dict[component2]:
                                design_dict[component2].append(segm2)
                        # This part is needed in the case of early exits
                        # If it is not the last partition then, we must take as 
                        # transition probability the user-defined one 
                        
                        if component2 in ee_components and idx < num_partitions2-1:
                            new_dependency.append(self.get_ee_transition_probability(component2, idx))
                        else:
                            new_dependency.append(1) # NOTE: in the case they are normal partitions, we assume always 1 as transition probability
                        if new_dependency not in new_dependencies:
                            new_dependencies.append(new_dependency)
        
        new_dag_dict = {'System': {}}
        new_dag_dict['System']['name'] = self.dag_dict['System']['name']
        new_dag_dict['System']['components'] = new_components
        new_dag_dict['System']['dependencies'] = new_dependencies

        self.new_dag_dict = new_dag_dict
        self.design_dict = design_dict

        with open(os.path.join(self.deployment_dir, 'application_dag.yaml'), 'w') as f:
            yaml.dump(new_dag_dict, f, sort_keys=False)
    
    def create_deployment(self, deployment_name, dag_filename, partitions_dict, components_combination):
        ''' Create base deployment.

            Parameters:
                - deployment_name: name of the new deployment
                - dag: application dag of the current deployment 
        '''
        super().create_deployment(deployment_name, dag_filename)
    
        print("\n")
        print("[AI-SPRINT]: " + "Starting creating {} application deployment..".format(deployment_name))

        # Create DAG
        self.create_dag(partitions_dict, components_combination)

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
        for component_name in self.design_dict:
            designs = self.design_dict[component_name]
            for design in designs:
                source_design = os.path.join(designs_dir, component_name, design)
                symlink = os.path.join(
                    os.path.abspath(self.deployment_dir), 'src', component_name + '_' + design)
                os.symlink(source_design, symlink)

        # Create production deployment #
        # ---------------------------- #
        # Save production_deployment.yaml 

        # Initialize the symbolic link to the optimal deployment to point 
        # to the base deployment
        print("             " + "Done!")