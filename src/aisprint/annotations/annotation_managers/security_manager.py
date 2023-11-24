import yaml

from .annotation_manager import AnnotationManager


class SecurityManager(AnnotationManager):

    ''' 'security' annotation manager.

        Parameters:
            annotations_file (str): complete path to the parsed annotations' file.
        
        NOTE: the annotations are assumed to be already parsed by the QoSAnnotationsParser, which
        also check errors in the annotations' format.
    '''

    def process_annotations(self, args):
        # TODO
        pass