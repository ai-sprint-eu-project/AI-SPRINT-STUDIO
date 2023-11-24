import os
import yaml
from abc import ABC, abstractmethod

class DeploymentGenerator(ABC):

    def __init__(self, application_dir):
        self.application_dir = application_dir

    @abstractmethod
    def create_deployment(self, deployment_name, dag_filename):
        ''' Create a deployment.

            Parameters:
                - deployment_name: name of the new deployment
                - dag: application dag of the current deployment 
        '''
        deployment_dir = os.path.join(
            self.application_dir, 'aisprint', 'deployments', deployment_name)
        if not os.path.exists(deployment_dir):
            os.makedirs(deployment_dir)
        self.deployment_dir = deployment_dir

        with open(dag_filename, 'r') as f:
            self.dag_dict = yaml.safe_load(f)