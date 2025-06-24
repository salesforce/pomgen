import hello
import calculator.calculator as calculator


if __name__ == "__main__":
    print(hello.get_greeting())
    print("Math is cool:", calculator.calculate("*", 2, 3))
