# STT/TTS Provider Pricing Comparison (2026)

This document compares pricing for Speech-to-Text (STT) and Text-to-Speech (TTS) providers suitable for production deployment of the voice agent.

## Speech-to-Text (STT) Providers

### Pricing Overview

| Provider | Cost per minute | Billing Model | Notes |
|----------|----------------|---------------|-------|
| **AssemblyAI** | ~$0.0025/min | Pay per audio length | Best value, but 65% overhead on short calls |
| **Deepgram Nova-3** | ~$0.0043/min | Pay per second | Low latency, straightforward pricing |
| **OpenAI Whisper API** | ~$0.006/min | Pay per second | Good accuracy, moderate pricing |
| **Google Cloud STT** | ~$0.006-0.024/min | 15-sec blocks | High overhead due to block-rounding |
| **AWS Transcribe** | ~$0.024/min | 15-sec blocks | Higher cost, concurrency caps |

### Cost-Effective Recommendations

**For Testing:**
- **ElevenLabs STT**: Free tier available (limited usage) ✅ Currently integrated
- **OpenAI Whisper API**: $0.006/min with good accuracy ✅ Currently integrated

**For Production:**
- **AssemblyAI** ($0.0025/min): Best value for continuous transcription
- **Deepgram Nova-3** ($0.0043/min): Good balance of latency and cost
- **Expected cost**: ~$0.40-0.65 per hour for professional accuracy

### Implementation Notes
- Per-second billing (Deepgram, AssemblyAI) beats 15-sec block billing by up to 36% on short utterances
- For typical voice agent usage (< 8 sec utterances), avoid AWS and Google Cloud STT

## Text-to-Speech (TTS) Providers

### Pricing Overview

| Provider | Cost per 1k chars | Billing Model | Voice Quality | Latency |
|----------|------------------|---------------|---------------|---------|
| **Speechmatics** | $0.011 | Pay-as-you-go | Good | Medium |
| **Unreal Speech** | ~$0.05 | Pay-as-you-go | Good | Low |
| **Cartesia** | $0.05 | Pay-as-you-go | Excellent | Ultra-low (<500ms) |
| **Google Cloud TTS** | $16/million chars | Pay-as-you-go | Good | Medium |
| **Amazon Polly** | ~$16/million chars | Pay-as-you-go | Good | Medium |
| **Play.ht** | $5/mo starter | Subscription | Good | Low |
| **ElevenLabs** | $5/mo starter | Subscription | Premium | Low-Medium |

### Cost Estimates (Approximate)

Average response length: ~100 characters
Average conversation: ~50 exchanges = ~5,000 characters

- **Speechmatics**: $0.055 per conversation ($0.011/1k × 5k chars)
- **Cartesia**: $0.25 per conversation ($0.05/1k × 5k chars)
- **ElevenLabs**: ~$0.25 per conversation (subscription model)

### Cost-Effective Recommendations

**For Testing:**
- **ElevenLabs** (Free tier: limited usage) ✅ Currently integrated
- Good voice quality for development

**For Production - Budget Option:**
- **Speechmatics** ($0.011/1k chars): 27x cheaper than ElevenLabs
- **Unreal Speech** (~$0.05/1k chars): Claims 11x cheaper than ElevenLabs

**For Production - Balanced:**
- **Cartesia** ($0.05/1k chars): Excellent quality + ultra-low latency
- Best for real-time conversational AI

**For Production - Premium:**
- **ElevenLabs** (Subscription ~$5-25/mo): Highest quality voices
- Natural, emotionally expressive output

## Integration Recommendations

### Current Setup (Testing)
- ✅ **STT**: ElevenLabs (free tier) or Whisper API ($0.006/min)
- ✅ **TTS**: ElevenLabs (free tier)

### Recommended Production Setup

#### Budget-Conscious (~$1.50/hour of conversation)
- **STT**: AssemblyAI ($0.0025/min = $0.15/hr)
- **TTS**: Speechmatics ($0.011/1k chars ≈ $1.10/hr for typical usage)
- **LLM**: Minimax (your chosen provider)

#### Balanced Quality/Cost (~$2.50/hour)
- **STT**: Deepgram Nova-3 ($0.0043/min = $0.26/hr)
- **TTS**: Cartesia ($0.05/1k chars ≈ $5/hr, but with better caching could be ~$2/hr)
- **LLM**: Minimax

#### Premium Quality (~$3-5/hour)
- **STT**: OpenAI Whisper API ($0.006/min = $0.36/hr)
- **TTS**: ElevenLabs (subscription model)
- **LLM**: Minimax or upgrade to Claude

## Local/Self-Hosted Alternatives

For Raspberry Pi 4 (4GB RAM) deployment:

### STT
- **Whisper.cpp** (local): Free, but may be slow on RPi4
- **Vosk** (local): Lightweight, good for constrained hardware
- **Coqui STT** (local): Open source, moderate accuracy

### TTS
- **Piper TTS** (local): Fast, lightweight, good quality
- **Coqui TTS** (local): Higher quality, more resource-intensive
- **eSpeak-ng** (local): Very lightweight, robotic voice

**Note**: Local models eliminate API costs but may have higher latency and lower quality on RPi4 hardware.

## Sources

**STT Pricing:**
- [Speech-to-Text API Pricing Breakdown 2025](https://deepgram.com/learn/speech-to-text-api-pricing-breakdown-2025)
- [5 Google Cloud Speech-to-Text alternatives](https://www.assemblyai.com/blog/google-cloud-speech-to-text-alternatives)
- [Deepgram Pricing](https://deepgram.com/pricing)
- [Deepgram vs OpenAI vs Google STT Comparison](https://deepgram.com/learn/deepgram-vs-openai-vs-google-stt-accuracy-latency-price-compared)

**TTS Pricing:**
- [Best TTS APIs in 2026](https://www.speechmatics.com/company/articles-and-news/best-tts-apis-in-2025-top-12-text-to-speech-services-for-developers)
- [ElevenLabs API Pricing](https://elevenlabs.io/pricing/api)
- [Text-to-Speech Pricing Calculator](https://llmpricingcalculator.com/llm-text-to-speech-pricing)
- [Unreal Speech](https://unrealspeech.com/)
- [Text-to-Speech Pricing Comparison 2025](https://comparevoiceai.com/tts)
- [ElevenLabs vs. Cartesia](https://elevenlabs.io/blog/elevenlabs-vs-cartesia)
