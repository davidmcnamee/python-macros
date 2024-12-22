import re

from mozzarella import macro

from .__macros__.types import GenStuff, gen_my_func, gen_my_other_func


@macro
def my_macro(code: str, *, x: int) -> str:
    print(x)
    res = code.replace("+", "-")
    res = re.sub(r"return (.*)", r"return str(\1)", res)
    res = res.replace("-> int", "-> str")
    return res


@my_macro(gen=gen_my_other_func, x=5)
def my_other_func(a: int, b: int) -> int:
    return a + 3 + b


@my_macro(gen=gen_my_func, x=6)
def my_func(a: int, b: int) -> int:
    return a + b


assert my_func(1, 2) == "-1"
assert my_other_func(1, 2) == "-4"


@my_macro(gen=GenStuff, x=7)
class Stuff:
    def __init__(self, c: int) -> None:
        self.c = c

    def my_method(self, a: int, b: int) -> int:
        return a + b + self.c

    @property
    def whatever(self) -> int:
        self.my_method(1, 2)
        return 4


class NewClass(Stuff):
    def whatever2(self) -> None:
        a = self.my_method(1, 2)
        print(a)


assert Stuff(5).my_method(3, 4) == str(3 - 4 - 5)
