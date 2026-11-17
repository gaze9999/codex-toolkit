import { test } from '@component-test/harness';

const count: number = 'not a number';
test('B1', 'never runs because compilation fails', check => check.equal(count, 1));
