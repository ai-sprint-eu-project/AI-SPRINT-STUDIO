import os
import yaml
import shutil

from multiprocessing import Process

import numpy as np

import re


class CodePartitioner():
    ''' Temporary partitioner that, given a partitionable model:
        - Generate the model partitions from the ONNX file. In particular,
            takes the partition with the lowest tensor size.
        - Generate the Python code to execute the partitions
    '''

    def __init__(self, application_dir):

        self.application_dir = application_dir
        self.designs_dir = os.path.join(
            self.application_dir, 'aisprint', 'designs')
        self.partitionable_components = self.get_partitionable_components()
    
    def get_partitionable_components(self):
        components = []
        with open(os.path.join(self.application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
            annotations = yaml.load(f, yaml.FullLoader)    
        for _, item in annotations.items():
            if 'partitionable_model' in item:
                components.append(item['component_name']['name'])
        return components
    
    def generate_code_partitions(self):
        
        # Get list of partitions
        component_dirs = next(os.walk(self.designs_dir))[1]

        for component_dir in component_dirs:
            component_name = os.path.normpath(component_dir)

            if component_name not in self.partitionable_components:
                continue
            
            # Get list of partitions
            partition_dirs = next(os.walk(
                os.path.join(self.designs_dir, component_dir)))[1]
            
            partition_dirs = [p for p in partition_dirs if 'partition' in p]

            if partition_dirs == []:
                continue
            
            print("\n")
            print("             " + "- Generating code for the component: {}".format(component_name))
        
            # Check component has exec_time
            with open(os.path.join(self.application_dir, 'common_config', 'annotations.yaml'), 'r') as f:
                annotations = yaml.load(f, yaml.FullLoader)

            has_exec_time = False
            for _, item in annotations.items():
                if item['component_name']['name'] == component_name:
                    if 'exec_time' in item:
                        has_exec_time = True
                    orig_onnx_file = item['partitionable_model']['onnx_file']
            
            # 1st half
            first_half = [p for p in partition_dirs if re.search("^partition[1-9]+_1", p)]
            self._generate_first_half_code(
                component_name=component_name, first_half=first_half, 
                has_exec_time=has_exec_time, orig_onnx_file=orig_onnx_file)
            
            # 2nd half
            second_half = [p for p in partition_dirs if re.search("^partition[1-9]+_2", p)]
            self._generate_second_half_code(
                component_name=component_name, second_half=second_half, has_exec_time=has_exec_time)

            # Copy all the other files, except onnx nad main.py 
            for h in first_half+second_half:
                base_dir = os.path.join(self.designs_dir, component_name, 'base')
                # Copy dirs
                for dir in next(os.walk(base_dir))[1]:
                    if dir != 'onnx':
                        shutil.copytree(
                            os.path.join(base_dir, dir), 
                            os.path.join(self.designs_dir, component_name, h, dir))
                # Copy files
                for file in next(os.walk(base_dir))[2]:
                    if file != 'main.py':
                        shutil.copyfile(
                            os.path.join(base_dir, file), 
                            os.path.join(self.designs_dir, component_name, h, file))
            print("             " + "  Done! Code generated for segments:", first_half + second_half)
        
    def _generate_first_half_code(self, component_name, first_half, 
                                  has_exec_time, orig_onnx_file):

        base_design = os.path.join(self.designs_dir, component_name, 'base')
        # Get main script
        with open(os.path.join(base_design, 'main.py'), 'r') as f:
            main_code = f.readlines()
        
        inference_row = [l for l in main_code if ('load_and_inference' in l and 'import' not in l)]
        if len(inference_row) > 1:
            raise Exception(
                "Multiple ONNX load_and_inference calls found in {} script. Only one is allowed.".format(
                    os.path.join(base_design, 'main.py')))
        elif len(inference_row) == 0:
            raise Exception(
                "ONNX load_and_inference call required in {} script.".format(
                    os.path.join(base_design, 'main.py')))
        
        inference_line = np.where(np.array(main_code) == inference_row[0])[0][0]

        inference_str = main_code[inference_line]
        inference_str_res, inference_cmd = inference_str.split("=")

        # Compute number of spaces at the beginning
        spaces_str = ""
        for i in range(len(inference_str_res)):
            if inference_str_res[i] not in [" ", "\t"]:
                break
            if inference_str_res[i]  == " ":
                spaces_str += " "
            elif inference_str_res[i] == "\t":
                spaces_str += "\t"
        dict_res, out_res = inference_str_res.replace(" ", "").replace("\t", "").split(',')
        new_inference_str = inference_str 
        
        # Get __name__ line
        name_row = [l for l in main_code if ("__name__=='__main__'" in l.replace(" ", "") and 'import' not in l)]
        name_line = np.where(np.array(main_code) == name_row[0])[0][0]

        # Generate save string
        save_str = ""
        save_str += spaces_str
        save_str += "with open(args['output'], 'wb') as f:\n"
        save_str += spaces_str
        if "\t" in spaces_str:
            save_str += "\t"
        else:
            save_str += "    "
        save_str += "pickle.dump(" + dict_res + ", f)\n\n"

        # Start generating new script
        
        # Add new import for pickle
        gen_script = ["import pickle\n\n"]

        # Add pre-processing + inference + save
        gen_script += main_code[0:inference_line]
        gen_script += [new_inference_str]
        gen_script += [save_str]
        gen_script += main_code[name_line:]


        for fh in first_half:
            partition_dir = os.path.join(self.designs_dir, component_name, fh)
            idx_onnx_line = 0
            for idx, line in enumerate(gen_script):
                if '--onnx_file' in line:
                    new_onnx_file_line = line.replace(
                        '{}'.format(orig_onnx_file), '{}.onnx'.format(fh))
                    idx_onnx_line = idx
            new_gen_script = gen_script[:idx_onnx_line] + [new_onnx_file_line] + gen_script[idx_onnx_line+1:]
            with open(os.path.join(partition_dir, 'main.py'), 'w') as f:
                f.writelines(new_gen_script)

    def _generate_second_half_code(self, component_name, second_half, has_exec_time):

        base_design = os.path.join(self.designs_dir, component_name, 'base')
        # Get main script
        with open(os.path.join(base_design, 'main.py'), 'r') as f:
            main_code = f.readlines()
        
        # Get load_and_inference line
        inference_row = [l for l in main_code if ('load_and_inference' in l and 'import' not in l)]
        if len(inference_row) > 1:
            raise Exception(
                "Multiple ONNX load_and_inference calls found in {} script. Only one is allowed.".format(
                    os.path.join(base_design, 'main.py')))
        elif len(inference_row) == 0:
            raise Exception(
                "ONNX load_and_inference call required in {} script.".format(
                    os.path.join(base_design, 'main.py')))
        
        inference_line = np.where(np.array(main_code) == inference_row[0])[0][0]

        inference_str = main_code[inference_line]
        inference_str_res, inference_cmd = inference_str.split("=")
        
        # Compute number of spaces at the beginning
        spaces_str = ""
        for i in range(len(inference_str_res)):
            if inference_str_res[i] not in [" ", "\t"]:
                break
            if inference_str_res[i]  == " ":
                spaces_str += " "
            elif inference_str_res[i] == "\t":
                spaces_str += "\t"
        dict_res, out_res = inference_str_res.replace(" ", "").replace("\t", "").split(',')
        new_inference_str = spaces_str + dict_res + ", " + out_res + " =" + " load_and_inference(args['onnx_file'], input_dict)\n"

        # Get main script line
        main_row = [l for l in main_code if ('def main(' in l and 'import' not in l)]
        main_line = np.where(np.array(main_code) == main_row[0])[0][0]
        
        # Get __name__ line
        name_row = [l for l in main_code if ("__name__=='__main__'" in l.replace(" ", "") and 'import' not in l)]
        name_line = np.where(np.array(main_code) == name_row[0])[0][0]

        # Generate pickle load str
        load_str = ""
        load_str += spaces_str
        load_str += "with open(args['input'], 'rb') as f:\n"
        load_str += spaces_str
        if "\t" in spaces_str:
            load_str += "\t"
        else:
            load_str += "    "
        load_str += "input_dict = pickle.load(f)\n"

        # Start generating new script
        
        # Add new import for pickle
        gen_script = ["import pickle\n\n"]
        gen_script += ["import os\n\n"]
        
        # Add load + inference + post-processing
        gen_script += main_code[0:main_line+1]
        gen_script += [load_str]
        gen_script += [new_inference_str]
        gen_script += main_code[inference_line+1:name_line] 

        # Add new if __name__ == '__main__'
        gen_script += ["\n"]
        gen_script += ["if __name__ == '__main__':\n"]
        gen_script += [spaces_str + "parser = argparse.ArgumentParser()\n"]
        gen_script += [spaces_str + "parser.add_argument('-i', '--input', required=True, help='path to input file')\n"]
        gen_script += [spaces_str + "parser.add_argument('-o', '--output', help='path to output directory')\n"]
        gen_script += [spaces_str + "args = vars(parser.parse_args())\n"]
        gen_script += [spaces_str + "input_filename = args['input'].split('/')[-1]\n"]
        gen_script += [spaces_str + "args['output'] = os.path.join(os.path.dirname(args['output']), input_filename)\n"]
        gen_script += [spaces_str + "main(args)"]
        
        for sh in second_half:
            partition_dir = os.path.join(self.designs_dir, component_name, sh)
            new_onnx_line = [spaces_str + "parser.add_argument('-y', '--onnx_file', default='onnx/{}.onnx', help='complete path to tge ONNX model')\n".format(sh)]
            new_gen_script = gen_script[:-4] + new_onnx_line + gen_script[-4:]
            with open(os.path.join(partition_dir, 'main.py'), 'w') as f:
                f.writelines(new_gen_script)