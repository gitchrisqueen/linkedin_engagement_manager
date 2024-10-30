import sys

DEBUG_LEVEL = 2

def debug_function(func):
    global DEBUG_LEVEL

    def inner_function(*args, **kwargs):
        result = None
        if DEBUG_LEVEL >= 1:
            print("Before calling the function")
        if DEBUG_LEVEL != 2:
            result = func(*args, **kwargs)
        if DEBUG_LEVEL == 3:
            print("After calling the function")
        return result

    return inner_function


def myprint(message):
    sys.stdout.flush()
    sys.stdout.write('\r' + message + '\n')
    sys.stdout.flush()
