export const STEP_MS = 3000
export const STEPS = [
  'Initializing a neural network…',
  'Reading your photos…',
  'Matching aesthetics…',
  'Placing you on the globe…',
  'Writing your verdict…',
]

/** Which loading line to show `elapsed` ms after the analysis started; the last one holds. */
export const stepAt = (elapsed) => STEPS[Math.min(STEPS.length - 1, Math.floor(elapsed / STEP_MS))]
