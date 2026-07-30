# What Janus is, and why

## The short version

Janus takes an Android app, fetches its historical releases, and shows you **how the
list of servers that app talks to has changed over the years**.

## The longer version

Every Android app has web addresses baked into its code — the APIs it calls, the
analytics services it reports to, the payment processors it uses, the CDNs it loads
assets from. When a developer stops using a service, the old address often stays behind
in the code for a while, and even when removed, it is preserved in the archived older
versions of the app.

That makes an app's release history a kind of **sediment record of its infrastructure
dependencies**. If a fintech app quietly switches from a US cloud provider to a Chinese
one, or a messaging app adds a new state-linked analytics endpoint, that change is
visible in the code long before anyone announces it — if you know to look, and if you
can compare versions systematically.

Janus is the tool for doing that comparison systematically.

## Research context

Janus is built by [DIGISILK](https://www.digisilk.eu/), a project in the Department of
Digital Humanities at King's College London, funded by the European Research Council
(Horizon 2020, grant agreement 850891) and led by Dr Elisa Oreglia.

DIGISILK studies **China's Digital Silk Road** — the digital component of the Belt and
Road Initiative — as it plays out on the ground in China, Kazakhstan, Myanmar and
Cambodia. The project's methods are mostly ethnographic: fieldwork, interviews, document
analysis. Janus supplies a complementary quantitative layer, letting researchers
triangulate what people say about digital infrastructure against what the software
itself reveals.

A published example: DIGISILK's paper *"Following the code: what apps reveal about
US–China tech competition"* (**Big Data & Society**, 2025) used Janus to trace the
Kazakhstani super-app **Kaspi**, showing how its embedded endpoints recorded shifting
platform dependencies — evidence relevant to debates about the "splinternet" and
technological decoupling.

The related tool [`bgp_parser`](https://github.com/digisilk/bgp_parser) does something
comparable at the network routing layer. Janus is the application-layer instrument.

## Who uses it

Primarily social scientists, plus (as intended future users) non-profits, journalists
and regulators who want to understand app traffic patterns without reverse-engineering
skills.

**This shapes every design decision.** The people who need Janus most are the least
equipped to fight a Python environment. Anything that reduces the technical expertise
required to get an answer out of this tool is worth more than a clever internal
refactor. Conversely, anything that silently produces *wrong* numbers is worse than a
crash, because a crash gets noticed and a wrong chart gets published.

## What Janus is not

- **Not a security scanner.** It doesn't judge whether an app is malicious. It describes
  what an app connects to, and leaves interpretation to the researcher.
- **Not dynamic analysis.** It never runs the app or captures live traffic. Everything
  is static: read the code, extract the strings. An endpoint appearing in the code does
  not prove the app actually contacted it.
- **Not a general APK decompiler.** It extracts endpoints specifically, and discards
  most of what a full decompiler would surface.

Understanding that third point matters when interpreting results: Janus reports
*presence of an address in the code*, which is evidence of intent or history, not proof
of a network connection.
