import os
import shutil
import yaml

from .deployment_generator import DeploymentGenerator


class AlternativeDeploymentGenerator(DeploymentGenerator): 

    def __init__(self, application_dir):
        
        self.application_dir = application_dir
    
    def create_dag(self, deployment_name, deployment):
        
        new_dag_dict = {'System': {}}
        new_dag_dict['System']['name'] = deployment_name
        new_dag_dict['System']['components'] = list(deployment['components'])
        new_dag_dict['System']['dependencies'] = list(deployment['dependencies'])

        self.new_dag_dict = new_dag_dict

        with open(os.path.join(self.deployment_dir, 'application_dag.yaml'), 'w') as f:
            yaml.dump(new_dag_dict, f, sort_keys=False)

    
    def create_deployment(self, deployment_name, dag_filename, deployment): 
        ''' Create base deployment.

            Parameters:
                - deployment_name: name of the new deployment
                - dag: application dag of the current deployment 
        '''
        super().create_deployment(deployment_name, dag_filename)
    
        print("\n")
        print("[AI-SPRINT]: " + "Starting creating {} application deployment..".format(deployment_name))

        # Create DAG
        self.create_dag(deployment_name, deployment)

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
        for component_name in self.new_dag_dict['System']['components']:
            source_design = os.path.join(designs_dir, component_name, 'base')
            symlink = os.path.join(
                os.path.abspath(self.deployment_dir), 'src', component_name)
            os.symlink(source_design, symlink)

        # Create production deployment #
        # ---------------------------- #
        # Save production_deployment.yaml 

        # Initialize the symbolic link to the optimal deployment to point 
        # to the base deployment
        print("             " + "Done!")