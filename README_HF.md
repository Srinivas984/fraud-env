---
title: Fraud Investigator Environment
emoji: 🛡️
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
models:
  - Qwen/Qwen2.5-72B-Instruct
  - meta-llama/Llama-2-70b-chat-hf
license: apache-2.0
---

# 🛡️ Fraud Investigator - OpenEnv RL Environment

**OpenEnv-Compatible Fraud Detection Environment for Training Intelligent Agents**

## Quick Start

```bash
# Health check
curl http://localhost:7860/health

# Interactive API
http://localhost:7860/docs
```

## Features

- **3 Difficulty Levels:** EASY (1.0), MEDIUM (0.813), HARD (0.043)
- **OpenEnv Compliant:** Standard RL environment interface
- **Production Ready:** Docker containerized, fully tested
- **Realistic Fraud Scenarios:** Multi-pattern detection challenges

## Test Your Agent

```bash
python inference.py single_fraud       # EASY task
python inference.py multi_pattern_fraud # MEDIUM task
python inference.py adaptive_fraud_attack # HARD task
```

## Expected Scores

| Task | Baseline | Status |
|------|----------|--------|
| EASY | 1.000 | Perfect ✓ |
| MEDIUM | 0.813 | Strong ✓ |
| HARD | 0.043 | Challenging ✓ |

For full documentation, see [README.md](README.md)
