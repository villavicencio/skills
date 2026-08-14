# Concepts

Shared domain vocabulary for this project — entities, named processes, and status concepts with project-specific meaning. Seeded with core domain vocabulary, then accretes as ce-compound and ce-compound-refresh process learnings; direct edits are fine. Glossary only, not a spec or catch-all.

## Distribution

### Skill
A unit of agent instruction conforming to the Agent Skills specification: a directory whose `SKILL.md` carries frontmatter (name, description, version) above a prose body the agent reads when the skill activates. A skill is instructions, not executable code — which is why proving one *works* requires running an agent against it rather than compiling it.

### Plugin
The release and distribution unit. A plugin holds many skills and ships them together under a single shared version, so a fix to any one skill releases the whole set. This project deliberately ships its entire suite as one plugin rather than one plugin per skill, trading independent version cycles for a single install and a single version to reason about.

### Marketplace
The repository-as-catalog that a Claude Code instance registers once in order to install plugins from it. The local clone of a marketplace is not refreshed automatically, so updating an installed plugin is two steps — refresh the catalog, then update the plugin — and the order matters.

### Version parity
The invariant that every skill inside a plugin declares the same version as the plugin manifest. Enforced by CI as two separate checks: skills within a plugin must agree with each other, and they must agree with the manifest. Parity is what makes "one plugin, one version" true rather than aspirational; it is a structural property and says nothing about whether any skill behaves correctly.

## Evaluation

### Trigger eval
An evaluation asking whether a skill gets *selected* from the full catalog when it should, and stays unselected when it should not. It renders every skill's name and description into a catalog, poses a query, and samples the choice repeatedly, because selection is stochastic. It measures the description, not the skill body.

### Output eval
An evaluation asking whether *loading* a skill changes the agent's behavior in the intended direction. Each case runs twice — once with the skill body injected, once against a neutral baseline — and assertions are applied only to the with-skill response, with the baseline kept for comparison. Assertions are mechanical pattern matches, never a judgment of quality.

### Behavioral eval
The collective name for trigger and output evals — the layer that tests whether skills *work*, as distinct from whether they are well-formed. Behavioral evals require live model calls and therefore cost real money, which is why they run on a restricted cadence and can be gated off entirely without turning the build red.

## Verification

### Structural validation
Checking that an artifact has the right *shape*: it parses, required frontmatter fields are present, versions agree, a script compiles. Cheap enough to run on every change, and it passes without any of the artifact's logic ever executing.

### Behavioral validation
Checking that an artifact *does the right thing*: the function was called with real inputs and returned the right output, or the script ran against the real system and reported the truth. The two layers are routinely conflated, and a pipeline composed entirely of structural checks can be green over code nothing has ever run.

### Live run
Executing a skill or script against the real system it targets, as opposed to reviewing it, parsing it, or exercising it against fixtures. Reserved for the case where the real system's data shape and configuration are themselves the thing under test — a health probe cannot be validated by reading it, because what it gets wrong is what the host will actually answer.

## Flagged ambiguities

- "Validation" had been used for both the shape check and the works check — these are distinct, and the project now says **structural validation** or **behavioral validation** rather than the bare word.
- "Verified" is reserved for artifacts that have been *executed*; an artifact that has only passed structural validation is described as validated, not verified.
