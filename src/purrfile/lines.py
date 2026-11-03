"""Everything the cat says. `**bold**` marks emphasis; the renderers turn it into bold text."""
from __future__ import annotations

from .stats import Stats

GROWTH_MILESTONES = (100, 500)
MILESTONE_WINDOW = 10
QUIET_DAYS = 7
STREAK_WEEKS = 4

JOKES: tuple[str, ...] = (
    # The five from the brainstorm, verbatim.
    "I tried to run sudo, but I'm not in the purr-sudoers file.",
    "Phishing? I'm only interested in the kind with actual fish.",
    "I sleep 16 hours a day, so for me every day is a zero-day.",
    "I don't need a firewall. I have a fur-wall.",
    "Error 404: treats not found.",
    # Security, but make it cat.
    "Social engineering tip: look cute, get treats. Works every time.",
    "My password is meow123. Please don't tell the other cats.",
    "I found a vulnerability in your desk: the coffee mug is unprotected.",
    "Have you tried turning it off and on again? I tried it on your coffee mug. It's on the floor now.",
    "I don't do brute force. I do brute purr-suasion.",
    "Two-factor authentication: one paw on the keyboard, one paw on your face.",
    "I'm not ignoring you. I'm rate-limiting you.",
    "My threat model is simple: the vacuum cleaner.",
    "I run my own red team. Mostly I just knock things off tables.",
    "Root access? I already sleep on the router.",
    "I don't need a VPN. Nobody can track me when I'm under the bed.",
    "Least privilege? I have the privilege of sitting on your keyboard.",
    "I always encrypt my naps. Nobody knows when they end.",
    "Port scanning complete: every sunny spot in the house is open.",
    "I patched the vulnerability. By lying on it.",
    "Zero trust policy: I don't trust the cucumber on the counter.",
    "I perform penetration testing on cardboard boxes daily.",
    "Your keyboard is warm, so technically it's a honeypot.",
    "I log everything. Mostly in the litter box.",
    "Captcha solved: I am definitely not a robot. Robots don't shed.",
    # Programming, but make it cat.
    "I only write purr-formant code.",
    "There's no place like 127.0.0.1. Except your keyboard. That's warmer.",
    "I have nine lives. Your production server has one. Be careful.",
    "Purr-ogramming is 10% writing code and 90% sitting on it.",
    "It works on my machine. My machine is a sunbeam.",
    "I pushed straight to main. What are you going to do, take away my treats?",
    "My favourite design pattern is the box. I fit in every one.",
    "I don't write bugs. I catch them.",
    "git blame says it was the dog.",
    "I reviewed your pull request. I sat on it. Approved.",
    "Tabs or spaces? Laps.",
    "I tried pair programming. The other cat stole my chair.",
    "Every keyboard is a mechanical keyboard if you walk on it hard enough.",
    "I'm fluent in three languages: Python, meow, and knocking things over.",
    "My code has no memory leaks. It just forgets on purpose, like me.",
    "I don't use dark mode. I just turn off the lights with my tail.",
    "Stack overflow? That's just me on top of your books.",
    "Ctrl+Z doesn't work on things I've pushed off the desk.",
    "I named my variables after my favourite snacks. Tuna is undefined again.",
    "Deploy on Friday? Sure, I'll be napping either way.",
)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def github_line(stats: Stats) -> str:
    """The day's one line about the account. The first matching rule wins.

    Images are drawn just after midnight UTC, so nothing here may say "today".
    """
    total = stats.year_total
    next_hundred = (total // 100 + 1) * 100
    if total > 0 and next_hundred - total <= MILESTONE_WINDOW:
        away = next_hundred - total
        tail = "I can feel myself growing!" if next_hundred in GROWTH_MILESTONES else "Big number incoming."
        return f"You're **{_plural(away, 'contribution')}** away from {next_hundred} this year. {tail}"
    if stats.quiet_days >= QUIET_DAYS:
        return f"It looks like you haven't committed in **{_plural(stats.quiet_days, 'day')}**. I'll just… nap on your keyboard."
    if stats.last7 > 0 and stats.last7 >= stats.busy_threshold:
        return (f"It looks like you made **{_plural(stats.last7, 'contribution')}** this week. "
                "Want me to knock your coffee off the desk to celebrate?")
    if stats.current_streak_weeks >= STREAK_WEEKS:
        return (f"Your weekly streak is **{stats.current_streak_weeks}**. "
                f"Your best is {stats.longest_streak_weeks}. No pressure.")
    if stats.latest_repo:
        return f"It looks like you've been pushing to **{stats.latest_repo}**. Need a hand? I only have paws."
    return "It looks like you're up to something. Want a cat on your keyboard?"
