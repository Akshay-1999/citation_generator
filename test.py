class Animal:
    pass

class Dog(Animal):
    pass

my_dog = Dog()
print(isinstance(my_dog, Dog))    # Output: True
print(isinstance(my_dog, Animal)) # Output: True