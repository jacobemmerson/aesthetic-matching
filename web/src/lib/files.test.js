import { expect, test } from 'vitest'
import { MAX_FILES } from './files.js'

test('caps at ten files', () => { expect(MAX_FILES).toBe(10) })
