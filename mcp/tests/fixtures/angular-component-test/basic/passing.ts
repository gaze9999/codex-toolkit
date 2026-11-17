import { group, test } from '@component-test/harness';

group('fixture');
test('P1', 'a passing case', check => {
  check.equal([1, { a: 2 }], [1, { a: 2 }], 'deep value');
});
