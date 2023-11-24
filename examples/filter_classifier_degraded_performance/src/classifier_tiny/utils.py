# Adapted from keras
def preprocess_input(x):

    # 'RGB'->'BGR'
    x = x / 255.

    return x 