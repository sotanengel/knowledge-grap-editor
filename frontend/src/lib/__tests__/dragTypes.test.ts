import { describe, expect, it } from 'vitest';

import { CLASS_DRAG_TYPE } from '../dragTypes';

describe('the class drag payload', () => {
  it('uses a vendor MIME type so nothing else claims the drop', () => {
    expect(CLASS_DRAG_TYPE).toBe('application/x-ontoforge-class');
  });
});
