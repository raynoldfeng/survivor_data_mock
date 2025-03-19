from typing import Dict, List, Tuple, Union, Optional, Set, Any, Callable
from enum import Enum
import csv
import datetime
import uuid
import random
import math
import json
import pickle
import datetime

def serialize_object(obj):
    try:
        return pickle.dumps(obj)
    except pickle.PicklingError:
        print("序列化失败，对象可能无法被序列化。")
        return None


def deserialize_object(serialized_bytes):
    try:
        return pickle.loads(serialized_bytes)
    except pickle.UnpicklingError:
        print("反序列化失败，输入可能不是有效的序列化字节串。")
        return None