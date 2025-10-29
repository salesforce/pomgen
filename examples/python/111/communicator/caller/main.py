import mobile


def run():
    # let's make a call
    for event in mobile.make_outbound_call():
        print(event)

    # start the amiga emulator to play lemmings
    mobile.run_amiga_emulator()


if __name__ == "__main__":
    run()
