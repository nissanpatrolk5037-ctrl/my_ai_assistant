import os
from llama_cpp import Llama

MODEL_DIR = "local-llms"
_llm_cache = {}

def load_model(name, ctx=4096):
    if name not in _llm_cache:
        _llm_cache[name] = Llama(
            model_path=os.path.join(MODEL_DIR, name),
            n_threads=os.cpu_count(),
            n_ctx=ctx,
            verbose=False
        )
    return _llm_cache[name]

def run(model_name, prompt, max_tokens=512):
    llm = load_model(model_name)
    out = llm(prompt, max_tokens=max_tokens)
    return out["choices"][0]["text"].strip()


def judge_answer(prompt):
    return run("BAAI.JudgeLM-7B-v1.0.Q4_K_M.gguf", prompt)

def truth_check(prompt):
    return run("truthfulqa-truth-judge-llama2-7b.gguf", prompt)

def deep_reason(prompt):
    return run("DeepSeek-R1-Distill-Qwen-7B-Q4_1.gguf", prompt)

def experimental_reason(prompt):
    return run("xwin-lm-7b-v0.2.Q4_K_M.gguf", prompt)

def solve_math(prompt):
    return run("deepseek-math-7b-rl.Q4_K_M.gguf", prompt)

def code(prompt):
    return run("qwen2.5-coder-7b-instruct-q4_k_m.gguf", prompt)

def biomedical(prompt):
    return run("BioMedLM-7B.Q4_K_M.gguf", prompt)

def legal(prompt):
    return run("legal-llama-3-unsloth.Q4_K_M.gguf", prompt)

def casual_chat(prompt):
    return run("baichuan2-7b-chat.Q4_K_M.gguf", prompt)

def friendly_chat(prompt):
    return run("openbuddy-zephyr-7b-v14.1.Q4_K_M.gguf", prompt)

def open_discussion(prompt):
    return run("OpenAssistant-falcon-7b-sft-top1.gguf", prompt)

def creative_write(prompt):
    return run("gemma-7b.Q4_K_M.gguf", prompt)

def multilingual(prompt):
    return run("internlm2-chat-7B.Q4_K_M.gguf", prompt)

def world_knowledge(prompt):
    return run("Yi-1.5-9B-Chat-Q4_K_M.gguf", prompt)

def function_call(prompt):
    return run("llama-2-7b-function-calling.Q3_K_M.gguf", prompt)

def ultra_fast(prompt):
    return run("orca-mini-3b-gguf2-q4_0.gguf", prompt)

def micro_tasks(prompt):
    return run("MiniCPM-2B-dpo-fp32.Q4_K_M.gguf", prompt)

def compact_reason(prompt):
    return run("Phi-3-mini-4k-instruct-q4.gguf", prompt)

def general_assistant(prompt):
    return run("Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf", prompt)

def precise_instruction(prompt):
    return run("qwen2.5-7b-instruct-q4_k_m.gguf", prompt)

def lightweight_instruction(prompt):
    return run("qwen2.5-3b-instruct-q4_k_m.gguf", prompt)

def base_research(prompt):
    return run("s1-Qwen2.5-Base-7B.i1-Q4_K_M.gguf", prompt)

def synthetic_data(prompt):
    return run("synthia-7b.Q4_0.gguf", prompt)

def long_context(prompt):
    return run("mpt-7b-8k-chat.Q4_K_M.gguf", prompt, max_tokens=1024)

def supreme_intelligence(prompt):
    return run("qwen3-30b-a3b-q4_k_m.gguf", prompt, max_tokens=1024)

