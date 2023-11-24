import numpy as np

from .annotation_validator import AnnotationValidator


class EarlyExitsModelValidator(AnnotationValidator):

    def _check_arguments(self, component_name, arguments):
        pass

    def _check_arguments_validity(self):
        for component_script, annotations in self.annotations.items():
            if 'early_exits_model' in annotations:
                arguments = annotations['early_exits_model']
                try:
                    self._check_arguments(annotations['component_name']['name'], arguments)
                except Exception as e:
                    print("\nAn error occurred while parsing 'early_exits_model' " + 
                          "annotation in the following component: \n{}.\n".format(component_script))
                    raise(e)


    def _check_no_partitionable_model(self):
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

        self._check_no_partitionable_model()
