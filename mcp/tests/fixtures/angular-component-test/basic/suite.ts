import { Component } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { group, mount, observe, test, typeBlur } from '@component-test/harness';

@Component({
  selector: 'fixture-host',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: '<input id="name" [formControl]="name">',
})
class FixtureHost {
  public readonly name = new FormControl('', { nonNullable: true, validators: [Validators.required] });
}

group('fixture');
test('F1', 'typed text reaches the control', async check => {
  const mounted = await mount(FixtureHost);
  await typeBlur('#name', 'abc');
  check.equal(mounted.host.name.value, 'abc', 'control value');
  check.ok(mounted.host.name.valid, 'control valid');
  mounted.destroy();
});
test('F2', 'a wrong expectation is reported as failed', check => {
  check.equal('2026/11/17', '2026-11-17', 'separator');
});
test('F3', 'a thrown error is reported as error', () => {
  throw new Error('fixture error');
});
observe('O1', 'an observation is recorded without a verdict', check => {
  check.observe({ timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, epochDay: new Date(0).getDate() });
});
