from example.module_1 import file_3
from example.module_0 import file_1


def example_function_0():
    print("This is example function 0 in module_6/file_1.py")
    return 42


def example_function_1():
    print("This is example function 1 in module_6/file_1.py")
    return 42


def example_function_2():
    print("This is example function 2 in module_6/file_1.py")
    return 42


if __name__ == "__main__":
    file_3.example_function_0()
    file_1.example_function_1()
    example_function_2()
