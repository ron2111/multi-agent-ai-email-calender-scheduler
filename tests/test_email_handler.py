# test_email_handler.py
from agents import email_handler

if __name__ == "__main__":
    result = email_handler.remote()
    output = ray.get(result)
    print(output)
