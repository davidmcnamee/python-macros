"""
THIS FILE IS GENERATED BY A MACRO. DO NOT EDIT.
"""

import typing
from mozzarella import macro
import re


class GenStuff:
    def __init__(self, c: int) -> None:
        self.c = c

    def my_method(self, a: int, b: int) -> str:
        return str(a - b - self.c)

    @property
    def whatever(self) -> str:
        self.my_method(1, 2)
        return str(4)
