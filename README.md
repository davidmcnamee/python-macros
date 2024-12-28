# Typed macros in Python

**Status**: like really early pre-alpha

Inspired by Rust procedural macros, this package creates a macro system for Python. You can define a macro by writing a function that accepts a string of code and returns another string of code.

Your expanded macro is written to a `__macro__` file in the same directory, and automatically imported.

You don't need to add another build step, just run your code as normal. As soon as it runs, your IDE and type checker will start to pass.

> Note: ideally, you should load your module on every save, so that you get better IDE support when using macros. That part's sort of optional, but for my small projects, it's been handy.

## Why would I want this?

Python is a dynamic language, so you can technically do anything... if you don't care about type hinting. But if you're a sane person, then you *must* care about type hinting, and therefore you might care about macros 😛 

I like to think of Python as:
* runtime code can talk to runtime code (normal)
* type checking code can talk to type checking code (normal)
* type checking code can talk to runtime code (e.g. dataclasses)
* ...but runtime code can't talk to type hinting code

^ macros fill the gap on that last missing step


### Example use cases

* If you have a decorator that's impossible to fit with type hints (python generics are nowhere near as powerful as typescript generics, for example); make it a macro instead!
  * E.g. you want to [Concatenate](https://docs.python.org/3/library/typing.html#typing.Concatenate) a kwarg to a paramspec, but it only supports positional arguments
* If you want to modify the behavior of Python code at runtime
  * E.g. you want to build a system where if/else statements are eager evaluated rather than lazy evaluated
* If you have some auto-generated code and you want to auto-generate some type-safe code on top of it
  * E.g. you want to add extra methods to the OpenAPI spec objects that were previously generated

## Differences from Rust

* Rust puts your code inline, this package puts it in a separate file. So you can't automatically use things from the outer scope unless you specify them in the macro.
* Rust macros deal with syntax trees, but this package lets you parse the code yourself; sometimes the formatting of your python code could be important -- it's up to you whether you parse the AST or just do basic string manipulation.


