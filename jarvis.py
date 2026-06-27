"""Jarvis — voice-driven personal assistant. Run: python jarvis.py"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime

from colorama import Fore, Style, init as colorama_init
from dotenv import load_dotenv

from config import LOG_DIR
from core.brain import Brain
from core.voice import Voice


def banner() -> None:
    print(
        f"""{Fore.CYAN}
     ██  █████  ██████  ██    ██ ██ ███████
     ██ ██   ██ ██   ██ ██    ██ ██ ██
     ██ ███████ ██████  ██    ██ ██ ███████
██   ██ ██   ██ ██   ██  ██  ██  ██      ██
 █████  ██   ██ ██   ██   ████   ██ ███████
{Style.RESET_ALL}
   {Fore.YELLOW}voice-driven Claude assistant — say something{Style.RESET_ALL}
   {Fore.LIGHTBLACK_EX}press Ctrl+C to quit{Style.RESET_ALL}
"""
    )


def log_turn(user: str, assistant: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / f"jarvis_{datetime.now():%Y-%m-%d}.log"
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n")
        f.write(f"USER: {user}\n")
        f.write(f"JARVIS: {assistant}\n")


def main() -> int:
    colorama_init()
    load_dotenv()
    banner()

    try:
        brain = Brain()
    except Exception as e:
        print(f"{Fore.RED}Brain failed to start: {e}{Style.RESET_ALL}")
        return 1

    try:
        voice = Voice()
    except Exception as e:
        print(f"{Fore.RED}Voice failed to start: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Falling back to text-only mode.{Style.RESET_ALL}\n")
        voice = None

    print(f"{Fore.GREEN}Ready.{Style.RESET_ALL}\n")

    while True:
        try:
            if voice:
                print(f"{Fore.LIGHTBLACK_EX}🎤 listening…{Style.RESET_ALL}", end="\r")
                user_text = voice.listen()
                print(" " * 30, end="\r")
                if not user_text:
                    continue
            else:
                user_text = input(f"{Fore.GREEN}you> {Style.RESET_ALL}").strip()
                if not user_text:
                    continue

            print(f"{Fore.GREEN}you>{Style.RESET_ALL} {user_text}")

            if user_text.lower().strip(" .,!?") in {"quit", "exit", "goodbye", "shut down", "stop jarvis"}:
                farewell = "Goodbye, sir."
                print(f"{Fore.MAGENTA}jarvis>{Style.RESET_ALL} {farewell}")
                if voice:
                    voice.speak(farewell)
                return 0

            reply = brain.respond(user_text)
            print(f"{Fore.MAGENTA}jarvis>{Style.RESET_ALL} {reply}")
            log_turn(user_text, reply)

            if voice:
                voice.speak(reply)

        except KeyboardInterrupt:
            print(f"\n{Fore.LIGHTBLACK_EX}— Ctrl+C —{Style.RESET_ALL}")
            return 0
        except Exception as e:
            print(f"{Fore.RED}error: {e}{Style.RESET_ALL}")
            traceback.print_exc()


if __name__ == "__main__":
    sys.exit(main())
