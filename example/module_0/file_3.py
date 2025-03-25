from example.module_5 import file_2
from example.module_6 import file_1


def example_function_0():
    print("This is example function 0 in module_0/file_3.py")
    return 42


def example_function_1():
    print("This is example function 1 in module_0/file_3.py")
    return 42


def example_function_2():
    print("This is example function 2 in module_0/file_3.py")
    return 42


if __name__ == "__main__":
    file_2.example_function_0()
    example_function_1()
    file_1.example_function_2()
