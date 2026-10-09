<!-- GENERATED from shared/engineering-practice.md by scripts/vendor_shared.py. Edit the source, then rerun the script. -->

# Engineering practice

Read this when diagnosing, implementing, testing, or fixing code.

## Diagnose before you touch code

- Reproduce a bug end to end, as a user would hit it, before proposing or writing a fix.
- On any timeout, race, or "almost worked" symptom, respond first with a diagnostic plan, not a fix.
  Pull primary-source evidence (health-probe history, boot logs, exact timestamps from authoritative clocks) and verify the failure mode.
- Never bundle "here is what I think went wrong" with "so change X to Y" in the same step; diagnose first.
- ⛔ "Raise the timeout", "add a retry", and "widen the window" hide real bugs; they are off the table until the failure mode is verified.
- Cross-check independent clocks (container health log, app boot log, the caller's timeout).
  If they disagree the caller is wrong; if they agree the app is slow, and only then ask why.

## Make minimal, durable changes

- Ship only durable root-cause fixes; never a workaround, temporary unblock, or bypass.
- Change exactly what was asked; do not tear down working functionality and rebuild it.
- When a mechanism works in one context and fails in another, the fault is the context (who can read the secret, what the runner can reach), not the mechanism.
  Fix the context; never rewrite the working mechanism on a theory.
- Before changing a working credential, auth, or transport path, find a recent successful run.
  If one exists, look for what differs between the passing and failing runs, and test the risky step in isolation under the failing conditions before opening a PR around it.
- When a fix fails and you need a new theory to explain why, stop and report; do not layer theory on theory.
- Do not over-engineer: accept low-risk operational tradeoffs instead of adding supervisors, sidecars, or restart wrappers for unlikely failures.

## Fix the whole class, not the first instance

- ⛔ Before a stale-record, reclaim, or reuse fix, enumerate every uniqueness and idempotency constraint and every record keyed by the entity, across every service and the whole lifecycle.
  Search the schema for every unique key, idempotency key, and foreign key first.
- When fixing a missing template variable, audit every template in the same directory for the same defect before committing.
- When mirroring a proven handler, copy its wiring (dependency-injection qualifiers, transaction boundaries, which client or credential is injected, where external calls sit relative to the transaction), not only its branch logic.
  Mocked unit tests pass on a wrong qualifier or transaction placement.

## Test-driven development

- Write a failing test first, see it fail, then implement until it passes.
  The test exercises the new behavior; it is not back-fitted to existing code.
- Write only meaningful tests.
  Before each assertion ask whether a realistic change could break it without breaking another assertion; if not, drop it.
- Mock only external edges (network, cloud APIs, containers, secrets stores, git).
  Exercise the code's own logic for real and assert the resulting behavior, not that a stub received what you passed it.
- Prefer fewer, sharper tests; if you cannot name the regression a test catches, do not write it.
- A guard test is not proven by being green.
  Mutation-test it, with the literal original defect as one of the mutants.
- Pair a positive assertion (the correct thing is present) with a negative one (the bad construction is absent), and add a false-positive probe: reformat a correct input and assert the check still passes.
- ⛔ Never guess an external API's payload shape.
  Ground every parser and fixture in real evidence: the provider's documented example verbatim, a captured live payload, or a sandbox response.
  Handle and test the absence of fields the docs mark conditional, and keep an acceptance criterion that verifies against the real integration before done.
- Run the existing test suite, not only syntax checks, before every commit.

## Reuse and study existing code

- Before writing code for an operation (API call, CLI invocation, auth flow, secret operation), search the codebase for a working implementation; reuse it directly where you can, and otherwise follow its pattern exactly.
- Apply DRY (Don't Repeat Yourself): when the logic you need already exists, call it, or extract it into a shared function, module, or script that every caller uses, rather than copying it.
  Each copy is another place a later fix must reach; look for these opportunities in every change, including duplicates your own diff introduces.
- Read the repo's decision records (ADRs or equivalent) before design work in an area they cover, and cite the ones that apply; the design is often already decided.
- When porting logic to a new context (script to workflow, inline to module), treat the original as authoritative: read it line by line and account for every variable, dependency, ordering constraint, and edge case.

## Do not hide failures

- Never suppress errors: no `2>/dev/null`, no `|| true`, no `except Exception: pass` or bare `except:`, no `.catch` that turns a failure into a silent no-op.
- In bash, fix the noisy command (`curl -sf`, `jq '.success // false'`) instead of muting the stream.
  In Python, catch the narrowest exception, log it with context, then re-raise or take a deliberate, logged fallback.
- The only legitimate suppression is a benign miss (for example "not found" on first creation), with an inline comment naming which error is benign and why the fallback is correct.
- Before committing, search your diff for `2>/dev/null`, `|| true`, `except`, and `.catch`, and justify every hit.
  When something ran green but did nothing, suspect a silenced error first.

## Migrations

- ⛔ Never edit a schema migration that has already been applied.
  Tools that validate checksums at startup (for example Flyway with migrate-at-start) fail the boot on a mismatch.
  Add a new migration version instead; to recover, restore the applied file byte for byte (`git show <sha>:<path>`) and move the change to the new version.
- A corrective migration does not fix a fresh database built from the edited history; check both paths.
