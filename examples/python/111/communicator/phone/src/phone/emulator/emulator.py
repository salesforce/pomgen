import startup


def run_amiga_emulator():
    print("Starting Amiga Emulator")
    for task in startup.get_tasks():
        print(" ", task)
