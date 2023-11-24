import os
import yaml

import pkg_resources
import shutil
import zipfile

import numpy as np
import pandas as pd

from .annotation_manager import AnnotationManager


class DetectMetricDriftManager(AnnotationManager):

    ''' 'detect_metric_drift' annotation manager.

        Parameters:
            annotations_file (str): complete path to the parsed annotations' file.
        
        NOTE: the annotations are assumed to be already parsed by the QoSAnnotationsParser, which
        also check errors in the annotations' format.
    '''

    def process_annotations(self, args=None):
        ''' Get partitionable models and generate partition designs by running SPACE4AIDPartitioner.
        ''' 

        annotation_exists = False
        for _, component_arguments in self.annotations.items():
            if 'detect_metric_drift' in component_arguments:
                annotation_exists = True
        if not annotation_exists:
            return None

        # Generate Drift Detector component 
        # ---------------------------------

        print("\n")
        print("[AI-SPRINT]: " + "Creating drift detector component..")
        
        for _, component_arguments in self.annotations.items():
            if 'detect_metric_drift' in component_arguments:
                metrics = component_arguments['detect_metric_drift']['metric']
                if type(metrics) == str:
                    metrics = [metrics]
                fields = component_arguments['detect_metric_drift']['field']
                if type(fields) == str:
                    fields = [[fields]]
                statistical_tests = component_arguments['detect_metric_drift']['statistical_test']
                if type(statistical_tests) == str:
                    statistical_tests = [[statistical_tests]]
                test_thresholds = component_arguments['detect_metric_drift']['test_threshold']
                if type(test_thresholds) != list:
                    test_thresholds = [[test_thresholds]]
                monitoring_periods = component_arguments['detect_metric_drift']['monitoring_period']
                if type(monitoring_periods) != list:
                    monitoring_periods = [[monitoring_periods]]
                detection_interval = component_arguments['detect_metric_drift']['detection_interval']
                data_collection_period = component_arguments['detect_metric_drift']['data_collection_period']

                # Save dictionary
                metric_dict = {'metrics': {}}

                for metric_idx, metric in enumerate(metrics):
                    metric_dict['metrics'][metric] = {}
                    for field_idx, field in enumerate(fields[metric_idx]):
                        metric_dict['metrics'][metric][field] = {}
                        metric_dict['metrics'][metric][field]['statistical_test'] = statistical_tests[metric_idx][field_idx]
                        metric_dict['metrics'][metric][field]['test_threshold'] = test_thresholds[metric_idx][field_idx]
                        metric_dict['metrics'][metric][field]['monitoring_period'] = monitoring_periods[metric_idx][field_idx]
                metric_dict['detection_interval'] = detection_interval
                metric_dict['data_collection_period'] = data_collection_period

                if not os.path.exists(os.path.join(self.application_dir, 'common_config', 'drift_detector')):
                    os.makedirs(os.path.join(self.application_dir, 'common_config', 'drift_detector'))

                drift_detector_location = pkg_resources.resource_filename("aisprint", "drift_detector/drift_detector.zip")
                with zipfile.ZipFile(drift_detector_location, 'r') as zip_ref:
                    zip_ref.extractall(os.path.join(self.application_dir, 'common_config', 'drift_detector'))

                with open(os.path.join(self.application_dir, 'common_config', 'drift_detector', 'drift_detector_config.yaml'), 'w') as f:
                    yaml.dump(metric_dict, f)
                
                break

        print("\n")
        print("             " + "The Drift Detector component has been created and added to the components.\n")
        # ----------------