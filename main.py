import argparse
import asyncio
import io
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List

import requests
from pydub import AudioSegment


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
    id: int
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

        # Specify speaker
        if line.startswith("#"):
            speaker_name = line.split("#")[1].strip()
            continue

        utters.append(Utterance(id=len(utters), text=line, speaker_name=speaker_name))

    logging.info(f"{len(utters)} utterances detected")

    return utters


def synth_voice_sub(
    utter: Utterance,
) -> AudioSegment:
    speaker = SPEAKER_NAME_TO_ID.get(utter.speaker_name)

    query = requests.post(
        f"{ENDPOINT}/audio_query", params={"text": utter.text, "speaker": speaker}
    )
    assert query.ok
    voice = requests.post(
        f"{ENDPOINT}/synthesis",
        params={"speaker": speaker},
        data=json.dumps(query.json()),
    )
    assert voice.ok

    audio = AudioSegment.from_wav(io.BytesIO(voice.content))

    logging.info(f"synth_voice_sub: Synthesized id={utter.id} ({len(audio.raw_data)} bytes)")

    return audio


def synth_voice(
    utters: List[Utterance],
) -> AudioSegment:
    start = time.time()

    async def run(loop):
        async def run_req(utter: Utterance):
            return await loop.run_in_executor(None, synth_voice_sub, utter)

        tasks = [run_req(utter) for utter in utters]
        return await asyncio.gather(*tasks)

    loop = asyncio.get_event_loop()
    audio = sum(loop.run_until_complete(run(loop)))

    logging.info(f"synth_voice: elapsed: {time.time() - start:.2f} [s]")

    return audio


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="text file (utterances)")
    parser.add_argument("-o", "--output", help="output wav file", default="test.wav")
    args = parser.parse_args()

    utters = parse_file(args.file)
    voice = synth_voice(utters)

    voice.export(args.output, format="wav")

    logging.info(f"Output: {args.output} ({len(voice.raw_data)} bytes)")


if __name__ == "__main__":
    main()
