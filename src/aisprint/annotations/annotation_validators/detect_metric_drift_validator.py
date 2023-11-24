from .annotation_validator import AnnotationValidator

class DetectMetricDriftValidator(AnnotationValidator):

    def _check_arguments(self, component_name, arguments):
        pass

    def _check_arguments_validity(self):
        for component_script, annotations in self.annotations.items():
            if 'detect_metric_drift' in annotations:
                arguments = annotations['detect_metric_drift']
                try:
                    self._check_arguments(annotations['component_name']['name'], arguments)
                except Exception as e:
                    print("\nAn error occurred while parsing 'detect_metric_drift' " + 
                          "annotation in the following component: \n{}.\n".format(component_script))
                    raise(e)

    def check_annotation_validity(self):
        super().check_annotation_validity()