from .annotation_validator import AnnotationValidator

class SecurityValidator(AnnotationValidator):

    def _check_arguments_validity(self):
        # TODO
        pass

    def check_annotation_validity(self):
        super().check_annotation_validity()
