import os
import yaml
from abc import ABC, abstractmethod

class AnnotationManager(ABC):

    def __init__(self, application_name, application_dir):
        
        self.application_name = application_name
        self.application_dir = application_dir
        self.designs_dir = os.path.join(application_dir, 'aisprint', 'designs')
        self.deployments_dir = os.path.join(application_dir, 'aisprint', 'deployments')
        with open(os.path.join(application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
            self.annotations = yaml.safe_load(f)

    @abstractmethod
    def process_annotations(self, args):
        pass