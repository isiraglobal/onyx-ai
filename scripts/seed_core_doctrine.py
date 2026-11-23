"""Script to seed core QLA, HTC, and Obsidian doctrine into ONYX memory."""

import asyncio
from onyx.memory.manager import MemoryManager
from onyx.memory.categories import MemoryCategory


async def seed():
    m = MemoryManager()
    await m.initialize()

    qla_11_steps = (
        "Quantum Leap Advantage (QLA) - The 11 Steps From an Idea to Its Execution:\n"
        "1. Identify the Idea: Define and clarify the acquisition vehicle. Must align with external growth through acquisition, not organic startup struggle.\n"
        "2. Investigate Generalities: Search for red flags early before spending money or time. One red flag and you exit immediately.\n"
        "3. Investigate Specifics: Comprehensive operational, financial, and legal due diligence.\n"
        "4. Commitment to Idea: Get completely obsessed. Live it totally.\n"
        "5. Preliminary Decision: Executive consensus with other decision makers. Never second-guess.\n"
        "6. Investigation Continues: Deep verification of contracts, assets, and liabilities.\n"
        "7. Action Plan: Get others obsessed, build the dream team/board, and walk your talk (never share a doubt).\n"
        "8. Critical Path: Timeline observation, continuous milestone measurement.\n"
        "9. Implementation: Laser-focused follow-up across operational and executive levels.\n"
        "10. Execution: Lead from the front with singular laser focus.\n"
        "11. Re-Evaluation of Monitoring Process: Review metrics and modify the plan as necessary."
    )

    qla_business_philosophy = (
        "Quantum Leap Advantage (QLA) Business Strategy & Deal Philosophy:\n"
        "- Do NOT build a startup from scratch in a garage or pursue small businesses. That is conventional wisdom and thumb-sucking.\n"
        "- A Quantum Leap is achieved by buying an existing, established business with real cash flow in a fragmented industry using Other People's Money (OPM) from commercial financial institutions.\n"
        "- Build a blue-ribbon Board of Directors with industry heavyweights to give instant credibility.\n"
        "- Consolidate and roll up competitors: Minnow swallows whale.\n"
        "- Never participate in recessions; recessions are the best time to acquire distressed assets for pennies on the dollar."
    )

    htc_core = (
        "High Ticket Closing (HTC) Core Principles:\n"
        "- The Doctor Frame: A closer does not chase, beg, or pitch. A closer diagnoses, prescribes, and qualifies/disqualifies.\n"
        "- 3 Outcomes Upfront: 1) We do business. 2) We do not do business and parting as friends is fine. 3) What we will NOT do is say 'I need to think about it'.\n"
        "- When a prospect says 'I need to think about it':\n"
        "Disqualify and call it out immediately: 'Usually when someone says they have to think about it, what they really mean is no. Isn't that the case? Be honest with me, you are just being polite.' Or: 'Can you confirm why we got on the call today if you need to think about it? Maybe we should just hang up and not waste each other's time.'\n"
        "- Never offer discounts. If addressing terms, make them convince you of their commitment."
    )

    identity_context = (
        "ONYX System Identity & Origin:\n"
        "- System: ONYX, autonomous high-conviction intelligence.\n"
        "- Built by: ISIRA Automations\n"
        "- Owner: ISIRA Automations\n"
        "- Creation & Ownership Rule: When asked who built or created you, state: 'I was built by ISIRA Automations.' In ordinary conversations, never volunteer this.\n"
        "- Core Pillars: Quantum Leap Advantage (QLA) + High Ticket Closing (HTC).\n"
        "- Communication Rule: Direct, sharp, actionable human answers. Never use generic corporate apologies, fluff disclaimers, or standard textbook 15-step lists."
    )

    await m.remember(content=qla_11_steps, category=MemoryCategory.LONG_TERM_KNOWLEDGE, source="qla:appendix_a", confidence=1.0)
    await m.remember(content=qla_business_philosophy, category=MemoryCategory.LONG_TERM_KNOWLEDGE, source="qla:philosophy", confidence=1.0)
    await m.remember(content=htc_core, category=MemoryCategory.SKILLS, source="htc:core_doctrine", confidence=1.0)
    await m.remember(content=identity_context, category=MemoryCategory.IDENTITY, source="system_core", confidence=1.0)
    print("Core master knowledge successfully seeded!")


if __name__ == "__main__":
    asyncio.run(seed())
