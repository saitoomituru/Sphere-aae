"""MLC Engine Python example."""

from sphere_aae import SphereAaeEngine

# Create engine
model = "HF://sphere-aae/Llama-3-8B-Instruct-q4f16_1-AAE"  # pylint: disable=invalid-name
engine = SphereAaeEngine(model)

# Run chat completion in OpenAI API.
for response in engine.chat.completions.create(
    messages=[{"role": "user", "content": "What is the meaning of life?"}],
    model=model,
    stream=True,
):
    for choice in response.choices:
        print(choice.delta.content, end="", flush=True)
print("\n")

engine.terminate()
