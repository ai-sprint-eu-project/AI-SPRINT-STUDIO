import os
import yaml

import itertools
import numpy as np
import pandas as pd

from .annotation_manager import AnnotationManager


class ModelPerformanceManager(AnnotationManager):

    ''' 'model_performance' annotation manager.

        Parameters:
            annotations_file (str): complete path to the parsed annotations' file.
        
        NOTE: the annotations are assumed to be already parsed by the QoSAnnotationsParser, which
        also check errors in the annotations' format.
    '''

    def get_alternative_of(self, parent, childs):
        for child in childs:
            if child in self.alternative_components[parent]:
                return child 
            if child == parent:
                return child
        return None 

    def get_alternative_deployments(self):
        
        #  Need to use DAG 
        dag_file = os.path.join(self.application_dir, 'common_config', 'application_dag.yaml')
        
        with open(dag_file, 'r') as f:
            dag_dict = yaml.safe_load(f)
        
        alternative_components = dag_dict['System']['alternative_components']
        self.alternative_components = alternative_components

        alternatives = []
        for c in alternative_components:
            alternatives.append([c] + alternative_components[c])
        alternatives_temp = list(itertools.product(*alternatives))
        alternatives = [alternative for alternative in alternatives_temp if not set(
            dag_dict['System']['components']) == set(alternative)]

        num_alternatives = len(alternatives)
        
        deployments = {}
        deployments['base'] = {}
        deployments['base']['components'] = dag_dict['System']['components']
        deployments['base']['dependencies'] = dag_dict['System']['dependencies']

        for idx in range(num_alternatives):
            deployment_name = 'deployment{}'.format(idx+1)
            deployments[deployment_name] = {}
            deployments[deployment_name]['components'] = alternatives[idx]
            dependencies = dag_dict['System']['dependencies'][0]
            start_c = dependencies[0]
            end_c = dependencies[1]
            prob = dependencies[2]
            
            deployments[deployment_name]['dependencies'] = [[
                self.get_alternative_of(start_c, alternatives[idx]),
                self.get_alternative_of(end_c, alternatives[idx]),
                prob]]

        return deployments
    
    def compute_f1(self, precisions, recalls, class_weights=None):
        
        num_classes = len(list(precisions.keys()))
        
        f1s = {}
        average_f1 = 0
        for c, precision in precisions.items(): 
            recall = recalls[c]

            f1s[c] = 2 * precision * recall / (precision + recall)

            if class_weights is not None:
                average_f1 += (class_weights[c] * f1s[c]) 
            else:
                average_f1 += (f1s[c] / num_classes) 

        return f1s, average_f1

                   
    def compute_precision(self, filter_rates, classifier_cm, filter, classifier, 
                          p_filtered_class, p_classifier_filtered_class, class_weights):
        
        TPf = filter_rates['TP']
        FPf = filter_rates['FP']
        FNf = filter_rates['FN']
        TNf = filter_rates['TN']

        classifier_classes = list(classifier_cm.keys())
        num_classes = len([p_filtered_class] + classifier_classes)
        
        precisions = {}
        average_precision = 0
        for c in [p_filtered_class] + classifier_classes: 
            if p_classifier_filtered_class is None:
                # The classifier does not predict the filtered-out class
                if c == p_filtered_class: # filtered class
                    precisions[c] = TNf / (TNf + FNf)
                else:
                    TP = classifier_cm[c][c] 
                    FP = 0 
                    for c2, v in classifier_cm.items():
                        if c2 != c:
                            FP += v[c]
                    
                    total_sum = 0
                    for c2, v in classifier_cm.items():
                        for c3, v2 in classifier_cm[c2].items():
                            total_sum += v2
                    precisions[c] = (TPf * TP) / (
                        (TPf * TP) + (TPf * FP) + (FPf * (TP + FP) / total_sum))
            else:
                # The classifier predicts the filtered-out class (the same of the filter)
                TP = classifier_cm[c][c] 
                FP = 0 
                for c2, v in classifier_cm.items():
                    if c2 != c:
                        FP += v[c]
                        
                if c == p_filtered_class: # filtered class
                    precisions[c] = (TNf + FPf * TP) / (
                        TNf + (FPf * TP) + FNf + (TPf * FP))
                else:
                    # FP due to the filtered class
                    FPfclass = classifier_cm[p_classifier_filtered_class][c]
                    # FP without the contribution of the filtered class
                    FPnof = FP - FPfclass 
                    precisions[c] = (TPf * TP) / (
                        (TPf * TP) + (TPf * FPnof) + (FPf * FPfclass))
            
            if class_weights is not None:
                average_precision += (class_weights[c] * precisions[c]) 
            else:
                average_precision += (precisions[c] / num_classes) 

        return precisions, average_precision
            
    def compute_recall(self, filter_rates, classifier_cm, filter, classifier, 
                       p_filtered_class, p_classifier_filtered_class, class_weights):
        TPf = filter_rates['TP']
        FPf = filter_rates['FP']
        FNf = filter_rates['FN']
        TNf = filter_rates['TN']

        classifier_classes = list(classifier_cm.keys())
        num_classes = len([p_filtered_class] + classifier_classes)
        
        recalls = {}
        average_recall = 0
        for c in [p_filtered_class] + classifier_classes: 
            if p_classifier_filtered_class is None:
                # The classifier does not predict the filtered-out class
                        
                if c == p_filtered_class: # filtered class
                    recalls[c] = TNf / (TNf + FPf)
                else:
                    TP = classifier_cm[c][c] 
                    FN = 0 
                    for c2, v in classifier_cm[c].items():
                        if c2 != c:
                            FN += v
                    
                    total_sum = 0
                    for c2, v in classifier_cm.items():
                        for c3, v2 in classifier_cm[c2].items():
                            total_sum += v2
                    recalls[c] = (TPf * TP) / (
                        (TPf * TP) + (TPf * FN) + (FNf * (TP + FN) / total_sum))
            else:
                # The classifier predicts the filtered-out class (the same of the filter)
                TP = classifier_cm[c][c] 
                FN = 0 
                for c2, v in classifier_cm[c].items():
                    if c2 != c:
                        FN += v 
                
                total_sum = 0
                for c2, v in classifier_cm.items():
                    for c3, v2 in classifier_cm[c2].items():
                        total_sum += v2
                        
                if c == p_filtered_class: # filtered class
                    recalls[c] = (TNf + FPf * TP) / (
                        TNf + (FPf * TP) + (FPf * FN))
                else:
                    recalls[c] = (TPf * TP) / (
                        (TPf * TP) + (TPf * FN) + (FNf * (TP + FN) / total_sum))

            if class_weights is not None:
                average_recall += (class_weights[c] * recalls[c]) 
            else:
                average_recall += (recalls[c] / num_classes) 
                
        return recalls, average_recall 

    def compute_accuracy(self, filter_rates, classifier_cm, filter, classifier, 
                         p_filtered_class, p_classifier_filtered_class, class_weights):
        TPf = filter_rates['TP']
        FPf = filter_rates['FP']
        FNf = filter_rates['FN']
        TNf = filter_rates['TN']
        
        classifier_classes = list(classifier_cm.keys())
        num_classes = len([p_filtered_class] + classifier_classes)
        
        accuracies = {}
        classifier_classes = list(classifier_cm.keys())
        for c in [p_filtered_class] + classifier_classes: 
            if p_classifier_filtered_class is None:
                # The classifier does not predict the filtered-out class
                if c == p_filtered_class: # filtered class
                    accuracies[c] = TNf
                else:
                    TP = classifier_cm[c][c] 
                    FN = 0 
                    for c2, v in classifier_cm[c].items():
                        if c2 != c:
                            FN += v
                    
                    accuracies[c] = TPf * TP

            else:
                # The classifier predicts the filtered-out class (the same of the filter)
                TP = classifier_cm[c][c] 
                FN = 0 
                for c2, v in classifier_cm[c].items():
                    if c2 != c:
                        FN += v

                if c == p_filtered_class: # filtered class
                    accuracies[c] = TNf + (FPf * TP)
                else:
                    accuracies[c] = TPf * TP
            
            if class_weights is not None:
                average_accuracy += (class_weights[c] * accuracies[c]) 
            else:
                average_accuracy += (accuracies[c] / num_classes) 

        return accuracies, average_accuracy
    
    def compute_metric(self, components, filter_rates, ref_classifier_cm, original_filter, 
                       original_classifier, p_metric, p_filtered_class, p_classifier_filtered_class):
        # Compute metric
        # --------------
        # Get filter component
        filter = self.get_alternative_of(original_filter, components)
        # Get classifier component
        classifier = self.get_alternative_of(original_classifier, components)

        # Read weights
        weights_file = os.path.join(self.application_dir, 'src', 'class_weights.csv')
        if os.path.exists(weights_file):
            class_weights = pd.read_csv(weights_file)
        else:
            class_weights = None

        if p_metric == 'average_f1':
            precisions, _ = self.compute_precision(
                filter_rates, ref_classifier_cm, filter, classifier, 
                p_filtered_class, p_classifier_filtered_class, class_weights)
            recalls, _ = self.compute_recall(
                filter_rates, ref_classifier_cm, filter, classifier, 
                p_filtered_class, p_classifier_filtered_class, class_weights)
            f1s, average_f1 = self.compute_f1(precisions, recalls, class_weights)
            return average_f1
        elif p_metric == 'average_precision':
            precisions, average_precision = self.compute_precision(
                filter_rates, ref_classifier_cm, filter, classifier, 
                p_filtered_class, p_classifier_filtered_class, class_weights)
            return average_precision
        elif p_metric == 'average_recall':
            recalls, average_recall = self.compute_recall(
                filter_rates, ref_classifier_cm, filter, classifier, 
                p_filtered_class, p_classifier_filtered_class, class_weights)
            return average_recall
        elif p_metric == 'accuracy':
            accuracy = self.compute_accuracy(
                filter_rates, ref_classifier_cm, filter, classifier, 
                p_filtered_class, p_classifier_filtered_class, class_weights)   
            return accuracy
    
    def get_filter_rates(self, components, original_filter, filtered_class):
        # Get filter component
        filter = self.get_alternative_of(original_filter, components) 
        # Read CM
        cm = np.load(os.path.join(
            self.application_dir, 'src', filter, 'classification_performance', 'confusion_matrix.npy'))
        # Read class names dictionary
        class_names = pd.read_csv(os.path.join(
            self.application_dir, 'src', filter, 'classification_performance', 'class_names_dictionary.csv'))
        # Compute rates
        filter_rates = {}
        for cname in class_names['class']:
            index = class_names['index'][class_names['class'] == cname].iloc[0]
            if cname == filtered_class:
                filter_rates['TN'] = cm[index, index]
                filter_rates['FN'] = cm[1-index, index]
            else:
                filter_rates['TP'] = cm[index, index]
                filter_rates['FP'] = cm[1-index, index]
        return filter_rates
    
    def refactor_classifier_cm(self, components, original_classifier):
        # Get classifier component
        classifier = self.get_alternative_of(original_classifier, components) 
        # Read CM
        cm = np.load(os.path.join(
            self.application_dir, 'src', classifier, 'classification_performance', 'confusion_matrix.npy'))
        # Read class names dictionary
        class_names = pd.read_csv(os.path.join(
            self.application_dir, 'src', classifier, 'classification_performance', 'class_names_dictionary.csv'))
        # Compute confusion matrix in the form of dictionary (with class names) 
        ref_cm = {}
        for cname in class_names['class']:
            index = class_names['index'][class_names['class'] == cname].iloc[0]
            ref_cm[cname] = {}
            for cname2 in class_names['class']:
                index2 = class_names['index'][class_names['class'] == cname2].iloc[0]
                ref_cm[cname][cname2] = cm[index, index2]
        return ref_cm 
        
    def process_annotations(self, args=None):
        ''' Get partitionable models and generate partition designs by running SPACE4AIDPartitioner.
        ''' 

        annotation_exists = False
        for _, component_arguments in self.annotations.items():
            if 'model_performance' in component_arguments:
                annotation_exists = True
        if not annotation_exists:
            return None

        # Generate alternative deployments and their performance 
        # ------------------------------------------------------

        # Get alternative deployments
        alternative_deployments = self.get_alternative_deployments()

        print("\n")
        print("[AI-SPRINT]: " + "Computing metrics for alternative deployments..")
        p_metric = None
        p_metric_thr = None
        p_filtered_class = None
        p_classifier_filtered_class = None
        original_filter = None
        original_classifier = None
        for _, component_arguments in self.annotations.items():
            if 'model_performance' in component_arguments:
                metric = None
                metric_thr = None
                filtered_class = None
                if 'metric' in component_arguments['model_performance'].keys():
                    metric = component_arguments['model_performance']['metric'] 
                if 'metric_thr' in component_arguments['model_performance'].keys():
                    metric_thr = component_arguments['model_performance']['metric_thr']
                if 'filtered_class' in component_arguments['model_performance'].keys():
                    filtered_class = component_arguments['model_performance']['filtered_class']

                component_name = component_arguments['component_name']['name']                   
                if metric is not None:
                    p_metric = metric
                    original_classifier = component_name
                    if filtered_class is not None:
                        p_classifier_filtered_class = filtered_class
                    if metric_thr is not None:
                        p_metric_thr = metric_thr 
                else:
                    original_filter = component_name
                    if filtered_class is not None:
                        p_filtered_class = filtered_class 
        # ----------------------
        
        # Compute metrics
        # ---------------

        deployments_metric = {}
        for d, v in alternative_deployments.items():
            # Get CM with class names 
            ref_classifier_cm = self.refactor_classifier_cm(v['components'], original_classifier)
            # Get filter TP, FP, FN, TN
            filter_rates = self.get_filter_rates(v['components'], original_filter, p_filtered_class)

            # Compute the value of the metric chosen by the user
            metric_value = self.compute_metric(
                v['components'], filter_rates, ref_classifier_cm, original_filter, original_classifier, 
                p_metric, p_filtered_class, p_classifier_filtered_class)
            
            deployments_metric[d] = metric_value
        
        # Save result in space4ai-r
        deployments_performance = {}
        deployments_performance['System'] = {}
        deployments_performance['System']['metric_name'] = p_metric
        deployments_performance['System']['metric_thr'] = p_metric_thr

        sorted_names = []
        temp_dict = {}
        for d, v in alternative_deployments.items():
            temp_dict[d] = {}
            temp_dict[d]['components'] = list(v['components'])
            # substitute with the correct probability of the alternative
            # transition probability = TP + FP (of the filter)
            # Get filter TP, FP, FN, TN
            filter_rates = self.get_filter_rates(v['components'], original_filter, p_filtered_class)
            temp_dict[d]['dependencies'] = [
                [v['dependencies'][0][0], v['dependencies'][0][1], np.round(filter_rates['TP'] + filter_rates['FP'], 4).item()]]
            temp_dict[d]['metric_value'] = np.round(deployments_metric[d], 4).item()
            sorted_names.append({'name': d, 'metric_value': deployments_metric[d]})

        sorted_names = sorted(sorted_names, key=lambda d: d['metric_value'], reverse=True)
        deployments_performance['System']['sorted_deployments_performance'] = []
        idx = 1
        for name_dict in sorted_names:
            if name_dict['name'] == 'base':
                new_d = 'original_deployment'
            else:
                new_d = 'alternative_deployment{}'.format(idx)
                idx += 1
            deployments_performance['System']['sorted_deployments_performance'].append(
                {new_d: temp_dict[name_dict['name']]})
        
        # Save the final YAML file 
        p_file = os.path.join(self.application_dir, 'space4ai-r', 'deployments_performance.yaml')
        with open(p_file, 'w') as f:
            yaml.dump(deployments_performance, f, default_flow_style=False)

        print("\n")
        print("             " + "Done! Alternative deployments performance generated.\n")
        # ----------------
        return alternative_deployments