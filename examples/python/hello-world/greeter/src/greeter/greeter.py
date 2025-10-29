from computer import computer


def get_greeting():
    amiga = computer.get_amiga()
    return "Hello %s!" % amiga.echo("World")
