import json
from pathlib import Path

from sphere_aae.protocol.generation_config import GenerationConfig
from sphere_aae.serve import data
from sphere_aae.serve.sync_engine import EngineConfig, SyncSphereAaeEngine


def get_test_image(config) -> data.ImageData:
    return data.ImageData.from_url("https://llava-vl.github.io/static/images/view.jpg", config)


def test_engine_generate():
    # Create engine
    model = "dist/llava-1.5-7b-hf-q4f16_1-AAE/params"
    model_lib = "dist/llava-1.5-7b-hf-q4f16_1-AAE/llava-1.5-7b-hf-q4f16_1-AAE.so"
    engine = SyncSphereAaeEngine(
        model=model,
        model_lib=model_lib,
        mode="server",
        engine_config=EngineConfig(max_total_sequence_length=4096),
    )
    max_tokens = 256

    with open(Path(model) / "sphere-aae-chat-config.json", "r", encoding="utf-8") as file:
        model_config = json.load(file)

    prompts = [
        [
            data.TextData("USER: "),
            get_test_image(model_config),
            data.TextData("\nWhat does this image represent? ASSISTANT:"),
        ],
        [
            data.TextData("USER: "),
            get_test_image(model_config),
            data.TextData("\nIs there a dog in this image? ASSISTANT:"),
        ],
        [data.TextData("USER: What is the meaning of life? ASSISTANT:")],
    ]

    output_texts, _ = engine.generate(
        prompts, GenerationConfig(max_tokens=max_tokens, stop_token_ids=[2])
    )

    for req_id, outputs in enumerate(output_texts):
        print(f"Prompt {req_id}: {prompts[req_id]}")
        if len(outputs) == 1:
            print(f"Output {req_id}:{outputs[0]}\n")
        else:
            for i, output in enumerate(outputs):
                print(f"Output {req_id}({i}):{output}\n")


if __name__ == "__main__":
    test_engine_generate()
