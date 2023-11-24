import json
from abc import ABC, abstractmethod

from aisprint.utils import parse_dag

class AnnotationValidator(ABC):

    def __init__(self, annotations, dag_file) -> None:
        super().__init__()
        self.annotations = annotations 
        self.dag, _ = parse_dag(dag_file)
    
    @abstractmethod
    def _check_arguments_validity(self):
        pass

    @abstractmethod
    def check_annotation_validity(self):
        self._check_arguments_validity()