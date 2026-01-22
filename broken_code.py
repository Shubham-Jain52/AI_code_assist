
import random

def chaos(x):
    # NameError
    if x == "name":
        return not_defined_variable + 1

    # ZeroDivisionError
    if x == "zero":
        return 10 / 0

    # TypeError
    if x == "type":
        return "5" + 5

    # IndexError
    if x == "index":
        arr = [1, 2, 3]
        return arr[999]

    # KeyError
    if x == "key":
        d = {"a": 1}
        return d["missing"]

    # AttributeError
    if x == "attr":
        return "5".upper()

    # ValueError
    if x == "value":
        return int("not_a_number")

    # UnboundLocalError
    if x == "local":
        if False:
            y = 10
        return y + 1

    # RecursionError
    if x == "recurse":
        return chaos("recurse")

    # Memory blow attempt (may freeze your PC)
    if x == "memory":
        a = []
        while True:
            a.append("X" * 10_000_000)

    return "Somehow survived"


def main():
    tests = [
        "name", "zero", "type", "index", "key",
        "attr", "value", "local", "recurse"
        # DO NOT run "memory" unless you want suffering
    ]

    for t in tests:
        print
