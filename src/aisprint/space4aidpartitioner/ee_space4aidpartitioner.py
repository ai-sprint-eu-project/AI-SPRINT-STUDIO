import os
import shutil

from tqdm import tqdm

import onnx
from skl2onnx.helpers.onnx_helper import load_onnx_model

import pandas as pd


class EESPACE4AIDPartitioner():
    ''' Partitioner that, given an early-exits model,
        generates the model partitions from the ONNX file. 

        Params:
        - application_dir: directory of the AI-SPRINT application
        - partitionable_model: name of the model with early-exits nodes
        - onnx_file: ONNX model of the considered component
        - early_exits_nodes: dictionary for the early exits
    '''

    def __init__(self, application_dir, partitionable_model, onnx_file):

        self.application_dir = application_dir
        self.partitionable_model = partitionable_model
        self.partitionable_model_dir = os.path.join(
            self.application_dir, 'aisprint', 'designs', partitionable_model, 'base')
        self.onnx_file = os.path.join(self.partitionable_model_dir, 'onnx', onnx_file)
        # Read early exits dataframe with the nodes names
        self.ee_df = pd.read_csv(os.path.join(self.partitionable_model_dir, 'onnx', 'early_exits.csv'))
    
    def get_partitions(self):
        # Load the Onnx Model
        print("- Getting early-exit partitions of model: {}".format(self.partitionable_model))
        onnx_model = load_onnx_model(self.onnx_file)

        return self.split_by_early_exits(onnx_model=onnx_model)

    def _get_true_input(self, onnx_model):
        '''
        Get the list of TRUE inputs of the ONNX model passed as argument.
        The reason for this is that sometimes "onnx.load" interprets some of the static initializers
        (such as weights and biases) as inputs, therefore showing a large list of inputs and misleading for instance
        the fuctions used for splitting.
        :param onnx_model: the already imported ONNX Model
        :returns: a list of the true inputs
        '''
        input_names = []

        initializers = [node.name for node in onnx_model.graph.initializer]

        # Iterate all inputs and check if they are valid
        for i in range(len(onnx_model.graph.input)):
            node_name = onnx_model.graph.input[i].name
            # Check if input is not an initializer, if so ignore it
            if node_name in initializers:
                continue
            else:
                input_names.append(node_name)

        return input_names
    
    def filter_nodes(self, node_names):
        filtered_node_names = []
        for node_name in node_names.split(','):
            node_name = node_name.replace(" ", "").replace("\t", "")
            if '\'' in node_name:
                node_name = node_name.split('\'')[1]
            elif '\"' in node_name:
                node_name = node_name.split('\"')[1]
            filtered_node_names.append(node_name) 
        return filtered_node_names
        

    def split_by_early_exits(self, onnx_model=None):
        ''' Get all the partitions defined by the early exits, 
            which are stored as designs in the designs folder of the AI-SPRINT application.
        '''

        designs_folder = os.path.join(
            self.application_dir, 'aisprint', 'designs', self.partitionable_model)
        
        if onnx_model is None:
            # Load the Onnx Model
            onnx_model = load_onnx_model(self.onnx_file)

        found_partitions = []

        #Make a split for every layer in the model
        ln = 0
        # for layer in enumerate_model_node_outputs(onnx_model):
        ee_output_nodes = []
        partitioned_layers = []

        print("- The following early exits path have been found: ")
        for ee_idx in range(len(self.ee_df)):
            print('- ', str(ee_idx+1)+":", "exit: {}, input nodes: {}, output nodes: {}".format(
                self.ee_df.iloc[ee_idx].exits, self.ee_df.iloc[ee_idx].input_nodes, self.ee_df.iloc[ee_idx].output_nodes))
        
        for ee_idx in tqdm(range(len(self.ee_df))):
            # Initialize partitions designs folders
            which_partition = 'partition{}'.format(ln+1)
            partition_dir = os.path.join(designs_folder, which_partition+'_{}'.format(ee_idx+1))
            if not os.path.exists(partition_dir):
                os.makedirs(partition_dir)
            
            onnx_folder = os.path.join(partition_dir, 'onnx')
            if not os.path.exists(onnx_folder):
                os.makedirs(onnx_folder)

            if ee_idx == 0:
                filtered_input_names = self._get_true_input(onnx_model)
            else:
                input_names = self.ee_df.iloc[ee_idx-1].input_nodes.split('[')[1].split(']')[0]
                filtered_input_names = self.filter_nodes(input_names)
           
            # if ee_idx < (len(self.ee_df) - 1): 
            output_nodes = self.ee_df.iloc[ee_idx].output_nodes.split('[')[1].split(']')[0]
            filtered_output_nodes = self.filter_nodes(output_nodes)
                    
            ee_output_nodes = ee_output_nodes + filtered_output_nodes

            input_names = self.ee_df.iloc[ee_idx].input_nodes.split('[')[1].split(']')[0]
            filtered_input_nodes = self.filter_nodes(input_names) 

            output_names = filtered_input_nodes + filtered_output_nodes 

            try:
                onnx.utils.extract_model(
                    self.onnx_file,
                    os.path.join(onnx_folder, which_partition+'_{}.onnx'.format(ee_idx+1)),
                    filtered_input_names, output_names) 
            except Exception as e:
                found_partitions = []
                shutil.rmtree(partition_dir)
                break
            found_partitions.append(which_partition+'_{}'.format(ee_idx+1))

            output_nodes = self.ee_df.iloc[ee_idx].output_nodes.split('[')[1].split(']')[0]
            filtered_output_nodes = self.filter_nodes(output_nodes)
            
            exit_nodes = {'exit_node': filtered_output_nodes}
            df = pd.DataFrame(exit_nodes)
            df.to_pickle(os.path.join(onnx_folder, 'exit_node.df'))

            if ee_idx == (len(self.ee_df)-1):
                # Initialize partitions designs folders
                which_partition = 'partition{}'.format(ln+1)
                last_partition_dir = os.path.join(designs_folder, which_partition+'_{}'.format(ee_idx+2))
                if not os.path.exists(last_partition_dir):
                    os.makedirs(last_partition_dir)
                
                onnx_folder = os.path.join(last_partition_dir, 'onnx')
                if not os.path.exists(onnx_folder):
                    os.makedirs(onnx_folder)

                input_names = self.ee_df.iloc[ee_idx].input_nodes.split('[')[1].split(']')[0]
                filtered_input_names = self.filter_nodes(input_names)
                
                # Get final output
                last_output_names = []
                for i in range(len(onnx_model.graph.output)):
                    if onnx_model.graph.output[i].name not in ee_output_nodes:
                        last_output_names.append(onnx_model.graph.output[i].name)
                
                try:
                    onnx.utils.extract_model(
                        self.onnx_file,
                        os.path.join(onnx_folder, which_partition+'_{}.onnx'.format(ee_idx+2)),
                        filtered_input_names, last_output_names) 
                except Exception as e:
                    found_partitions = []
                    shutil.rmtree(partition_dir)
                    shutil.rmtree(last_partition_dir)
                    break
                found_partitions.append(which_partition+'_{}'.format(ee_idx+2))

            # Found first smallest partition, then break
            ln = ln + 1

            input_names = self.ee_df.iloc[ee_idx].input_nodes.split('[')[1].split(']')[0]
            filtered_input_nodes = self.filter_nodes(input_names)
            
            partitioned_layers = partitioned_layers + filtered_input_nodes 

        print("Model partitioned at layers: {}\n".format(partitioned_layers))
        return found_partitions
        # ------------------------------------------------------
        
        # ln = ln + 1