import os
import sys

STATS_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stats_layer/python/'))
if STATS_LAYER_PATH not in sys.path:
    sys.path.insert(0, STATS_LAYER_PATH)