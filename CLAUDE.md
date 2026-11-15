# CLAUDE.md - ᴘᴛ/ᴇɴ

Todo o contexto básico para o Claude Code neste repositório. 
As regras gerais de agentes e de design são importadas abaixo e continuam sendo a fonte da verdade; este arquivo só adiciona o que é específico para o dia a dia no código.

All basic context for Claude Code in this repository.
General agent and design rules are imported below and remain the source of truth; this file only adds specifics relevant to day-to-day coding.

---

@AGENTS.md [AGENTS](./AGENTS.md)
@CONTRIBUTING.md [CONTRIBUTING](./CONTRIBUTING.md)
@README.md [README](./README.md)
@docs/ARCHITECTURE.md [ARCHITECTURE](./docs/ARCHITECTURE.md)

---

É essencial entender todo contexto e ler a documentação antes de implementar, corrigir ou adicionar qualquer linha de código ao projeto.

It is essential to understand the full context and read the documentation before implementing, fixing, or adding any line of code to the project.

## Revisores / Reviewers (`.claude/agents/`)

Antes de finalizar uma mudança, rode o revisor da área que ela toca e resolva os achados bloqueantes:

| Agente | Quando |
|---|---|
| `payments-reviewer` | Checkout, provedores, webhooks, cupons, cartão salvo, reconciliação |
| `auth-reviewer` | Login, 2FA, step-up, lockout, sessões, passkeys, TV, mobile auth |
| `lgpd-reviewer` | Dado pessoal ou de saúde: schema de usuário, export, exclusão, logs, terceiros |
| `security-reviewer` | Qualquer rota de API, middleware, upload, HTML renderizado ou integração |
| `feature-reviewer` | Qualquer funcionalidade nova ou alterada (web, mobile, TV, ai-service ou pacotes): regras de negócio, contrato API e telas, testes, i18n e docs |
| `performance-reviewer` | Rota de API, query, schema, cache, middleware, listas e páginas, worker ou chat; peça "auditoria completa" para varrer o projeto inteiro |

Before finalizing a change, run the reviewer for the affected area and resolve any blocking findings:

| Agent | When |
|---|---|
| `payments-reviewer` | Checkout, providers, webhooks, coupons, saved cards, reconciliation |
| `auth-reviewer` | Login, 2FA, step-up, lockout, sessions, passkeys, TV, mobile auth |
| `lgpd-reviewer` | Personal or health data: user schema, export, deletion, logs, third parties |
| `security-reviewer` | Any API route, middleware, upload, rendered HTML, or integration |
| `feature-reviewer` | Any new or changed feature (web, mobile, TV, ai-service or packages): business rules, API and screen contract, tests, i18n and docs |
| `performance-reviewer` | API route, query, schema, cache, middleware, lists and pages, worker or chat; ask for a "full audit" to sweep the whole project |