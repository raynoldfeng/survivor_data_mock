from typing import Dict, List, Tuple, Union, Optional, Set, Any, Callable
from enum import Enum
import csv
import datetime
import uuid
import random
import math
import json
import pickle

def serialize_object(obj):
    """
    将对象序列化为可以作为字典键的字节串
    :param obj: 待序列化的对象
    :return: 序列化后的字节串
    """
    try:
        return pickle.dumps(obj)
    except pickle.PicklingError:
        print("序列化失败，对象可能无法被序列化。")
        return None


def deserialize_object(serialized_bytes):
    """
    将序列化的字节串反序列化为原始对象
    :param serialized_bytes: 序列化后的字节串
    :return: 反序列化后的对象
    """
    try:
        return pickle.loads(serialized_bytes)
    except pickle.UnpicklingError:
        print("反序列化失败，输入可能不是有效的序列化字节串。")
        return None