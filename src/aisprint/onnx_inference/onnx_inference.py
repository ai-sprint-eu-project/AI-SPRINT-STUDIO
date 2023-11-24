import os
import onnx
import onnxruntime as ort
import pandas as pd

def get_exit_node(exit_node_df):
    exit_node = pd.read_pickle(exit_node_df).iloc[0].exit_node
    return exit_node

def load_and_inference(onnx_file, input_dict):
    onnx_model = onnx.load(onnx_file)
    onnx.checker.check_model(onnx_model)
    onnx.helper.printable_graph(onnx_model.graph)

    # Check whether the onnx folder contains 'exit_nodes.df' file
    exit_node_file = os.path.join(os.path.dirname(onnx_file), 'exit_node.df')
    is_ee_model = False
    if os.path.exists(exit_node_file):
        is_ee_model = True

    #To get the inputs we must ignore the initializers, otherwise it would seem like we have a lot of inputs in some cases
    input_all = [node.name for node in onnx_model.graph.input]
    input_initializer =  [node.name for node in onnx_model.graph.initializer]
    net_feed_input = list(set(input_all) - set(input_initializer))

    so = ort.SessionOptions()
    
    # Get available providers
    available_providers = ort.get_available_providers()
    
    ort_session = ort.InferenceSession(onnx_file, so, providers=available_providers)

    session_input = {}
    for node_name in net_feed_input:
        session_input[node_name] = input_dict[node_name] 

    result = ort_session.run(None, session_input)

    return_dict = {}
    outputs = onnx_model.graph.output

    if is_ee_model:
        ee_return = []
        exit_node = get_exit_node(exit_node_file)
    
    # NOTE: the following supposes ordered results
    for idx, output in enumerate(outputs):
        if is_ee_model:
            if output.name != exit_node:
                return_dict[output.name] = result[idx]
            else:
                ee_return.append(result[idx])
        else:
            return_dict[output.name] = result[idx]

    if 'keep' in input_dict and input_dict:
        if input_dict['keep']:
            # Forward input tensors
            for input in net_feed_input:
                return_dict[input] = input_dict[input]
    
    # Unused input must be forwarded
    for input in input_dict:
        if input not in net_feed_input:
            return_dict[input] = input_dict[input]
    
    if is_ee_model:
        return return_dict, ee_return
    else:
        return return_dict, result