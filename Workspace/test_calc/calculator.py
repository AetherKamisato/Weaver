def add(a, b):
    """Return the sum of a and b."""
    return a + b


def divide(a, b):
    """Return the division of a by b. Raises ZeroDivisionError if b is 0."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


def factorial(n):
    """Return the factorial of a non-negative integer n."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("factorial is only defined for non-negative integers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def main():
    print("Welcome to Calculator!")
    print("Available operations: add, divide, factorial")
    
    op = input("Enter operation (add/divide/factorial): ").strip().lower()
    
    if op == "factorial":
        try:
            n_str = input("Enter a non-negative integer: ").strip()
            # Try to convert to int, or float first if user entered decimal
            n = int(n_str)
            result = factorial(n)
            print(f"Result: {result}")
        except ValueError as e:
            print(f"Error: {e}")
    elif op in ["add", "divide"]:
        try:
            a_str = input("Enter first number (a): ").strip()
            b_str = input("Enter second number (b): ").strip()
            
            # Support both int and float conversion
            a = float(a_str) if '.' in a_str or 'e' in a_str.lower() else int(a_str)
            b = float(b_str) if '.' in b_str or 'e' in b_str.lower() else int(b_str)
            
            if op == "add":
                result = add(a, b)
                print(f"Result: {result}")
            elif op == "divide":
                result = divide(a, b)
                print(f"Result: {result}")
        except ValueError as e:
            print(f"Error: Invalid number input. {e}")
        except ZeroDivisionError as e:
            print(f"Error: {e}")
    else:
        print("Error: Unknown operation selected.")


if __name__ == "__main__":
    main()
