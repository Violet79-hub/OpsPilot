# Financial complaint casework

The primary workspace is now Casework. Historical public complaint categories are available as replay records. An analyst can search/filter the register, inspect a record and initiate an assessment. The four file sections are Case file, Assessment, Evidence and Activity.

1. Select CP-001 in the complaint register. The summary is generated deterministically from structured public categories; it is not a real customer quotation.
2. Choose Policy workflow + trained model and assess. The existing LangGraph looks up the record, retrieves policy, scores the trained artifact, validates the output and pauses for review.
3. Inspect the Assessment section: score, limitations and checks. Test precision is prominently disclosed. Evidence contains the actual cited policy and tool inputs/outputs.
4. Edit the response and approve or return it. The review is persisted, uses revision concurrency control and updates the register. No message or money is sent.
5. Inspect Activity for real saved events and earlier runs. Export file downloads this selected record and its current run/events.
6. New complaint stores an analyst account and manually confirmed model categories in D1, scoped to the current browser session. Historical categories can be used as a starting point but the analyst must confirm them. Unknown categories can trigger abstention. The account is not automatically classified by an LLM.

Five dedicated financial tests cover scoring, unsupported categories, a missing complaint, malicious instructions and missing identifiers. They are separate from the preserved 30-case legacy refund suite, selectable in Evaluation. Model validation, policy library, exceptions, monitoring and project notes remain available. The old generic task interface is retained under Workflow lab.

## Design sources

[Mercury Transactions](https://mercury.com/blog/updated-transactions-page) shows filterable transaction records, focused views and an evidence-led working surface. Its published interface image was inspected. [Stripe Dashboard documentation](https://docs.stripe.com/dashboard/basics) describes navigation around records, searches, customer details and unresolved work. These informed interaction structure, not an affiliation or copied brand.

Visual decisions: light navigation, white document surface, restrained navy actions, thin separators, serif case titles, compact metadata and a persistent register. The initial screen is an operational task rather than a marketing hero. No fabricated charts, growth figures, financial amounts, deadlines or customer identities were added. Counts derive from available records and this session's actual runs.

## Remaining boundary

Hosted language-model generation and semantic retrieval still require an approved server credential. That choice stays disabled while the server reports unconfigured. Rules assessment and the trained model operate now. Backend and compiled Worker checks are automated; a visual browser check was unavailable in the current execution environment.
