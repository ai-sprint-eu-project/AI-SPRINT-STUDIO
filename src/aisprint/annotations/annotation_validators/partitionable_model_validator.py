import numpy as np

from .annotation_validator import AnnotationValidator

class PartitionableModelValidator(AnnotationValidator):

    def _check_arguments(self, component_name, arguments):
        # No 'onnx_file' argument (arguments is empty)
        if 'onnx_file' not in arguments:
            raise RuntimeError("'onnx_file' argument required in 'partitionable_model' annotation. ")
        # Check number of arguments
        num_arguments = len(list(arguments.keys()))
        if len(list(arguments.keys())) > 2:
            raise RuntimeError("Annotation 'partitionable_model' takes maximum 2 arguments ({}).".format(num_arguments))
        # Check 'onnx_file' is a string
        if not isinstance(arguments['onnx_file'], str):
            raise TypeError("'onnx_file' argument must be a string.")

    def _check_arguments_validity(self):
        for component_script, annotations in self.annotations.items():
            if 'partitionable_model' in annotations:
                arguments = annotations['partitionable_model']
                try:
                    self._check_arguments(annotations['component_name']['name'], arguments)
                except Exception as e:
                    print("\nAn error occurred while parsing 'partitionable_model' " + 
                          "annotation in the following component: \n{}.\n".format(component_script))
                    raise(e)
    
    def _check_no_early_exit_model(self):
        for component_script, annotations in self.annotations.items():
            partitionable_models = []
            early_exits_models = []
            if 'partitionable_model' in annotations:
                partitionable_models.append(annotations['component_name']['name'])
            if 'early_exits_model' in annotations:
                early_exits_models.append(annotations['component_name']['name'])
        
        inter = np.intersect1d(partitionable_models, early_exits_models)
        if len(inter) > 0:
            raise Exception("Using 'early_exit_model' and 'partitionable_model' together is not allowed. " + 
                            "Please check components: {}\n".format(inter))

    def check_annotation_validity(self):
        super().check_annotation_validity()

        self._check_no_early_exit_model()