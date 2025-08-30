import os
import sys

PLATFORM_COMM_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../platform_comm_layer/python/'))
if PLATFORM_COMM_LAYER_PATH not in sys.path:
    sys.path.insert(0, PLATFORM_COMM_LAYER_PATH)

GRAPH_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../graph_layer/python/'))
if GRAPH_LAYER_PATH not in sys.path:
    sys.path.insert(0, GRAPH_LAYER_PATH)

GRAPH_MANAGER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../graph_manager/'))
if GRAPH_MANAGER_PATH not in sys.path:
    sys.path.insert(0, GRAPH_MANAGER_PATH)