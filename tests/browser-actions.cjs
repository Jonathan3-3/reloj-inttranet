const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const root = process.cwd();
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    let mode = 'empty';
    const requests = [];
    const main = fs.readFileSync(path.join(root, 'static/js/main.js'), 'utf8');
    function fixture(name) {
      let html = fs.readFileSync(path.join(root, `templates/asistencia/${name}.html`), 'utf8');
      html = html.replace(/\{%[\s\S]*?%\}/g, '').replace(/\{\{ csrf_token \}\}/g, 'fixture-token').replace(/\{\{[\s\S]*?\}\}/g, '2026-11-03');
      return `<!doctype html><html><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script><script>${main}</script></head><body>${html}</body></html>`;
    }
    await page.route('http://reloj.test/**', async route => {
      const req = route.request();
      const url = new URL(req.url());
      if (url.pathname === '/buscar/') return route.fulfill({contentType:'text/html', body: fixture('buscar')});
      if (url.pathname === '/horas/') return route.fulfill({contentType:'text/html', body: fixture('horas_reales')});
      if (url.pathname.includes('/empleados/')) return route.fulfill({json:{empleados:[{id:7,id_original:'A7',nombre:"O'Connor <img src=x onerror=alert(1)>",departamento:'RH'}]}});
      if (url.pathname.includes('/recalcular/')) {
        requests.push({method:req.method(), csrf:req.headers()['x-csrftoken'], search:url.search});
        return route.fulfill({json:{ok:true,mensaje:'Recalculados 0 registros'}});
      }
      if (url.pathname.includes('/reporte/')) {
        if (mode === 'error') return route.fulfill({status:400,json:{error:'Rango inválido'}});
        if (mode === 'session') return route.fulfill({contentType:'text/html',body:'Login'});
        if (mode === 'row') return route.fulfill({json:{total:1,resultados:[{id:'A7',nombre:"O'Connor <script>bad()</script>",departamento:'RH',fecha:'2026-11-03',observacion:'<img src=x onerror=bad()>',incidencia:'',retardo:0}]}});
        return route.fulfill({json:{total:0,resultados:[]}});
      }
      return route.fulfill({status:404,body:''});
    });
    page.on('dialog', dialog => dialog.accept());
    await page.goto('http://reloj.test/buscar/');
    await page.getByText('Sin resultados para esta consulta.').waitFor();
    await page.locator('#buscar-empleado').fill('Connor');
    await page.locator('#sugerencias button').waitFor();
    assert.equal(await page.locator('#sugerencias img').count(),0);
    mode = 'row';
    await page.locator('#sugerencias button').click();
    await page.locator('#resultados-container td').first().waitFor();
    assert.equal(await page.locator('#resultados-container script, #resultados-container img').count(),0);
    assert.match(await page.locator('#resultados-container').innerText(), /O'Connor <script>/);
    mode='error';
    await page.getByRole('button',{name:'Consultar',exact:true}).click();
    await page.getByText('Rango inválido',{exact:true}).waitFor();
    mode='session';
    await page.getByRole('button',{name:'Consultar',exact:true}).click();
    await page.getByText('La sesión expiró o el servidor no devolvió una respuesta válida.',{exact:true}).waitFor();
    mode='empty';
    await page.getByRole('button',{name:'Recalcular Hoy',exact:true}).click();
    await page.getByText('Sin resultados para esta consulta.').waitFor();
    await page.locator('#recalcular-desde').fill('2026-11-01');
    await page.locator('#recalcular-hasta').fill('2026-11-03');
    await page.getByRole('button',{name:'Recalcular',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('#recalcular-rango').classList.contains('d-none'));
    await page.goto('http://reloj.test/horas/');
    await page.getByRole('button',{name:'Recalcular Hoy',exact:true}).click();
    await page.waitForTimeout(300);
    assert.equal(requests.length,3);
    for (const request of requests) {
      assert.equal(request.method,'POST');
      assert.equal(request.csrf,'fixture-token');
    }
    assert.equal(requests[1].search,'?desde=2026-11-01&hasta=2026-11-03');
    assert.deepEqual(errors,[]);
    console.log('OK: navegador Edge aislado; búsqueda con comillas/HTML, vacío, error HTTP, sesión y tres recálculos POST con CSRF. Sin errores JS.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
