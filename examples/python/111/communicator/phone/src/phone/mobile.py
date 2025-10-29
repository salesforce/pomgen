import emulator.emulator as emulator
import message.message as message
import ringtone.ringtone as ringtone


def make_outbound_call():
    return [ringtone.get_ringtone(), message.get_message()]


def run_amiga_emulator():
    emulator.run_amiga_emulator()
