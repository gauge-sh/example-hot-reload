from example.module_0 import file_3
from example.module_1 import file_1
from example.module_2 import file_2


def example_function_0():
    print("This is example function 0 in module_5/file_1.py")
    return 42


def example_function_1():
    print("This is example function 1 in module_5/file_1.py")
    return 42


def example_function_2():
    print("This is example function 2 in module_5/file_1.py")
    return 42


if __name__ == "__main__":
    file_3.example_function_2()
    file_1.example_function_1()
    file_2.example_function_0()
