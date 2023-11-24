import os
import yaml

from .annotation_manager import AnnotationManager
from aisprint.space4aidpartitioner import SPACE4AIDPartitioner
from aisprint.space4aidpartitioner import CodePartitioner


class PartitionableModelManager(AnnotationManager):

    ''' 'partitionable_model' annotation manager.

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
        print("[AI-SPRINT]: " + "Running SPACE4AI-D-partitioner..")
        annotation_exists = False
        for _, component_arguments in self.annotations.items():
            if 'partitionable_model' in component_arguments:
                annotation_exists = True
                onnx_file = component_arguments['partitionable_model']['onnx_file'] 
                component_name = component_arguments['component_name']['name']

                try:
                    num_partitions = component_arguments['partitionable_model']['num_partitions']
                except:
                    num_partitions = 1

                partitioner = SPACE4AIDPartitioner(
                    self.application_dir, component_name, onnx_file)
                found_partitions = partitioner.get_partitions(num_partitions=num_partitions)

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
            code_partitioner = CodePartitioner(application_dir=self.application_dir)
            code_partitioner.generate_code_partitions()
            # ----------------
        else:
            print("\n")
            print("[AI-SPRINT]: " + "Done. No partitionable_model defined.")