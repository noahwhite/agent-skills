// OPTIONAL, RUNTIME-SPECIFIC ACCELERATOR for the escalation loop of the pre-PR gate.
//
// This file targets a runtime that runs workflow scripts with the globals `args`, `agent(prompt, opts)`,
// `parallel([...])` and `log(msg)`. On any other runtime, follow the manual procedure in
// engineering-workflow SKILL.md ("Escalation: the gated two-lens loop"); the two are equivalent.
//
// The default pre-PR gate is the adversarial-review-pipeline skill. Escalate to this loop only when
// that gate cannot close the diff. Never run both over the same head.
//
// Each round: two reviewers with DIFFERENT lenses review the branch diff in parallel (the hunter for
// correctness/wiring/security/tests, the simplicity reviewer for scope and over-engineering);
// blocking findings (critical/high with a concrete failure scenario) are VERIFIED against the code;
// a scope-capped fixer fixes, rejects with a reason, or escalates. The loop converges on zero
// VERIFIED blocking findings, never on zero findings: a zero-findings terminator rewards reviewers
// for inventing findings once the real ones are gone, and a fixer forced to act on all of them
// bloats the code.
//
// The loop fails closed: a lens that did not report reviewer_ran_against_real_code === true, a
// verifier response without exactly one boolean verdict per candidate, or a fix whose tests did not
// pass is an unresolved gate (converged: false), never a clean one.
//
// Arguments (all from the consumer profile; nothing is defaulted to a project value):
//   base        required  diff base, origin/<profile.git.integration_branch> after a fetch
//   spec        optional  story + acceptance-criteria text (the scope reference)
//   maxRounds   optional  default 2, hard cap 2 (escalation path)
//   hunter      required  { name, command }  shell template for profile.review.pre_pr.hunter, with
//                         {prompt_file}, {output_file} and {checkout} placeholders
//   models      required  { simplicity, verifier, fixer }  model ids in this runtime's syntax, from
//                         profile.review.pre_pr.simplicity_reviewer, .arbiter and .fixer
//   agentType   optional  subagent type to launch (runtime-specific)
//
// Returns { converged, rounds, reason, blocking, nits }. Unresolved reasons: reviewer-missing,
// reviewer-blind, verifier-invalid, no-progress, escalated-scope, all-rejected, fix-not-committed,
// fix-tests-failed, max-rounds.

export const meta = {
  name: 'adversarial-review-loop',
  description: 'Escalation pre-PR review: two lenses find issues, a verifier confirms the blocking ones, a scope-capped fixer fixes or rejects, until no verified blocking findings remain or progress stalls.',
  whenToUse: 'Only when the default adversarial-review-pipeline gate cannot close the diff. Not the default gate.',
  phases: [
    { title: 'Review', detail: 'Hunter (correctness/security) + simplicity reviewer (scope) in parallel' },
    { title: 'Verify', detail: 'Confirm each blocking finding against the code; drop the unconfirmed' },
    { title: 'Fix', detail: 'Scope-capped fixer fixes or rejects, runs tests, commits' },
  ],
}

function required(value, label) {
  if (!value) throw new Error(`adversarial-review-loop: missing required argument ${label} (take it from the consumer profile)`)
  return value
}

const a = args || {}
const base = required(a.base, 'base')
const hunter = required(a.hunter, 'hunter')
required(hunter.command, 'hunter.command')
const models = required(a.models, 'models')
required(models.simplicity, 'models.simplicity')
required(models.verifier, 'models.verifier')
required(models.fixer, 'models.fixer')
const agentType = a.agentType
const maxRounds = Math.min(a.maxRounds || 2, 2)
const spec = a.spec || null
const specBlock = spec
  ? `\n\nSPEC / ACCEPTANCE CRITERIA (the reference for scope: anything outside this is out of scope, not a defect):\n${spec}\n`
  : '\n\n(No spec was provided; judge scope conservatively and prefer the smallest change.)\n'
const SECRETS = 'Never write secrets to files or command arguments.'

const IMPORTANT = new Set(['critical', 'high'])

const FINDINGS = {
  type: 'object',
  properties: {
    reviewer_ran_against_real_code: { type: 'boolean' },
    evidence: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          file: { type: 'string' },
          line: { type: 'number' },
          issue: { type: 'string' },
          failure_scenario: { type: 'string' },
          suggestion: { type: 'string' },
          source: { type: 'string', enum: ['hunter', 'simplicity'] },
        },
        required: ['severity', 'issue', 'source'],
      },
    },
  },
  required: ['reviewer_ran_against_real_code', 'findings'],
}

const VERIFY = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          index: { type: 'number' },
          confirmed: { type: 'boolean' },
          rationale: { type: 'string' },
        },
        required: ['index', 'confirmed'],
      },
    },
  },
  required: ['results'],
}

const FIX = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    fixed: { type: 'array', items: { type: 'string' } },
    rejected: { type: 'array', items: { type: 'string' } },
    escalated: { type: 'array', items: { type: 'string' } },
    tests_passed: { type: 'boolean' },
    committed: { type: 'boolean' },
  },
  required: ['summary', 'committed'],
}

