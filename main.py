import argparse
import json
import os
from typing import List

import requests

ENDPOINT: str = os.getenv("VVCLI_ENDPOINT", default="127.0.0.1:50021")


def parse_file(file: str) -> List[str]:
    with open(file, "r") as f:
        lines = f.readlines()

    utters = []
    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            # Specify speaker
            continue

        utters.append(line)

    return utters


def synth_voice(utters: List[str], speaker: int = 1) -> None:
    text = "\n".join(utters)

    query = requests.post(
        f"{ENDPOINT}/audio_query", params={"text": text, "speaker": speaker}
    )
    voice = requests.post(
        f"{ENDPOINT}/synthesis",
        params={"speaker": speaker},
        data=json.dumps(query.json()),
    )

    with open("test.wav", mode="wb") as f:
        f.write(voice.content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="text file (utterances)")
    args = parser.parse_args()

    utters = parse_file(args.file)
    synth_voice(utters)


if __name__ == "__main__":
    main()
