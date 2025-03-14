import random

def random_drink():
    drinks = ["coffee", "tea", "beer", "wine", "water"]
    return random.choice(drinks)

if __name__ == "__main__":
    print(f"You should drink some {random_drink()}")