function opts(extra) {
  return agentType ? { ...extra, agentType } : extra
}

function hunterPrompt() {
  return `You are wrapping an external reviewer (${hunter.name || 'hunter'}) as an independent adversarial reviewer of this branch versus \`${base}\`. Its LENS: correctness, wiring (wrong client/key/queue, transaction boundaries, dependency-injection mistakes), security, concurrency/races, API/compat breakage, and missing or weak tests.
${specBlock}
Run it against a THROWAWAY checkout, never the real tree:
  1. Make a private scratch directory with mktemp -d; create a detached worktree of HEAD inside it (git worktree add --detach <dir> HEAD).
  2. Write the review instruction to a prompt file in the scratch directory: "Adversarially review ONLY the changes on this branch versus ${base}. First run: git diff ${base}...HEAD and read the changed files, their call sites and tests. Report concrete correctness/wiring/security/test findings, most severe first, each with the exact file:line and a concrete failure scenario. No praise. ${SECRETS}"
  3. Run this command template with {prompt_file}, {output_file} and {checkout} replaced by those paths, with stdin redirected from the prompt file, under a timeout of about 10 minutes. Never put the prompt or the diff in a command argument:
     ${hunter.command}
  4. Read the output file, then remove the worktree (git worktree remove --force <dir>).

Then return the schema with reviewer_ran_against_real_code=true only if the reviewer demonstrably read the diff and the changed files, and put that proof (the command and what it showed) in evidence. SEVERITY DISCIPLINE: critical/high ONLY for a real defect that should block the PR AND has a concrete failure_scenario (specific inputs/state -> wrong output/crash). Style, naming and speculative hardening are low/medium. Set source="hunter".
Never a false clean: if the output shows a sandbox or permission error (for example "bwrap"), shows the reviewer could not read the code, or the diff was empty, return reviewer_ran_against_real_code=false with that output in evidence. Do not invent findings. Do not modify the real tree. ${SECRETS}`
}

function simplicityPrompt() {
  return `You are an independent adversarial reviewer of this branch versus \`${base}\`. Your LENS: SIMPLICITY and SCOPE - is this the smallest correct change? Flag over-engineering, unnecessary abstractions/modules/persistence, gold-plating of low-stakes paths, duplicated or dead code, and genuine correctness/edge/test-adequacy defects the other reviewer might miss.
${specBlock}
Work read-only: run git diff ${base}...HEAD, read the changed files, call sites and tests.

Return the schema with reviewer_ran_against_real_code=true only if you actually read the diff and the changed files, and put that proof (the command and what it showed) in evidence; if you could not, set it false and explain in evidence. SEVERITY DISCIPLINE: critical/high only for real blocking defects WITH a concrete failure_scenario. Over-engineering is high ONLY if it adds real risk or maintenance burden; otherwise medium. Polish/style is low. Prefer recommending REMOVAL over addition. Set source="simplicity". An empty findings array is correct for a clean, proportionate diff. ${SECRETS}`
}

function verifyPrompt(importantJson) {
  return `You are an adversarial verifier. For each candidate BLOCKING finding below, try to REFUTE it against the actual code. Default to confirmed=false unless you can point to the exact defect or a concrete reproduction (a failing input, a wrong branch, a real missing test). A finding that is vague, speculative, style-only, out of the spec's scope, or already handled elsewhere is confirmed=false.

Read the code you need: git diff ${base}...HEAD, then open the cited files and their call sites.
${specBlock}
Candidate findings (JSON, with index):
${importantJson}

Return {results:[{index, confirmed, rationale}]}, exactly one entry per index, with confirmed a boolean; a response missing an index is treated as an unresolved gate. A confirmed finding must be a real defect a maintainer would fix now. ${SECRETS}`
}

function fixPrompt(round, verifiedJson) {
  return `You are the implementer for this branch (base \`${base}\`), round ${round}. Below are VERIFIED blocking findings, presented as claims to check: verify each yourself before changing anything.
${specBlock}
Verified findings (JSON):
${verifiedJson}

Rules:
- Fix a finding ONLY if, on your own inspection, it is a real defect within the spec's scope. List those in "fixed".
- If a finding is wrong, redundant, or out of scope, DO NOT change code for it: put it in "rejected" with a one-line reason.
- SCOPE CAP: do NOT add new modules, classes, database tables/migrations, persistence, or abstractions. If a finding genuinely requires that, put it in "escalated" with why (it needs a human design decision), and leave the code as is.
- Do not touch code this diff only consumes (another component's endpoint, a shared library, another story's surface).
- Prefer the smallest change; where a finding is about weak coverage, add a focused test.
Then run the repository's focused tests for the changed area and set tests_passed. If you changed anything, commit on the current branch following the repository's commit-signing and attribution rules, with message "fix: address verified review findings (round ${round})"; set committed=true only if a commit actually happened. Never push and never force-push. ${SECRETS}
Return {summary, fixed, rejected, escalated, tests_passed, committed}.`
}

