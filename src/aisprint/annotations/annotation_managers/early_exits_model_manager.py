import os
import yaml

from .annotation_manager import AnnotationManager
from aisprint.space4aidpartitioner import EESPACE4AIDPartitioner
from aisprint.space4aidpartitioner import EECodePartitioner


class EarlyExitsModelManager(AnnotationManager):

    ''' 'early_exit_model' annotation manager.

        Parameters:
            annotations_file (str): complete path to the parsed annotations' file.
        
        NOTE: the annotations are assumed to be already parsed by the QoSAnnotationsParser, which
        also check errors in the annotations' format.
    '''

    def process_annotations(self, args=None):
        ''' Get partitionable models and generate partition designs by running SPACE4AIDPartitioner.
        ''' 

        # SPACE4AI-D-partitioner
        # ----------------------
        print("\n")
        print("[AI-SPRINT]: " + "Running SPACE4AI-D-partitioner (early exits)..")
        annotation_exists = False
        for _, component_arguments in self.annotations.items():
            if 'early_exits_model' in component_arguments:
                annotation_exists = True
                onnx_file = component_arguments['early_exits_model']['onnx_file'] 
                component_name = component_arguments['component_name']['name']

                partitioner = EESPACE4AIDPartitioner(
                    self.application_dir, component_name, onnx_file)
                found_partitions = partitioner.get_partitions()

                found_partitions = ['base'] + found_partitions

                component_partitions_file = os.path.join(self.designs_dir, 'component_partitions.yaml')
                if not os.path.exists(component_partitions_file):
                    component_partitions = {'components': {
                        component_name: {'partitions': found_partitions}}}
                else:
                    with open(component_partitions_file, 'r') as f:
                        component_partitions = yaml.safe_load(f)
                        component_partitions['components'][component_name] = {
                            'partitions': found_partitions}
                with open(component_partitions_file, 'w') as f:
                    yaml.dump(component_partitions, f)
        # ----------------------

        if annotation_exists:
            # Code partitioner
            # ----------------
            print("\n")
            print("[AI-SPRINT]: " + "Automatic generating the code of the found partitions..")
            code_partitioner = EECodePartitioner(application_dir=self.application_dir)
            code_partitioner.generate_code_partitions()
            # ----------------
        else:
            print("\n")
            print("[AI-SPRINT]: " + "Done. No early_exits_model defined.")