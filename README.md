# Hackathon info — July 11, 2026 (NYC)

Organizer/sponsor research and setup info. Two same-day events are tracked here;
**the active target is the AI Healthcare Hack NYC** (confirmed by Advik, Jul 11).

---

## 🎯 ACTIVE: AI Healthcare Hack NYC — Arya Health & Twilio AI Startup Searchlight

Full capture: [`luma-ai-healthcare-hack-nyc.md`](./luma-ai-healthcare-hack-nyc.md)

- Devpost: https://ai-healthcare-hack.devpost.com/
- Deadline: **Jul 11, 2026 @ 3:30pm EDT** · Judging/demos 4:00–5:00pm
- Location: 307 W 36th St, floor 13 (Arya Health office)
- Challenge: production-ready **voice/text conversational AI agent** that carries a
  full healthcare workflow end-to-end (intake, scheduling, reminders, insurance
  verification, caregiver follow-up) — grounded in domain knowledge, personalized
  to the caller. Reliability/guardrails/security are the bar, not extras.
- **Must use Twilio telephony to qualify for sponsor prizes.**
- Sponsors: **Twilio** (AI Startup Searchlight), **Lovable**, **Arya Health**
- Judging: Technical implementation · Idea uniqueness · Team explanation · UI/UX (1–5 each)
- Judges: Anand Chandrasekaran (Arya), Nikki Hu (Arya), Twilio
- Prizes: $500/$300/$200 Twilio credits + Arya Health engineering interviews

### Chosen stack (decided)

- **Twilio** — telephony (required). Promo code `arya-hack` (see luma file for redemption steps)
- **ElevenLabs** — voice/TTS (not a sponsor, but best-in-class and pairs natively with
  Twilio ConversationRelay and via ElevenLabs Agents' Twilio integration)
- **Arya Health** — no public developer API found (aryahealth.ai is post-acute/home-health
  digital agents; the "arya.ai" APIs online are a different company). Their contribution is
  venue + hiring-interview prizes. **Strategic angle**: pick the *caregiver follow-up /
  home-health scheduling* workflow — it's literally Arya's domain, which should land well
  with the Arya judges.
- **Lovable** — sponsor credits available (Pro Plan, code `COMM-AI-GAYR`, alt
  `COMM-HEAL-UYEF`) — use for a quick dashboard/frontend showing transcripts + bookings.

### Setup checklist

- [ ] Twilio account + voice-capable phone number ([quick start](./luma-ai-healthcare-hack-nyc.md#event-blasts--resources-from-luma-updates-feed))
- [ ] Redeem Twilio promo `arya-hack`
- [ ] ElevenLabs account + API key
- [ ] Redeem Lovable Pro credit
- [ ] Devpost project page (name, one-liner, what/why, tools incl. Twilio usage, team, demo link)

OSS starter-repo research for this event → `advik-bhatt/emergence-hackathon-project`
(`ai-healthcare-hack-research.md`).

---

## Secondary: Enterprise Agents Hackathon — Emergence × Nebius

Full captures: [`devpost-enterprise-agents-hackathon.md`](./devpost-enterprise-agents-hackathon.md) ·
[`luma-emergence-x-nebius.md`](./luma-emergence-x-nebius.md) ·
[`nebius-hackathon-prerequisites.md`](./nebius-hackathon-prerequisites.md) ·
[`craft_databases.md`](./craft_databases.md) ·
[`research-starter-repos.md`](./research-starter-repos.md) ·
[`project-ideas.md`](./project-ideas.md) ·
[`SESSION-SUMMARY.md`](./SESSION-SUMMARY.md)

- Deadline: Jul 11, 2026 @ 5:00pm EDT · winners by 7pm
- Theme: agentic data-intelligence on **Emergence CRAFT** (MCP text-to-SQL semantic layer)
  + **Nebius Token Factory** inference (Nemotron-3 Super 120B), over Spider 2.0 databases
- Judging: CRAFT usage depth 30% · Insight quality 30% · Agent architecture 20% · Story clarity 20%
- Prizes: 1st = 6-month CRAFT access + $5,000 Nebius credits; 2nd/3rd/per-challenge = CRAFT + credits
- Links: [Luma](https://luma.com/f5smb6kp?tk=MMAqbM) · [NDA](https://scanned.page/6tITpm) ·
  [homepage](https://www.emergence.ai/hackathon#start) ·
  [starter repo](https://github.com/EmergenceAI/nebius-emergence-hackathon) ·
  [Nebius proxy](https://github.com/opencolin/claude-codex-nebius-proxy)

Other files: [`sponsor-env-vars.md`](./sponsor-env-vars.md) (env var setup for sponsor APIs).
