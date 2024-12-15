from .__macros__ import my_func
import re
from mozzarella import macro

@macro()
def my_macro(code: str) -> str:
    res = code.replace("+", "-")
    res = re.sub(r"return (.*)", r"return str(\1)", res)
    res = res.replace("-> int", "-> str")
    return res

@my_macro(generated=my_func, x=5)
def my_func(a: int, b: int) -> int:
    return a + b

print(type(my_func(1, 2)), my_func(1, 2))
# prints "<class 'str'> -1"
