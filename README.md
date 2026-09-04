# 🤖 NotifAI Core Framework Engine

> **An autonomous, telemetry-driven academic notice ingestion and Google Calendar synchronization agent.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/Orchestration-LangChain%20LCEL-1C2C4C?logo=chainlink)
![LLM](https://img.shields.io/badge/Model-Gemini%202.5%20Flash-4285F4?logo=google&logoColor=white)
![Validation](https://img.shields.io/badge/Validation-Pydantic%20v2-E92063?logo=pydantic&logoColor=white)
![API](https://img.shields.io/badge/Integration-Google%20Calendar%20API-4285F4?logo=googlecalendar&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Executive Overview

**NotifAI** is a production-grade AI agent designed to eliminate communication overhead in messy academic environments. It ingests unorganized, noisy college group chat logs (e.g., exported Telegram JSON files or raw text stream pastes), extracts structured scheduling intent via **Google Gemini 2.5 Flash**, enforces strict type safety via **Pydantic v2**, and automatically registers verified events into **Google Calendar** with customized multi-tier alarms.

---

## ⚡ Key Architectural Highlights

* 🎯 **Deterministic Schema Enforcement:** Binds Gemini 2.5 Flash directly to Pydantic models (`CollegeEventList`), guaranteeing zero JSON syntax errors or model hallucinations.
* 🕒 **Dynamic Temporal Anchoring:** Computes live runtime dates dynamically and injects them as anchor timestamps into the prompt matrix, cleanly resolving relative terms like *"next Tuesday"* or *"this Friday"*.
* 🔄 **Self-Healing OAuth 2.0 Engine:** Automatically manages token lifecycles with scoped permissions (`calendar.events`), background silent token refreshes, and automatic corrupted cache purging.
* 🛡️ **Fault-Isolated Execution Shields:** Individual event processing is wrapped inside localized `try-except` execution loops. A single invalid notice payload cannot crash brother entries in a batch stream.
* 📊 **Dual Telemetry Pipeline:** Simultaneous output streaming to both `stdout` for real-time monitoring and `app.log` for forensic debugging and auditing.

---

## 🔄 System Architecture & Data Flow

```text
┌─────────────────────────────────────────────────────────────────┐
│              UNSTRUCTURED NOTICE INGESTION GATEWAY              │
│   [ Option 1: Telegram JSON Exporter ]  |  [ Option 2: CLI Stream ]  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│      Context Compression & Noise Stripping Engine (O(M))        │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│     LangChain LCEL Pipeline + Gemini 2.5 Flash Execution        │
│          (PromptTemplate  ──>  Structured Pydantic Model)       │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│          Fault-Isolated Processing Shield & Filter Loop          │
└─────────────────┬───────────────────────────────┬───────────────┘
                  │                               │
       [is_important == True]           [is_important == False]
                  │                               │
                  ▼                               ▼
┌───────────────────────────────────┐   ┌─────────────────────────┐
│    Google Calendar REST API Sync  │   │  Drop Chat Noise & Log  │
│  • ISO 8601 Timestamp Generation  │   │  Telemetry Event Stream │
│  • 48-Hour & 7-Day Alarms Attached│   └─────────────────────────┘
└───────────────────────────────────┘
