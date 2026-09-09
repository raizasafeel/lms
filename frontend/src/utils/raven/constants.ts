// Runtime constants for the Raven settings UI, kept out of `@/types` so that
// barrel stays type-only.

/**
 * How deep condition groups may nest in this editor. ConditionBuilder offers a
 * group while `path.length < maxDepth`, so 1 means one level of nesting. Below
 * `raven_integration.engine.MAX_TREE_DEPTH` so everything authorable here saves.
 */
export const MAX_CONDITION_DEPTH = 1
