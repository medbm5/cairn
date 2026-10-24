export const GOAL_TYPES = ['retirement', 'home', 'safety_net', 'studies', 'other'] as const
export type GoalType = (typeof GOAL_TYPES)[number]
