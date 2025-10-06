import startup


def run():
    for task in startup.get_tasks():
        print(task)


if __name__ == "__main__":
    run()
