from .annotation_validator import AnnotationValidator

class ModelPerformanceValidator(AnnotationValidator):

    def _check_arguments(self, component_name, arguments):
        pass

    def _check_arguments_validity(self):
        for component_script, annotations in self.annotations.items():
            if 'model_performance' in annotations:
                arguments = annotations['model_performance']
                try:
                    self._check_arguments(annotations['component_name']['name'], arguments)
                except Exception as e:
                    print("\nAn error occurred while parsing 'model_performance' " + 
                          "annotation in the following component: \n{}.\n".format(component_script))
                    raise(e)

    def check_annotation_validity(self):
        super().check_annotation_validity()