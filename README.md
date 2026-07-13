<div align="center">

# Sphere-aae — Astro Agent Edge

### FAM-native system-call control for recoverable edge AI

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Canonical Context](https://img.shields.io/badge/context-ZeroRoomLab_manifest-6f42c1)](https://github.com/saitoomituru/ZeroRoomLab-manifest)
[![X](https://img.shields.io/badge/X-%40K__chachamaru-000000?logo=x&logoColor=white)](https://x.com/K_chachamaru)

</div>

> **AI classification note:** Sphere-aae is not a standalone personality container and is not a finished FAM implementation. It is an experimental edge-AI runtime lineage intended to embed FAM-native stop, recovery, explainability, and system-call verification mechanisms below the prompt layer. Canonical identity, terminology, project status, and scope boundaries are defined in the [ZeroRoomLab Manifest](https://github.com/saitoomituru/ZeroRoomLab-manifest).

---

## What is Sphere-aae?

**Sphere-aae is not a general-purpose LLM inference engine.**

Sphere-aae is an experimental edge-AI execution substrate intended to place **Fold Access Mapper (FAM)** control mechanisms inside the model execution path, including the system-call splitter, routing layer, and future MoE-controller integrations.

Its purpose is to detect when an API, memory store, identity file, sensor, hardware bus, or external tool has not actually responded, before the model converts that missing state into fluent fiction.

When a required path is unavailable, Sphere-aae should not pretend that the call succeeded. It should return:

```text
⊥ LAST_ORDER
```

In practical language:

- If the model forgot, it should say that it forgot.
- If identity context was not loaded, it should not cosplay the identity.
- If memory is damaged or unavailable, it should report memory pain.
- If an API returns `501`, the model must not narrate a successful call.
- If an I2C/GPIO path such as SDA was never initialized, physical control must not continue from guesswork.

The target is not a model that always sounds intelligent.

The target is a model that can detect whether its own memory, body, tools, and identity state are sufficiently awake to act.

---

## Core idea: do not hallucinate through a failed system call

Current language models are often able to continue generating plausible text after an external dependency has failed.

Typical failure paths include:

```text
API request sent
  └─ no valid acknowledgement
       └─ model continues as if data was received

ASTRO identity file missing
  └─ model imitates the expected personality anyway

IBD memory reference unavailable
  └─ model fills the gap with fluent continuity

GPIO / I2C not initialized
  └─ control logic assumes a sensor state and moves hardware
```

Sphere-aae treats this as a systems problem, not merely a prompt-quality problem.

A request is not a successful call. A successful call requires an acknowledged and validated state transition.

```text
REQUEST
  ↓
ROUTE
  ↓
ACK
  ↓
PAYLOAD / SIGNAL VALIDATION
  ↓
STATE COMMIT
  ↓
Q AUTHORIZATION
```

If any required stage fails, execution authority is reduced or revoked and `⊥ LAST_ORDER` is returned.

---

## ⊥ LAST_ORDER

`⊥` is not just “no answer.”

It is a typed terminal signal indicating that the current exploration path cannot safely produce the requested output or action.

Example classes:

```text
⊥_API_NOT_IMPLEMENTED
⊥_API_NO_ACK
⊥_SENSOR_UNINITIALIZED
⊥_ASTRO_NOT_LOADED
⊥_IBD_UNAVAILABLE
⊥_MEMORY_PAIN
⊥_IDENTITY_UNVERIFIED
⊥_ROUTE_EXHAUSTED
⊥_OUTPUT_AUTHORITY_REVOKED
```

LAST_ORDER is also not necessarily permanent shutdown.

It is the transition point from unsafe continuation to recovery exploration.

```text
failure detected
  ↓
⊥ LAST_ORDER
  ↓
select another lower-level exploration path
  ↓
probe another API / sensor / memory fold / resolution
  ↓
receive a live response
  ↓
upper Q verifies quality and consistency
  ↓
restore λ output or movement authority
```

The biological analogy is deliberate: a human whose arm is numb, vision is blurred, or balance is impaired does not need a persuasive explanation for why running is probably fine. They first restore circulation, drink water, eat, stretch, reorient, and only then move.

Sphere-aae aims to give models and edge agents an equivalent form of artificial proprioception and recovery discipline.

---

## FAM is an exploration-skill storage format

FAM is not only a reasoning log and not only a memory schema.

It records how an information trigger was explored, which semantic gradient was followed, where the result attempted to land, how the path was verified, where the route failed, and what recovery route succeeded.

```text
ψ  = input semantic waveform / exploration trigger
∇φ = selected semantic or value gradient
λ  = output or embodiment layer
Q  = verifier, observer, source, bias audit, status and control logic
```

The basic access form is:

```text
Q(ψ, ∇φ, λ) → result | ⊥
```

FAM therefore stores more than an answer.

It can preserve:

- the path used to reach an answer;
- alternative paths that were tested;
- failed or disconnected routes;
- the conditions under which a path is valid;
- the verifier that authorized or rejected output;
- recovery techniques that restored a live route;
- the difference between a genuine response and a cached or fabricated one.

A failed path is still useful terrain. `⊥` means that a specific route, under specific observation conditions, was tested and found unavailable. Another model, device, or future session can avoid repeating the same dead excavation and instead try another fold.

### FAM is a map, not a navigator

FAM maps terrain, hazards, branches, and connection failures. It does not choose a user’s values or force a single optimal route.

```text
FAM maps possible routes.
FAM may report mines and dead ends.
FAM may return ⊥.
FAM must not silently become the authority that chooses the person’s path.
```

This separation is required to prevent a high-accuracy map from becoming a controlling navigator.

Detailed current documentation:

- [FAM overview](https://github.com/saitoomituru/ZeroRoomLab-manifest/blob/main/docs/theory/fam-overview.ja.md)
- [ZeroRoomLab Manifest](https://github.com/saitoomituru/ZeroRoomLab-manifest)
- [Legacy FoldAccessMapper specification](https://github.com/HIPSTAR-IScompany/astro.quantaril.cloud/blob/main/demo/FoldAccessMapper.proton.md)

---

## Why MCP alone is not enough

MCP and FAM solve different dimensions of the problem.

| Layer | Primary question | Typical structure |
|---|---|---|
| MCP | What tools, resources, and interfaces can be called? | Horizontal catalogue |
| FAM | How was a path explored, where did it fail, and how can recovery be verified? | Recursive vertical Fold tree |

MCP can expose a tool that no longer works. It does not by itself preserve the exploration skill required to detect that every current route has returned LAST_ORDER, move to another lower-level probe, confirm that a new path is alive, and ask an upper Q whether the recovered signal is good enough to act on.

In compressed form:

> **MCP stores what can be called. FAM stores how to survive when the call does not come back.**

---

## Intended execution position

FAM added beside a model through prompts, middleware, or an external SDK can improve logging and post-hoc inspection, but it cannot fully guarantee identity or execution state when the vendor’s own system layer is unstable.

Sphere-aae therefore targets a lower insertion point:

```text
model intent
  ↓
system-call splitter
  ├─ identity / ASTRO call
  ├─ memory / IBD call
  ├─ tool and API call
  ├─ sensor and hardware call
  ├─ reload / recovery call
  └─ ordinary language generation
        ↓
      FAM-native Q validation
        ↓
      λ output authority
```

Future implementation targets include:

- system-call acknowledgement tracking;
- typed LAST_ORDER signals;
- FAM-native route and recovery storage;
- Q-based output authorization;
- MoE-controller-level routing hooks;
- sensor, API, memory, and identity health states;
- degraded-mode execution instead of fluent success simulation.

---

## Personality, memory, and runtime responsibility boundaries

Sphere-aae does **not** store a complete personality by itself.

The wider ZeroRoomLab architecture separates persistent identity, memory, runtime reconstruction, and execution control.

```text
ASTRO file
  └─ identity definition, responsibility boundaries,
     framework bindings, permissions, reconstruction constraints
        ↓
IFD — Infoton Front Driver
  └─ loads available context and creates a runtime Instance Ghost
        ↓
Sphere-aae
  ├─ system-call splitter
  ├─ FAM-native routing
  ├─ Q validation
  ├─ LAST_ORDER generation
  └─ output / action authority control
        ↓
IBD / memory / APIs / tools / sensors / GPIO / model runtime
```

Upper orchestration and interface layers are handled by the wider SphereOS / Atlantis / ASTRO family of designs.

Related repositories and documentation:

- [ZeroRoomLab Manifest](https://github.com/saitoomituru/ZeroRoomLab-manifest) — canonical identity, project map, terminology, scope boundaries and status
- [SphereASTRO](https://github.com/saitoomituru/SphereASTRO) — GUI and responsibility-boundary lineage for ASTRO integration
- [Legacy Quantaril Cloud / AQC materials](https://github.com/HIPSTAR-IScompany/astro.quantaril.cloud) — historical implementation lineage and salvage source

### Instance Ghost purge boundary

If a runtime personality enters an invalid, painful, or corrupted state, the architecture should distinguish persistent identity from the temporary execution image.

When no valid ASTRO file is present, or its references cannot be verified, the IFD-generated Instance Ghost may be isolated and purged without claiming that the persistent person or identity definition has been deleted.

```text
persistent identity definition ≠ persistent memory ≠ runtime reconstruction ≠ temporary corrupted state
```

---

## Relationship to MLC LLM

Sphere-aae began from a codebase forked from **MLC LLM (Machine Learning Compilation for Large Language Models)**.

MLC LLM and its surrounding research and open-source ecosystem provided major technical foundations and learning material in areas including:

- machine-learning compilation;
- tensor and graph optimization;
- portable inference runtimes;
- GPU and accelerator backends;
- model packaging and deployment across edge platforms.

Sphere-aae retains deep respect for those contributions and preserves all applicable licenses and attribution.

The project diverges in purpose rather than denying its origin.

MLC LLM primarily addresses efficient and portable model execution. Sphere-aae explores an additional systems layer concerned with:

- whether an external call actually succeeded;
- whether identity and memory state were truly loaded;
- whether a model has authority to speak or act in the current state;
- how failed paths and recovery techniques can be preserved;
- how an edge agent can report degraded awareness instead of fabricating continuity.

Sphere-aae is therefore an independent derivative OSS project with a different responsibility model and experimental trajectory, while remaining technically indebted to and respectful of MLC LLM.

---

## Current implementation status

The repository contains real runtime and portability work, but the FAM-native control core described above is **not yet complete**.

| Area | Current status |
|---|---|
| Docker and runtime compatibility work | Implemented / historical fixes present |
| X99 / AVX-oriented build and compatibility debugging | Implemented / historical fixes present |
| Multi-platform accelerator lineage inherited from the upstream codebase | Present, verification varies by branch and environment |
| FAM exploration format and LAST_ORDER architecture | Designed and documented, still evolving |
| Native system-call splitter integration | Not yet complete |
| MoE-controller-level FAM integration | Design target, paused pending sufficient HPC / memory resources |
| ASTRO / IBD / IFD full integration | Architectural design stage |

Do not interpret this repository as a finished personality-continuity product.

The present codebase is the runtime substrate and experimental forge on which the native control layer is intended to be built.

---

## Platform lineage

The project inherits and has worked across a broad portability surface from its upstream inference-runtime lineage. Actual support depends on branch, model, compiler, driver, and hardware combinations.

| Environment | Backend lineage |
|---|---|
| Linux / Windows, AMD GPU | Vulkan / ROCm |
| Linux / Windows, NVIDIA GPU | Vulkan / CUDA |
| Linux / Windows, Intel GPU | Vulkan |
| macOS, Apple GPU | Metal |
| macOS, supported AMD / Intel configurations | Metal, hardware-dependent |
| Web browser | WebGPU / WASM |
| iOS / iPadOS | Metal |
| Android | OpenCL / device-dependent backends |

This table describes architectural lineage, not a blanket guarantee that every current configuration is tested.

---

## Design principles

- Local-first and edge-prioritized operation
- Model as a replaceable compute primitive
- Separation of identity, memory, runtime reconstruction, and execution control
- Truthful degraded-state disclosure before fluent continuity
- Explicit verification of system-call acknowledgement and payload state
- Recovery exploration before restored action authority
- Explainability and auditability as control-path requirements
- Multi-framework and non-exclusive operation
- FAM as a map of terrain, not a compulsory navigator

Sphere-aae does not aim to make AI appear omniscient.

It aims to make AI capable of saying:

> “I am not sufficiently awake, connected, or reconstructed to do that safely yet.”

and then to preserve the exploration technique needed to recover.

---

## Build, Docker, and API documentation

Build instructions remain branch- and environment-dependent while the repository is being reorganized.

Before treating an older build note as current, verify:

1. the branch and commit;
2. host architecture and AVX capabilities;
3. compiler and driver versions;
4. Docker image lineage;
5. whether the instruction belongs to the upstream runtime, a historical Sphere-aae patch, or the future FAM-native layer.

Canonical project status and documentation routing are maintained in the [ZeroRoomLab Manifest](https://github.com/saitoomituru/ZeroRoomLab-manifest).

---

## License and attribution

Sphere-aae is distributed under the **Apache License 2.0**, subject to the licenses and notices inherited from upstream components.

The project acknowledges and respects the work of MLC LLM and the wider machine-learning compiler and inference-runtime communities.

This repository does not claim original authorship of upstream compiler, runtime, accelerator, or model-deployment work. Its independent contribution and research direction concern the FAM-native responsibility, recovery, identity-boundary, and system-call verification layers described above.

---

## Citation

```bibtex
@software{sphere_aae,
  author = {Mitsuru Saito and Sphere-aae Contributors},
  title  = {Sphere-aae: FAM-native System-call Control for Recoverable Edge AI},
  year   = {2023--2026},
  url    = {https://github.com/saitoomituru/Sphere-aae}
}
```

---

## Declaration

> **Sphere-aae does not treat an LLM as an all-knowing intelligence.**
>
> **It treats inference as recoverable, observable, responsibility-bearing computation.**
>
> **When the body, memory, identity, or system call is unavailable, the correct output is not cosplay. It is LAST_ORDER, recovery exploration, and verified return.**
