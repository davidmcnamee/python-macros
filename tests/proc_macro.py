import re

from mozzarella import macro

from .__macros__ import my_func, my_other_func


@macro()
def my_macro(code: str, *, x: int) -> str:
    print(x)
    res = code.replace("+", "-")
    res = re.sub(r"return (.*)", r"return str(\1)", res)
    res = res.replace("-> int", "-> str")
    return res


@my_macro(generated=my_other_func, x=5)
def my_other_func(a: int, b: int) -> int:
    return a + 3 + b


@my_macro(generated=my_func, x=4)
def my_func(a: int, b: int) -> int:
    return a + b


assert my_func(1, 2) == "-1"
assert my_other_func(1, 2) == "-4"