// A lens result counts only if it says it ran against the real code and returned a findings array.
function lensProblem(review) {
  if (!review || typeof review !== 'object') return 'reviewer-missing'
  if (review.reviewer_ran_against_real_code !== true || !Array.isArray(review.findings)) return 'reviewer-blind'
  return null
}

// Exactly one boolean verdict per candidate index 0..n-1, or null (unresolved).
function validVerdicts(verdicts, n) {
  if (!verdicts || !Array.isArray(verdicts.results) || verdicts.results.length !== n) return null
  const byIndex = new Map()
  for (const v of verdicts.results) {
    if (!v || !Number.isInteger(v.index) || v.index < 0 || v.index >= n) return null
    if (typeof v.confirmed !== 'boolean' || byIndex.has(v.index)) return null
    byIndex.set(v.index, v.confirmed)
  }
  return byIndex
}

function classify(findings) {
  const blocking = []
  const nits = []
  for (const f of findings) {
    if (f && IMPORTANT.has(f.severity)) blocking.push(f)
    else if (f) nits.push(f)
  }
  return { blocking, nits }
}

let converged = false
let reason = 'max-rounds'
let completedRounds = 0
let prevVerifiedCount = Infinity
let lastBlocking = []
let lastNits = []

for (let round = 1; round <= maxRounds; round++) {
  completedRounds = round

  const reviews = await parallel([
    () => agent(hunterPrompt(), opts({ label: `hunter:${round}`, phase: 'Review', schema: FINDINGS })),
    () => agent(simplicityPrompt(), opts({ label: `simplicity:${round}`, phase: 'Review', schema: FINDINGS, model: models.simplicity })),
  ])
  const problems = reviews.map(lensProblem).filter(Boolean)
  if (reviews.length !== 2 || problems.length) {
    reason = problems.includes('reviewer-missing') || reviews.length !== 2 ? 'reviewer-missing' : 'reviewer-blind'
    log(`Round ${round}: a lens did not run against the real code (${reason}); the gate is unresolved.`)
    return { converged: false, rounds: round, reason, blocking: lastBlocking, nits: lastNits, reviews }
  }
  const { blocking, nits } = classify(reviews.flatMap(r => r.findings))
  lastNits = nits
  log(`Round ${round}: ${blocking.length} blocking candidate(s), ${nits.length} nit(s) (logged, not fixed).`)

  if (blocking.length === 0) { converged = true; reason = 'clean'; break }

  const indexed = blocking.map((f, i) => ({ index: i, ...f }))
  const verdicts = await agent(verifyPrompt(JSON.stringify(indexed, null, 2)),
    opts({ label: `verify:${round}`, phase: 'Verify', schema: VERIFY, model: models.verifier }))
  const byIndex = validVerdicts(verdicts, indexed.length)
  if (!byIndex) {
    reason = 'verifier-invalid'
    log(`Round ${round}: the verifier did not return exactly one verdict per candidate; the gate is unresolved.`)
    return { converged: false, rounds: round, reason, blocking: indexed, nits, verdicts }
  }
  const verified = indexed.filter(f => byIndex.get(f.index) === true)
  lastBlocking = verified
  log(`Round ${round}: ${verified.length}/${blocking.length} blocking finding(s) survived verification.`)

  if (verified.length === 0) { converged = true; reason = 'clean-after-verify'; break }

  // After a fix, the verified blocking count must strictly shrink; otherwise it is fix-induced churn.
  if (round > 1 && verified.length >= prevVerifiedCount) {
    reason = 'no-progress'
    log(`Round ${round}: verified blocking count did not shrink (${prevVerifiedCount} -> ${verified.length}); stopping for human review.`)
    return { converged: false, rounds: round, reason, blocking: verified, nits }
  }
  prevVerifiedCount = verified.length

  const fix = await agent(fixPrompt(round, JSON.stringify(verified.map(({ index, ...f }) => f), null, 2)),
    opts({ label: `fix:${round}`, phase: 'Fix', schema: FIX, model: models.fixer }))
  if (fix && fix.escalated && fix.escalated.length) {
    reason = 'escalated-scope'
    log(`Round ${round}: a finding needs scope growth beyond the cap; escalating to a human.`)
    return { converged: false, rounds: round, reason, blocking: verified, nits, fix }
  }
  if (!fix || !fix.committed) {
    reason = fix && fix.rejected && fix.rejected.length && !(fix.fixed && fix.fixed.length) ? 'all-rejected' : 'fix-not-committed'
    log(`Round ${round}: fixer committed no fix (${reason}); stopping for human review.`)
    return { converged: false, rounds: round, reason, blocking: verified, nits, fix }
  }
  if (fix.tests_passed !== true) {
    reason = 'fix-tests-failed'
    log(`Round ${round}: the fix commit did not report passing tests; it is not accepted as a fix.`)
    return { converged: false, rounds: round, reason, blocking: verified, nits, fix }
  }
}

if (!converged) {
  log(`Hit the ${maxRounds}-round cap; ${lastBlocking.length} verified blocking finding(s) remain for human review.`)
}

return {
  converged,
  rounds: completedRounds,
  reason,
  blocking: converged ? [] : lastBlocking,
  nits: lastNits,
}
