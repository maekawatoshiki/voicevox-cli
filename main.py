import argparse
import json
import logging
import os
from dataclasses import dataclass
from typing import List, Dict

import requests


def get_speaker_ids() -> Dict[str, int]:
    speakers = requests.get(f"{ENDPOINT}/speakers")
    assert speakers.ok

    speaker_name_to_id = {}

    for speaker in speakers.json():
        for style in speaker["styles"]:
            speaker_name_to_id[f"{speaker['name']}:{style['name']}"] = style["id"]

    return speaker_name_to_id


ENDPOINT: str = os.getenv("VVCLI_ENDPOINT", default="127.0.0.1:50021")
SPEAKER_NAME_TO_ID: Dict[str, int] = get_speaker_ids()


@dataclass
class Utterance:
    text: str
    speaker_name: str


def parse_file(file: str) -> List[Utterance]:
    with open(file, "r") as f:
        lines = f.readlines()

    speaker_name = "ずんだもん:ノーマル"
    utters = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            # Specify speaker
            continue

        utters.append(Utterance(text=line, speaker_name=speaker_name))

    logging.info(f"{len(utters)} utterances detected")

    return utters


def synth_voice(
    utters: List[Utterance],
) -> bytes:
    # TODO: Support multiple speakers
    assert len(utters) > 0
    assert all(u.speaker_name == utters[0].speaker_name for u in utters)

    text = "\n".join(u.text for u in utters)
    speaker_name = utters[0].speaker_name
    speaker = SPEAKER_NAME_TO_ID.get(speaker_name)

    query = requests.post(
        f"{ENDPOINT}/audio_query", params={"text": text, "speaker": speaker}
    )
    assert query.ok
    voice = requests.post(
        f"{ENDPOINT}/synthesis",
        params={"speaker": speaker},
        data=json.dumps(query.json()),
    )
    assert voice.ok

    return voice.content


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="text file (utterances)")
    parser.add_argument("-o", "--output", help="output wav file", default="test.wav")
    args = parser.parse_args()

    utters = parse_file(args.file)
    voice = synth_voice(utters)

    with open(args.output, mode="wb") as f:
        f.write(voice)

    logging.info(f"Output: {args.output} ({len(voice)} bytes)")


if __name__ == "__main__":
    main()
