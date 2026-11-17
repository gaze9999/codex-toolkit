/** <功能> 元件測試套件: 掛載真實元件, 以 DOM 事件操作並判定 FormControl、service 狀態與 request */
import { Component } from '@angular/core';
import { EMPTY } from 'rxjs';
import { group, mount, observe, test, typeBlur } from '@component-test/harness';
/** 專案原始碼用 @project/<相對 Angular 專案根目錄的路徑> 引用, 例如 '@project/src/app/orders/order-form.component' */
/** 專案 tsconfig 原有的別名照常可用 */
/** 預期值依受測程式的名稱、JSDoc 或註解與開發者的決策判定, 不讀規格, 也不要先執行受測程式再把結果當成預期值 */
// import { OrderFormComponent } from '@project/src/app/orders/order-form.component';
// import { OrderApiService } from '@project/src/app/orders/order-api.service';

@Component({
  selector: 'example-host',
  standalone: true,
  imports: [],
  template: '<input id="example">',
})
class ExampleHost {}

/** 每個 request 都直接完成且沒有資料, 案例不會呼叫實際 API */
const api = new Proxy({}, { get: (_target, key) => (key === 'then' ? undefined : () => EMPTY) });

group('<功能>');
test('X-1', '<預期行為>', async check => {
  const mounted = await mount(ExampleHost, [/* { provide: OrderApiService, useValue: api } */]);
  await typeBlur('#example', '2026/11/17');
  check.equal((document.querySelector('#example') as HTMLInputElement).value, '2026/11/17', '<判定項目>');
  mounted.destroy();
});
observe('X-2', '<只記錄不判定的觀察>', check => {
  check.observe({ timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, stub: typeof api });
});
